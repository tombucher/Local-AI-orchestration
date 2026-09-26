"""
Lecture et mise à jour de la fiche .md d'un projet.

Format — libre et structuré combinables dans un même fichier :

    # Tickets de veille                      ← nom du projet (sinon : nom du dossier)

    Texte libre : décrit le projet.          ← description du projet

    ## Note d'intention                      ← une tâche (## [x] = terminée)
    type: document · échéance: 15/10 · après: Veille visuelle
    Consigne libre de la tâche.
    - [ ] Origine du projet                  ← sous-tâches (sections du document)
    - [ ] Dispositif technique

Clés reconnues sur la ligne qui suit le titre (séparées par « · » ou « | ») :
type, échéance, après, priorité, fichier, mots-clés, fréquence.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Dict, List, Optional, Tuple

from app.models.task import TaskPriority, TaskType

# type: … → (type de tâche, métadonnées)
TYPES: Dict[str, Tuple[TaskType, dict]] = {
    "code": (TaskType.CODE_GENERATION, {}),
    "document": (TaskType.DOCUMENT_WRITING, {}),
    "texte": (TaskType.DOCUMENT_WRITING, {}),
    "redaction": (TaskType.DOCUMENT_WRITING, {}),
    "rapport": (TaskType.DOCUMENT_WRITING, {"document_type": "rapport"}),
    "veille": (TaskType.VEILLE, {"scope": "news"}),
    "veille actualite": (TaskType.VEILLE, {"scope": "news"}),
    "veille visuelle": (TaskType.VEILLE, {"scope": "visual"}),
    "moodboard": (TaskType.VEILLE, {"scope": "visual"}),
    "veille culturelle": (TaskType.VEILLE, {"scope": "cultural"}),
    "veille tech": (TaskType.VEILLE, {"scope": "tech"}),
    "financement": (TaskType.FUNDING_SEARCH, {}),
    "financements": (TaskType.FUNDING_SEARCH, {}),
    "appels a projets": (TaskType.FUNDING_SEARCH, {}),
    "recherche": (TaskType.RESEARCH, {}),
    "administratif": (TaskType.ADMINISTRATIVE, {}),
    "admin": (TaskType.ADMINISTRATIVE, {}),
}

PRIORITES = {
    "haute": TaskPriority.P1, "urgente": TaskPriority.P1, "p1": TaskPriority.P1,
    "normale": TaskPriority.P2, "p2": TaskPriority.P2,
    "basse": TaskPriority.P3, "p3": TaskPriority.P3,
}

FREQUENCES = {
    "une fois": "once", "once": "once", "ponctuelle": "once",
    "quotidienne": "daily", "jour": "daily", "daily": "daily",
    "hebdo": "weekly", "hebdomadaire": "weekly", "semaine": "weekly", "weekly": "weekly",
    "mensuelle": "monthly", "mois": "monthly", "monthly": "monthly",
}

CLES = {"type", "echeance", "apres", "priorite", "fichier", "mots-cles", "motscles", "frequence"}

_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_H2 = re.compile(r"^##\s+(?:\[([ xX])\]\s+)?(.+?)\s*#*\s*$")
_SEPARATEUR_META = re.compile(r"\s*[·|]\s*")
_META = re.compile(r"^\s*([\w\- ]+?)\s*:\s*(.+?)\s*$")


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def cle_titre(titre: str) -> str:
    """Clé de correspondance entre un ## du fichier et une tâche."""
    return re.sub(r"\s+", " ", sans_accents(titre).lower()).strip(" .:")


def _cle_meta(cle: str) -> str:
    return sans_accents(cle).lower().replace(" ", "").replace("é", "e")


@dataclass
class TacheMd:
    titre: str
    ligne: int                       # index de la ligne ## dans le fichier
    fait: bool = False
    type_explicite: Optional[str] = None
    task_type: TaskType = TaskType.DOCUMENT_WRITING
    metadata: dict = field(default_factory=dict)
    echeance: Optional[datetime] = None
    apres: List[str] = field(default_factory=list)
    priorite: TaskPriority = TaskPriority.P2
    description: str = ""
    erreurs: List[str] = field(default_factory=list)

    @property
    def cle(self) -> str:
        return cle_titre(self.titre)


@dataclass
class ProjetMd:
    titre: Optional[str]
    description: str
    taches: List[TacheMd]
    erreurs: List[str] = field(default_factory=list)


def lire_echeance(valeur: str, aujourd_hui: Optional[date] = None) -> Optional[datetime]:
    """15/10, 15/10/2026, 15.10.26, 2026-10-15 → datetime (fin de journée, UTC)."""
    aujourd_hui = aujourd_hui or date.today()
    valeur = valeur.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", valeur)
    if m:
        a, mo, j = int(m[1]), int(m[2]), int(m[3])
    else:
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", valeur)
        if not m:
            return None
        j, mo = int(m[1]), int(m[2])
        if m[3]:
            a = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
        else:
            # Sans année : la prochaine occurrence de cette date
            a = aujourd_hui.year
            try:
                if date(a, mo, j) < aujourd_hui:
                    a += 1
            except ValueError:
                return None
    try:
        return datetime.combine(date(a, mo, j), time(18, 0), tzinfo=timezone.utc)
    except ValueError:
        return None


