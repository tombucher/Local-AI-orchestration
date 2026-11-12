"""
La réponse écrite sur une tâche fait évoluer la description du projet.

Cas du 12/11/2026 : la fiche disait « À préciser : zone géographique, montants
visés, acheteurs privilégiés ». L'utilisateur a répondu sur la tâche « Préciser
le périmètre de la veille », la veille a suivi… mais la description du projet,
en tête de sa fiche et de la page, demandait toujours les mêmes précisions.
Pour lui, « la fiche n'est pas mise à jour ». Ici, la réponse est intégrée à
la description : ce qui était à préciser l'est, le reste ne bouge pas.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models.project import Project
from app.models.task import Task

logger = logging.getLogger(__name__)

MAX_DESCRIPTION = 4000
MAX_HISTORIQUE = 10


def prompt_description(project: Project, task: Task, notes: str) -> str:
    extrait = (task.generated_code or "").strip()[:1500]
    return f"""Un projet est décrit en quelques paragraphes dans sa fiche. Une de ses tâches posait des questions ; l'utilisateur vient d'y répondre. Réécris la description pour qu'elle tienne compte de la réponse.

DESCRIPTION ACTUELLE :
{(project.description or '').strip() or '(vide)'}

TÂCHE « {task.title} » — ce qu'elle demandait (extrait) :
{extrait or '(pas de texte)'}

RÉPONSE DE L'UTILISATEUR :
{notes.strip()}

RÈGLES :
- Garde le texte tel quel partout où la réponse ne le concerne pas : mêmes phrases, même ton, même longueur à peu près.
- Là où la description dit qu'un point reste à préciser, à définir ou à choisir, et que la réponse le précise, remplace la question par la réponse, en une ou deux phrases.
- N'invente rien : chaque fait ajouté vient de la réponse.
- Pas de titre, pas de liste de tâches, pas de commentaire : uniquement la nouvelle description, en français."""


async def proposer_description(project: Project, task: Task, notes: str) -> str:
    """Demande au modèle rapide la description réécrite."""
    from app.services.modules.analyzer import AnalyzerModule

    analyzer = AnalyzerModule()
    texte = await analyzer._generate_text_async(
        prompt_description(project, task, notes), model=analyzer._FAST_FALLBACK_MODEL
    )
    texte = re.sub(r"<think>.*?</think>", "", texte or "", flags=re.DOTALL).strip()
    return texte.strip("`").strip()


def integrer_sans_modele(description: str, task: Task, notes: str) -> str:
    """Sans modèle : la réponse est ajoutée telle quelle, datée, à la fin."""
    date = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    ajout = f"Précisé le {date} (réponse à « {task.title} ») : {notes.strip()}"
    return f"{description.rstrip()}\n\n{ajout}" if description.strip() else ajout


def _acceptable(proposition: str, actuelle: str) -> bool:
    """Une réécriture, pas un autre texte : ni vide, ni démesurée, ni sectionnée."""
    if not proposition.strip() or len(proposition) > MAX_DESCRIPTION:
        return False
    if re.search(r"^#{1,2}\s", proposition, re.MULTILINE):
        return False
    return len(proposition) <= max(3 * len(actuelle), 1500)


async def appliquer_reponse_au_projet(db, project: Project, task: Task) -> Dict:
    """Intègre la réponse écrite sur `task` à la description de son projet.

    Idempotent : la même réponse, depuis la même tâche, n'est pas réappliquée.
    Sans modèle, la réponse est ajoutée datée à la fin de la description.
    """
    notes = (task.user_notes or "").strip()
    actuelle = (project.description or "").strip()
    historique = list(project.description_history or [])
    derniere = historique[-1] if historique else {}
    if derniere.get("source_task_id") == task.id and (derniere.get("user_notes") or "") == notes:
        return {"description": actuelle, "previous": derniere.get("previous"), "unchanged": True,
                "mode": derniere.get("mode")}

    try:
        proposition = await proposer_description(project, task, notes)
        if not _acceptable(proposition, actuelle):
            raise ValueError("proposition inutilisable")
        mode = "modele"
    except Exception as e:
        logger.warning(f"Projet {project.id} : description non réécrite par le modèle ({e}), réponse ajoutée")
        proposition, mode = integrer_sans_modele(actuelle, task, notes), "ajout"

    historique.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "source_task_id": task.id, "user_notes": notes,
        "previous": actuelle, "mode": mode,
    })
    project.description_history = historique[-MAX_HISTORIQUE:]
    changee = proposition.strip() != actuelle
    if changee:
        project.description = proposition.strip()
    return {"description": (project.description or "").strip(), "previous": actuelle,
            "unchanged": not changee, "mode": mode}
