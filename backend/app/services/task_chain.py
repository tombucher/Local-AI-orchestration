"""
Transmission des résultats d'une tâche à celles qui en dépendent.

Le plan de fichiers (`project_workspace`) relie les tâches de code entre elles.
Il manquait le reste de la chaîne : une note d'intention qui s'appuie sur une
recherche, un rapport qui synthétise une veille, une page HTML qui reprend un
texte rédigé. Sans ce contexte, chaque tâche rédigeait à partir du seul nom du
projet et produisait un texte générique.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskType, task_dependencies
from app.models.veille_result import VeilleResult, VeilleResultStatus

MAX_UPSTREAM_CHARS = 10000
MAX_CHARS_PER_TASK = 4000
MAX_RESULTS_PER_VEILLE = 8

VEILLE_TYPES = {TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS}
# La recherche de financements range ses appels comme des résultats de veille ; son
# texte se résume à « 7 opportunités trouvées », inutilisable par un dossier.
RESULT_TYPES = VEILLE_TYPES | {TaskType.FUNDING_SEARCH}

_CHECKLIST = re.compile(r"^\s*[-*]\s*\[[ xX]?\]\s*(.+?)\s*$", re.MULTILINE)


def checklist_items(description: Optional[str]) -> List[str]:
    """Sous-tâches écrites en cases à cocher (`- [ ] …`) dans une description."""
    return [item for item in _CHECKLIST.findall(description or "") if item]


def brief_without_checklist(description: Optional[str]) -> str:
    """La description sans ses cases à cocher, qui sont traitées à part."""
    return _CHECKLIST.sub("", description or "").strip()


async def _veille_digest(db: AsyncSession, task: Task) -> str:
    """Les meilleurs résultats d'une veille, ceux mis de côté par l'utilisateur d'abord."""
    results = (await db.execute(
        select(VeilleResult)
        .where(VeilleResult.task_id == task.id,
               VeilleResult.status != VeilleResultStatus.DISMISSED)
    )).scalars().all()
    if not results:
        return ""

    maintenant = datetime.now(timezone.utc)

    def clos(r) -> bool:
        if not r.deadline:
            return False
        echeance = r.deadline if r.deadline.tzinfo else r.deadline.replace(tzinfo=timezone.utc)
        return echeance < maintenant

    # Un appel clos ne sert plus à rien : ceux encore ouverts passent devant
    results = sorted(
        results,
        key=lambda r: (clos(r), r.status != VeilleResultStatus.SAVED, -(r.relevance_score or 0)),
    )[:MAX_RESULTS_PER_VEILLE]

    lines = []
    for r in results:
        resume = (r.ai_summary or r.description or "").strip().replace("\n", " ")[:240]
        ligne = f"- {r.title.strip()}"
        if r.deadline:
            ligne += f" [{'CLOS le' if clos(r) else 'date limite'} {r.deadline:%d/%m/%Y}]"
        if resume and resume != r.title.strip():
            ligne += f" — {resume}"
        if r.url:
            ligne += f" ({r.url})"
        lines.append(ligne)
    return "\n".join(lines)


async def build_upstream_context(
    db: AsyncSession, task: Task, max_chars: int = MAX_UPSTREAM_CHARS,
    skip_code: bool = False,
) -> str:
    """Ce que les tâches dont `task` dépend ont produit, prêt à injecter dans un prompt.

    `skip_code` : les tâches de code reçoivent déjà le code de leurs dépendances
    par le plan de fichiers ; inutile de le leur répéter.
    """
    dep_ids = (await db.execute(
        select(task_dependencies.c.depends_on_id).where(task_dependencies.c.task_id == task.id)
    )).scalars().all()
    if not dep_ids:
        return ""

    deps = (await db.execute(
        select(Task).where(Task.id.in_(dep_ids)).order_by(Task.id)
    )).unique().scalars().all()

    budget = max_chars
    blocks: List[str] = []
    for dep in deps:
        if skip_code and dep.task_type == TaskType.CODE_GENERATION:
            continue
        if budget <= 0:
            break

        if dep.task_type in RESULT_TYPES:
            body = "\n\n".join(filter(None, [
                (dep.generated_code or "").strip() if dep.task_type == TaskType.FUNDING_SEARCH else "",
                await _veille_digest(db, dep),
            ]))
        else:
            body = (dep.generated_code or "").strip()

        if not body:
            body = "(Cette tâche n'a encore rien produit : ne suppose pas son contenu.)"

        limit = min(MAX_CHARS_PER_TASK, budget)
        if len(body) > limit:
            body = body[:limit] + "\n… (tronqué)"
        budget -= len(body)
        blocks.append(f"### {dep.title}\n{body}")

    if not blocks:
        return ""
    return (
        "## Résultats des tâches précédentes\n"
        "Appuie-toi sur ces matériaux : reprends leurs faits, noms et références "
        "plutôt que d'en inventer.\n\n" + "\n\n".join(blocks)
    )