def deviner_type(titre: str, description: str) -> Tuple[TaskType, dict]:
    """Sans « type: », on devine d'après le titre — comme on le ferait à la lecture."""
    texte = sans_accents(f"{titre} {description}").lower()
    if re.search(r"moodboard|veille visuelle|references? visuelles?", texte):
        return TaskType.VEILLE, {"scope": "visual"}
    if re.search(r"\bveille\b", texte):
        return TaskType.VEILLE, {"scope": "news"}
    if re.search(r"financement|appels? a (projets|candidatures)|residences?\b|subvention", texte):
        return TaskType.FUNDING_SEARCH, {}
    if re.search(r"\b(html|css|javascript|js|code|script|site|page web|interface)\b", texte):
        return TaskType.CODE_GENERATION, {}
    if re.search(r"\betat de l'art\b|\brecherche\b", texte):
        return TaskType.RESEARCH, {}
    if re.search(r"administrati|checklist|inscription|facture|envoi", texte):
        return TaskType.ADMINISTRATIVE, {}
    return TaskType.DOCUMENT_WRITING, {}


def _lire_meta(ligne: str) -> Optional[Dict[str, str]]:
    """La ligne est-elle entièrement faite de « clé: valeur » reconnues ?"""
    morceaux = [m for m in _SEPARATEUR_META.split(ligne.strip()) if m]
    meta = {}
    for morceau in morceaux:
        m = _META.match(morceau)
        if not m or _cle_meta(m[1]) not in CLES:
            return None
        meta[_cle_meta(m[1])] = m[2]
    return meta or None


def _appliquer_meta(tache: TacheMd, meta: Dict[str, str], aujourd_hui: Optional[date]) -> None:
    for cle, valeur in meta.items():
        if cle == "type":
            connu = TYPES.get(cle_titre(valeur))
            if connu:
                tache.type_explicite = valeur
                tache.task_type, extra = connu
                tache.metadata.update(extra)
            else:
                tache.erreurs.append(f"type inconnu « {valeur} »")
        elif cle == "echeance":
            tache.echeance = lire_echeance(valeur, aujourd_hui)
            if not tache.echeance:
                tache.erreurs.append(f"échéance illisible « {valeur} »")
        elif cle == "apres":
            tache.apres = [t.strip() for t in re.split(r"\s*[,;]\s*", valeur) if t.strip()]
        elif cle == "priorite":
            tache.priorite = PRIORITES.get(cle_titre(valeur), TaskPriority.P2)
        elif cle == "fichier":
            tache.metadata["artifact_path"] = valeur.strip("`'\" ")
        elif cle in ("mots-cles", "motscles"):
            tache.metadata["keywords"] = [k.strip() for k in re.split(r"\s*[,;]\s*", valeur) if k.strip()]
        elif cle == "frequence":
            tache.metadata["frequency"] = FREQUENCES.get(cle_titre(valeur), "once")


def lire_projet(texte: str, aujourd_hui: Optional[date] = None) -> ProjetMd:
    lignes = texte.replace("\r\n", "\n").split("\n")
    titre = None
    description: List[str] = []
    taches: List[TacheMd] = []
    courante: Optional[TacheMd] = None
    corps: List[str] = []
    attend_meta = False
    dans_code = False

    def clore():
        if courante is not None:
            courante.description = "\n".join(corps).strip()
            if not courante.type_explicite:
                courante.task_type, extra = deviner_type(courante.titre, courante.description)
                courante.metadata = {**extra, **courante.metadata}
            taches.append(courante)

    for i, ligne in enumerate(lignes):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
        if not dans_code:
            h2 = _H2.match(ligne)
            if h2:
                clore()
                courante = TacheMd(titre=h2[2].strip(), ligne=i, fait=(h2[1] or "").lower() == "x")
                corps = []
                attend_meta = True
                continue
            h1 = _H1.match(ligne)
            if h1 and titre is None and courante is None:
                titre = h1[1].strip()
                continue
        if courante is None:
            description.append(ligne)
            continue
        if attend_meta and ligne.strip():
            attend_meta = False
            meta = _lire_meta(ligne)
            if meta:
                _appliquer_meta(courante, meta, aujourd_hui)
                continue
        corps.append(ligne)
    clore()

    projet = ProjetMd(titre=titre, description="\n".join(description).strip(), taches=taches)

    # Doublons : la seconde tâche du même nom serait indiscernable de la première
    vues = set()
    for t in list(taches):
        if t.cle in vues:
            projet.erreurs.append(f"Tâche « {t.titre} » en double : seule la première est prise en compte.")
            taches.remove(t)
        vues.add(t.cle)

    # « après: » doit désigner une tâche du fichier
    cles = {t.cle: t for t in taches}
    for t in taches:
        resolues = []
        for nom in t.apres:
            cible = cles.get(cle_titre(nom)) or next(
                (c for k, c in cles.items() if k.startswith(cle_titre(nom))), None)
            if cible and cible is not t:
                resolues.append(cible.titre)
            else:
                t.erreurs.append(f"« après: {nom} » ne correspond à aucune tâche du fichier")
        t.apres = resolues
    for t in taches:
        projet.erreurs += [f"{t.titre} : {e}" for e in t.erreurs]
    return projet


