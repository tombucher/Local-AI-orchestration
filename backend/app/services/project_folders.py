"""
Projets tenus dans des dossiers du Mac : un sous-dossier par projet, avec sa fiche .md.

    Mes projets/                 ← dossier choisi dans Paramètres
    ├── Tickets de veille/
    │   ├── tickets-de-veille.md ← la fiche du projet (lue, et cochée par l'outil)
    │   └── Production/          ← ce que l'outil a produit (code, documents, veilles)
    └── Calendrier de l'Avent/
        └── calendrier.md

Sens des échanges :
- fiche .md → outil : à chaque enregistrement, le projet et ses tâches suivent ;
- outil → fiche .md : seulement la case [x] d'une tâche terminée ;
- outil → Production/ : les fichiers produits, sans jamais écraser un fichier
  retouché à la main (on retient ce qu'on a écrit, voir MANIFESTE).

Le serveur tourne dans Docker : il ne voit que le dossier du Mac partagé avec lui
(PROJECTS_MOUNT, par défaut ~/Documents). Tous les chemins sont vérifiés pour
rester dedans.
"""

import hashlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.models.task_log import TaskEventType, TaskLog
from app.models.user_settings import UserSettings
from app.models.veille_topic import VeilleScope, VeilleTopic
from app.services.maturity import MaturityService
from app.services.project_export import collect_project_files, safe_path
from app.services.project_markdown import cle_titre, cocher_tache, lire_projet

logger = logging.getLogger(__name__)

SORTIES = "Production"
MANIFESTE = ".orchestrateur.json"
MAX_TAILLE_FICHE = 512 * 1024
NOMS_PREFERES = ("projet.md", "README.md", "readme.md")


# ---------------------------------------------------------------- chemins --

def mount() -> Path:
    return Path(settings.PROJECTS_MOUNT)


def mount_available() -> bool:
    return mount().is_dir()


def display_path(rel: str = "") -> str:
    """Chemin tel que Tom le voit sur son Mac."""
    base = (settings.PROJECTS_MOUNT_DISPLAY or str(mount())).rstrip("/")
    return f"{base}/{rel}".rstrip("/") if rel else base


def inside_mount(rel: Optional[str]) -> Path:
    """Chemin absolu d'un dossier relatif au partage, refusé s'il en sort."""
    base = mount().resolve()
    cible = (base / (rel or "").strip("/")).resolve()
    if cible != base and base not in cible.parents:
        raise ValueError("Ce dossier est hors du dossier partagé avec l'outil.")
    return cible


def relative(path: Path) -> str:
    return path.resolve().relative_to(mount().resolve()).as_posix()


def _visible(p: Path) -> bool:
    return not p.name.startswith(".") and p.name != SORTIES


def pick_project_file(dossier: Path) -> Optional[Path]:
    """La fiche du projet : le .md au premier niveau du dossier.

    S'il y en a plusieurs : celui qui porte le nom du dossier, puis projet.md,
    README.md, sinon le premier par ordre alphabétique.
    """
    fiches = sorted(p for p in dossier.glob("*.md") if p.is_file() and _visible(p))
    if not fiches:
        return None
    for fiche in fiches:
        if fiche.stem.lower() == dossier.name.lower():
            return fiche
    for nom in NOMS_PREFERES:
        if (dossier / nom) in fiches:
            return dossier / nom
    return fiches[0]


def scan(racine: Path) -> List[Path]:
    """Fiches des projets d'un dossier de projets (un sous-dossier = un projet)."""
    if not racine.is_dir():
        return []
    fiches = []
    for dossier in sorted(p for p in racine.iterdir() if p.is_dir() and _visible(p)):
        fiche = pick_project_file(dossier)
        if fiche:
            fiches.append(fiche)
    return fiches


