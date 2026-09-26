"""
Rassemble ce qu'un projet a produit : ses fichiers de code, ses documents, ses veilles.

Sans cela, le résultat d'un projet restait éparpillé dans ses tâches et il fallait
le reconstituer à la main par copier-coller, fichier par fichier.
"""

import io
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType
from app.models.veille_result import VeilleResult, VeilleResultStatus
from app.services.code_contract import check_coherence
from app.services.project_workspace import build_file_plan
from app.services.task_chain import RESULT_TYPES

# Une tâche transverse (intégration, relecture) rend plusieurs fichiers ainsi
# Tout marqueur est reconnu, même au chemin douteux : sinon son contenu se collait
# au fichier précédent. Les chemins refusés par safe_path sont ensuite écartés.
_MULTI_FILE = re.compile(r"^===\s*(\S[^=\n]*?)\s*===\s*$", re.MULTILINE)

TEXT_TYPES = {TaskType.DOCUMENT_WRITING, TaskType.RESEARCH, TaskType.ADMINISTRATIVE}


@dataclass
class ProducedFile:
    path: str
    content: str
    task_id: int
    task_title: str
    kind: str  # "code", "document", "veille"


@dataclass
class ProjectFiles:
    code: List[ProducedFile] = field(default_factory=list)
    documents: List[ProducedFile] = field(default_factory=list)
    coherence: List[str] = field(default_factory=list)

    @property
    def all(self) -> List[ProducedFile]:
        return self.code + self.documents


def safe_path(path: Optional[str]) -> Optional[str]:
    """Chemin relatif sans remontée : le modèle écrit les chemins, pas nous."""
    if not path:
        return None
    clean = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
    if clean in ("", ".") or clean.startswith("..") or "/../" in f"/{clean}/":
        return None
    return clean


def split_multi_file(code: str) -> Dict[str, str]:
    """Découpe une sortie `=== chemin ===` en fichiers ; vide si ce n'en est pas une."""
    marks = list(_MULTI_FILE.finditer(code or ""))
    files = {}
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(code)
        body = code[mark.end():end].strip("\n")
        path = safe_path(mark.group(1))
        if body.strip() and path:
            files[path] = body + "\n"
    return files


def _slug(text: str, max_length: int = 60) -> str:
    text = re.sub(r"[^\w\s-]", "", (text or "").lower(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", text).strip("-")[:max_length] or "sans-titre"


def _veille_markdown(task: Task, results: List[VeilleResult]) -> str:
    lines = [f"# {task.title}", ""]
    if (task.generated_code or "").strip():
        lines += [task.generated_code.strip(), ""]
    if results:
        lines += ["## Résultats", ""]
        for r in results:
            ligne = f"- **{r.title.strip()}**"
            if r.deadline:
                ligne += f" (date limite : {r.deadline:%d/%m/%Y})"
            if r.url:
                ligne += f" — {r.url}"
            lines.append(ligne)
            resume = (r.ai_summary or r.description or "").strip()
            if resume and resume != r.title.strip():
                lines.append(f"  {resume[:400]}")
    return "\n".join(lines) + "\n"


async def collect_project_files(db: AsyncSession, project: Project) -> ProjectFiles:
    tasks = (await db.execute(
        select(Task).where(Task.project_id == project.id,
                           Task.status != TaskStatus.CANCELLED).order_by(Task.id)
    )).unique().scalars().all()

    files = ProjectFiles()

    # --- Code : le plan de fichiers, puis les retouches des tâches transverses
    code_tasks = [t for t in tasks if t.task_type == TaskType.CODE_GENERATION]
    plan = build_file_plan(code_tasks)
    by_path: Dict[str, ProducedFile] = {}
    for task in code_tasks:
        code = (task.generated_code or "").strip()
        if not code:
            continue
        path = safe_path((task.task_metadata or {}).get("artifact_path") or plan.get(task.id))
        if path:
            by_path[path] = ProducedFile(path, code + "\n", task.id, task.title, "code")
        else:
            for sub_path, body in split_multi_file(code).items():
                by_path[sub_path] = ProducedFile(sub_path, body, task.id, task.title, "code")
    files.code = sorted(by_path.values(), key=lambda f: f.path)

    # --- Textes et veilles, numérotés dans l'ordre du projet
    rang = 0
    for task in tasks:
        if task.task_type in RESULT_TYPES:
            results = (await db.execute(
                select(VeilleResult).where(VeilleResult.task_id == task.id,
                                           VeilleResult.status != VeilleResultStatus.DISMISSED)
                .order_by(VeilleResult.relevance_score.desc())
            )).scalars().all()
            if not results and not (task.generated_code or "").strip():
                continue
            rang += 1
            files.documents.append(ProducedFile(
                f"veille/{rang:02d}-{_slug(task.title)}.md",
                _veille_markdown(task, list(results)), task.id, task.title, "veille"))
        elif task.task_type in TEXT_TYPES and (task.generated_code or "").strip():
            rang += 1
            files.documents.append(ProducedFile(
                f"documents/{rang:02d}-{_slug(task.title)}.md",
                f"# {task.title}\n\n{task.generated_code.strip()}\n", task.id, task.title, "document"))

    files.coherence = check_coherence({f.path: f.content for f in files.code})
    return files


def _readme(project: Project, files: ProjectFiles) -> str:
    lines = [f"# {project.name}", ""]
    if project.description:
        lines += [project.description.strip(), ""]
    lines.append(f"Exporté le {datetime.now(timezone.utc):%d/%m/%Y à %H:%M} UTC depuis l'Orchestrateur IA.")
    if files.code:
        lines += ["", "## Code", ""]
        lines += [f"- `{f.path}` — {f.task_title}" for f in files.code]
        if any(f.path.endswith((".html", ".htm")) for f in files.code):
            lines += ["", "Ouvre `index.html` dans un navigateur pour voir le site."]
    if files.documents:
        lines += ["", "## Documents et veilles", ""]
        lines += [f"- `{f.path}` — {f.task_title}" for f in files.documents]
    if files.coherence:
        lines += ["", "## Liens à vérifier entre les fichiers", ""]
        lines += [f"- {w}" for w in files.coherence]
    return "\n".join(lines) + "\n"


def build_zip(project: Project, files: ProjectFiles) -> bytes:
    buffer = io.BytesIO()
    racine = _slug(project.name, 40)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{racine}/README.md", _readme(project, files))
        for f in files.all:
            archive.writestr(f"{racine}/{f.path}", f.content)
    return buffer.getvalue()


def zip_filename(project: Project) -> str:
    return f"{_slug(project.name, 40)}.zip"


def entry_page(files: ProjectFiles) -> Optional[str]:
    """La page d'entrée du site, si le projet en a une."""
    pages = [f.path for f in files.code if f.path.endswith((".html", ".htm"))]
    if not pages:
        return None
    return "index.html" if "index.html" in pages else pages[0]