def cocher_tache(texte: str, titre: str) -> Optional[str]:
    """Coche le ## de la tâche (## [x] Titre). None si introuvable ou déjà cochée."""
    lignes = texte.split("\n")
    cible = cle_titre(titre)
    dans_code = False
    for i, ligne in enumerate(lignes):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
        if dans_code:
            continue
        h2 = _H2.match(ligne.rstrip("\r"))
        if h2 and cle_titre(h2[2]) == cible:
            if (h2[1] or "").lower() == "x":
                return None
            fin = "\r" if ligne.endswith("\r") else ""
            lignes[i] = f"## [x] {h2[2].strip()}{fin}"
            return "\n".join(lignes)
    return None


# ------------------------------------------------------------- écriture --
# Inverse de lire_projet : une fiche écrite depuis l'outil doit se relire à
# l'identique, sinon la synchronisation suivante déformerait le projet.

# type de tâche (+ portée de veille) → libellé de la ligne « type: »
LIBELLES_TYPE = {
    (TaskType.CODE_GENERATION, None): "code",
    (TaskType.DOCUMENT_WRITING, None): "document",
    (TaskType.VEILLE, "news"): "veille",
    (TaskType.VEILLE, "visual"): "veille visuelle",
    (TaskType.VEILLE, "cultural"): "veille culturelle",
    (TaskType.VEILLE, "tech"): "veille tech",
    (TaskType.FUNDING_SEARCH, None): "financement",
    (TaskType.RESEARCH, None): "recherche",
    (TaskType.ADMINISTRATIVE, None): "administratif",
}
LIBELLES_FREQUENCE = {"daily": "quotidienne", "weekly": "hebdo", "monthly": "mensuelle"}
_TITRE_A_ABAISSER = re.compile(r"^(#{1,2})(\s)", re.MULTILINE)


def _abaisser_titres(texte: str) -> str:
    """Un « ## » dans une description deviendrait une tâche à la relecture."""
    lignes, dans_code = [], False
    for ligne in (texte or "").split("\n"):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
        lignes.append(ligne if dans_code else _TITRE_A_ABAISSER.sub(r"###\2", ligne))
    return "\n".join(lignes).strip()


@dataclass
class TacheAEcrire:
    titre: str
    fait: bool
    task_type: TaskType
    metadata: dict
    description: str = ""
    echeance: Optional[datetime] = None
    apres: List[str] = field(default_factory=list)
    priorite: TaskPriority = TaskPriority.P2
    mots_cles: List[str] = field(default_factory=list)


def _libelle_type(t: TacheAEcrire) -> Optional[str]:
    scope = t.metadata.get("scope") if t.task_type in (TaskType.VEILLE, TaskType.VEILLE_TECH,
                                                        TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS) else None
    if t.task_type in (TaskType.VEILLE_TECH,):
        scope = "tech"
    elif t.task_type in (TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS):
        scope = "cultural"
    if t.task_type == TaskType.VEILLE and scope not in ("visual", "cultural", "tech"):
        scope = "news"  # sans portée, une veille relue passerait pour un document
    type_normal = TaskType.VEILLE if scope else t.task_type
    return LIBELLES_TYPE.get((type_normal, scope)) or LIBELLES_TYPE.get((type_normal, None))


def ecrire_projet(titre: str, description: Optional[str], taches: List[TacheAEcrire]) -> str:
    morceaux = [f"# {titre.strip()}", ""]
    if (description or "").strip():
        morceaux += [_abaisser_titres(description), ""]
    for t in taches:
        morceaux.append(f"## {'[x] ' if t.fait else ''}{t.titre.strip()}")
        meta = []
        libelle = _libelle_type(t)
        if libelle:
            meta.append(f"type: {libelle}")
        if t.echeance:
            meta.append(f"échéance: {t.echeance:%d/%m/%Y}")
        if t.apres:
            meta.append("après: " + ", ".join(a.strip() for a in t.apres))
        if t.priorite == TaskPriority.P1:
            meta.append("priorité: haute")
        elif t.priorite == TaskPriority.P3:
            meta.append("priorité: basse")
        if t.metadata.get("artifact_path") and t.task_type == TaskType.CODE_GENERATION:
            meta.append(f"fichier: {t.metadata['artifact_path']}")
        if t.mots_cles:
            meta.append("mots-clés: " + ", ".join(t.mots_cles))
        frequence = LIBELLES_FREQUENCE.get(t.metadata.get("frequency") or "")
        if frequence:
            meta.append(f"fréquence: {frequence}")
        if meta:
            morceaux.append(" · ".join(meta))
        corps = _abaisser_titres(t.description)
        if corps:
            morceaux.append(corps)
        morceaux.append("")
    return "\n".join(morceaux).rstrip() + "\n"