def browse(rel: str = "") -> dict:
    """Sous-dossiers d'un dossier du partage, pour choisir le dossier de projets."""
    dossier = inside_mount(rel)
    if not dossier.is_dir():
        raise ValueError("Dossier introuvable.")
    rel_propre = relative(dossier) if dossier != mount().resolve() else ""
    enfants = []
    for p in sorted(dossier.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith("."):
            try:
                enfants.append({"name": p.name, "path": relative(p),
                                "is_project": pick_project_file(p) is not None})
            except (PermissionError, ValueError):
                continue
    parent = None
    if rel_propre:
        parent = relative(dossier.parent) if dossier.parent != mount().resolve() else ""
    return {"path": rel_propre, "display": display_path(rel_propre), "parent": parent, "dirs": enfants}


def _empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


def _ecrire_atomique(chemin: Path, contenu: str) -> None:
    """Écrit sans jamais laisser un fichier à moitié écrit (éditeur ouvert, iCloud…)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=chemin.parent, prefix=".orchestrateur-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenu)
        os.replace(tmp, chemin)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ------------------------------------------------------------ rapport --

@dataclass
class SyncReport:
    created: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    checked: List[str] = field(default_factory=list)       # cases cochées dans les fiches
    exported: List[str] = field(default_factory=list)      # fichiers écrits dans Production/
    kept: List[str] = field(default_factory=list)          # retouchés à la main, non écrasés
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# ------------------------------------------------------- fiche → outil --

def _md_tasks(tasks: List[Task]) -> Dict[str, Task]:
    return {(t.task_metadata or {}).get("md_key"): t for t in tasks
            if (t.task_metadata or {}).get("md_key") and t.status != TaskStatus.CANCELLED}


async def apply_markdown(
    db: AsyncSession, user_id: int, texte: str, *,
    project: Optional[Project] = None, fallback_name: str = "Nouveau projet",
    source_path: Optional[str] = None, report: Optional[SyncReport] = None,
) -> Project:
    """Crée ou met à jour un projet et ses tâches d'après sa fiche .md."""
    report = report or SyncReport()
    fiche = lire_projet(texte)
    nom = (fiche.titre or fallback_name).strip()[:255] or fallback_name
    report.warnings += [f"{nom} — {e}" for e in fiche.erreurs]
    maintenant = datetime.now(timezone.utc)

    if project is None:
        project = Project(user_id=user_id, name=nom, description=fiche.description or None,
                          type=ProjectType.PERSONAL, status=ProjectStatus.ACTIVE,
                          features={"code_gen": True, "veille": True, "git_auto": False},
                          source_path=source_path)
        db.add(project)
        await db.flush()
        report.created.append(nom)
    else:
        project.name = nom
        project.description = fiche.description or None
        report.updated.append(nom)

    existantes = _md_tasks((await db.execute(
        select(Task).where(Task.project_id == project.id)
    )).unique().scalars().all())

    par_cle: Dict[str, Task] = {}
    for t in fiche.taches:
        tache = existantes.pop(t.cle, None)
        if tache is None:
            tache = Task(
                project_id=project.id, title=t.titre[:255], description=t.description or None,
                task_type=t.task_type, priority=t.priorite, due_date=t.echeance,
                # Créée en attente : c'est Tom qui active ses tâches
                status=TaskStatus.COMPLETED if t.fait else TaskStatus.CREATED,
                completed_at=maintenant if t.fait else None,
                task_metadata={**t.metadata, "source": "md", "md_key": t.cle,
                               "md_done": t.fait, "md_checked": t.fait},
            )
            db.add(tache)
            await db.flush()
            db.add(TaskLog(task_id=tache.id, event_type=TaskEventType.CREATED, user_id=user_id,
                           details={"source": "fiche .md", "initial_status": tache.status.value}))
            if t.task_type == TaskType.VEILLE and not t.fait:
                await _lier_veille(db, project.id, tache, t.metadata)
        else:
            meta = dict(tache.task_metadata or {})
            tache.title = t.titre[:255]
            tache.description = t.description or None
            tache.priority = t.priorite
            tache.due_date = t.echeance
            if tache.status == TaskStatus.CREATED:
                tache.task_type = t.task_type
                meta.update(t.metadata)
            # Case cochée à la main dans la fiche → tâche terminée
            if t.fait and not meta.get("md_done") and tache.status not in (
                    TaskStatus.COMPLETED, TaskStatus.GENERATING):
                ancien = tache.status.value
                tache.status = TaskStatus.COMPLETED
                tache.completed_at = maintenant
                db.add(TaskLog(task_id=tache.id, event_type=TaskEventType.STATUS_CHANGED, user_id=user_id,
                               details={"source": "fiche .md", "old_status": ancien, "new_status": "completed"}))
            meta["md_done"] = t.fait
            meta["md_checked"] = meta.get("md_checked") or t.fait
            tache.task_metadata = meta
        par_cle[t.cle] = tache

    # Retirée de la fiche : annulée si rien n'a encore été produit, sinon conservée
    for tache in existantes.values():
        if tache.status in (TaskStatus.CREATED, TaskStatus.READY) and not (
                (tache.generated_code or "").strip() or tache.radar_report):
            tache.status = TaskStatus.CANCELLED
            db.add(TaskLog(task_id=tache.id, event_type=TaskEventType.CANCELLED, user_id=user_id,
                           details={"source": "fiche .md", "reason": "retirée de la fiche"}))
        else:
            tache.task_metadata = {**(tache.task_metadata or {}), "md_removed": True}

    # « après: » → dépendances, entre tâches de la fiche seulement
    await db.flush()
    ids_fiche = [t.id for t in par_cle.values()]
    if ids_fiche:
        await db.execute(delete(task_dependencies).where(
            task_dependencies.c.task_id.in_(ids_fiche),
            task_dependencies.c.depends_on_id.in_(ids_fiche)))
        lignes = [{"task_id": par_cle[t.cle].id, "depends_on_id": par_cle[cle_dep].id}
                  for t in fiche.taches
                  for cle_dep in (cle_titre(a) for a in t.apres)
                  if cle_dep in par_cle and par_cle[cle_dep].id != par_cle[t.cle].id]
        if lignes:
            await db.execute(insert(task_dependencies), lignes)

    project.source_hash = _empreinte(texte)
    await db.flush()
    await MaturityService().update_project_maturity_score(project.id, db)
    return project


async def _lier_veille(db: AsyncSession, project_id: int, tache: Task, metadata: dict) -> None:
    """Comme à la création par l'API : une veille a besoin de son sujet de veille."""
    try:
        scope = VeilleScope(metadata.get("scope", "news"))
    except ValueError:
        scope = VeilleScope.NEWS
    frequence = metadata.get("frequency", "once")
    topic = VeilleTopic(project_id=project_id, name=tache.title, scope=scope,
                        description=tache.description, keywords=metadata.get("keywords", []),
                        excluded_keywords=[], scan_frequency=frequence, enabled=True)
    if frequence != "once":
        topic.next_scan = topic.calculate_next_scan()
    db.add(topic)
    await db.flush()
    tache.veille_topic_id = topic.id


# ------------------------------------------------------- outil → fiche --

async def _cocher_les_terminees(db: AsyncSession, project: Project, fiche: Path, report: SyncReport) -> None:
    taches = _md_tasks((await db.execute(
        select(Task).where(Task.project_id == project.id)
    )).unique().scalars().all())
    a_cocher = [t for t in taches.values()
                if t.status == TaskStatus.COMPLETED and not (t.task_metadata or {}).get("md_checked")]
    if not a_cocher:
        return

    texte = fiche.read_text(encoding="utf-8")  # relu juste avant d'écrire
    modifie = False
    for tache in a_cocher:
        nouveau = cocher_tache(texte, tache.title)
        if nouveau is not None:
            texte, modifie = nouveau, True
            report.checked.append(f"{project.name} — {tache.title}")
        # Cochée une fois pour toutes : si Tom la décoche, on ne recoche pas
        tache.task_metadata = {**(tache.task_metadata or {}), "md_checked": True, "md_done": True}
    if modifie:
        _ecrire_atomique(fiche, texte)
        project.source_hash = _empreinte(texte)


# --------------------------------------------------- outil → Production --

async def _exporter(db: AsyncSession, project: Project, dossier: Path, report: SyncReport) -> None:
    fichiers = (await collect_project_files(db, project)).all
    if not fichiers:
        return
    sortie = dossier / SORTIES
    chemin_manifeste = sortie / MANIFESTE
    try:
        manifeste = json.loads(chemin_manifeste.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifeste = {}

    change = False
    for f in fichiers:
        rel = safe_path(f.path)
        if not rel:
            continue
        cible = (sortie / rel).resolve()
        if sortie.resolve() not in cible.parents:
            continue
        voulu = _empreinte(f.content)
        if cible.exists():
            actuel = _empreinte(cible.read_text(encoding="utf-8", errors="replace"))
            if actuel == voulu:
                continue
            if actuel != manifeste.get(rel):
                # Retouché à la main depuis notre dernière écriture : on n'écrase pas
                if manifeste.get(f"{rel}#signale") != voulu:
                    report.kept.append(f"{project.name} — {rel}")
                    manifeste[f"{rel}#signale"] = voulu
                    change = True
                continue
        _ecrire_atomique(cible, f.content)
        manifeste[rel] = voulu
        manifeste.pop(f"{rel}#signale", None)
        report.exported.append(f"{project.name} — {rel}")
        change = True
    if change:
        _ecrire_atomique(chemin_manifeste, json.dumps(manifeste, ensure_ascii=False, indent=1))


# ------------------------------------------------------------- cycle --

async def user_root(db: AsyncSession, user_id: int) -> Optional[Path]:
    reglages = (await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id))).scalars().first()
    if not reglages or not reglages.projects_folder or not mount_available():
        return None
    try:
        return inside_mount(reglages.projects_folder)
    except ValueError:
        return None


async def sync_user(db: AsyncSession, user_id: int) -> SyncReport:
    """Un passage complet : fiches → outil, cases cochées, Production/."""
    report = SyncReport()
    racine = await user_root(db, user_id)
    if racine is None:
        return report

    for fiche in scan(racine):
        rel = relative(fiche)
        try:
            if fiche.stat().st_size > MAX_TAILLE_FICHE:
                report.warnings.append(f"{rel} : fiche trop volumineuse, ignorée.")
                continue
            texte = fiche.read_text(encoding="utf-8", errors="replace")
            projet = (await db.execute(select(Project).where(
                Project.user_id == user_id, Project.source_path == rel))).scalars().first()
            if projet is None or projet.source_hash != _empreinte(texte):
                projet = await apply_markdown(db, user_id, texte, project=projet,
                                              fallback_name=fiche.parent.name,
                                              source_path=rel, report=report)
            await _cocher_les_terminees(db, projet, fiche, report)
            await _exporter(db, projet, fiche.parent, report)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"📁 Synchronisation de {rel} en échec : {e}", exc_info=True)
            report.warnings.append(f"{rel} : {e}")
    return report


def _nom_de_dossier(nom: str) -> str:
    """Nom de dossier sûr sur macOS, lisible (accents et espaces conservés)."""
    propre = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "-", nom).strip(" .")
    return propre[:80] or "Nouveau projet"


async def import_markdown_file(db: AsyncSession, user_id: int, filename: str, texte: str) -> Project:
    """Fiche déposée dans l'outil.

    Avec un dossier de projets : elle y devient un dossier-projet, puis se
    synchronise comme les autres. Sans : le projet est créé directement.
    """
    fiche = lire_projet(texte)
    nom = (fiche.titre or Path(filename).stem or "Nouveau projet").strip()
    racine = await user_root(db, user_id)
    if racine is None:
        projet = await apply_markdown(db, user_id, texte, fallback_name=nom)
        await db.commit()
        return projet

    base = _nom_de_dossier(nom)
    dossier, n = racine / base, 2
    while dossier.exists():  # ne jamais écrire dans un dossier existant
        dossier, n = racine / f"{base} {n}", n + 1
    nom_fiche = _nom_de_dossier(Path(filename).stem or base) + ".md"
    _ecrire_atomique(dossier / nom_fiche, texte)
    rel = relative(dossier / nom_fiche)
    projet = await apply_markdown(db, user_id, texte, fallback_name=nom, source_path=rel)
    await db.commit()
    return projet
