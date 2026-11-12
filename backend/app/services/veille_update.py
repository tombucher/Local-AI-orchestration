"""
Faire évoluer les veilles d'un projet à partir de ce que l'utilisateur répond.

Cas rencontré : une tâche « Préciser le périmètre de la veille » pose des
questions (zone géographique, types de prestations, seuils de montant).
L'utilisateur a les réponses, mais la veille hebdomadaire continuait à
chercher avec ses mots-clés d'origine. Ici, la réponse écrite sur la tâche
est traduite en mots-clés à ajouter, à retirer ou à exclure, inscrite dans
l'historique d'affinage (que la génération des requêtes lit déjà), et la
prochaine occurrence est avancée à tout de suite.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.veille_topic import VeilleTopic

logger = logging.getLogger(__name__)

MAX_KEYWORDS = 8


def prompt_evolution(topic: VeilleTopic, notes: str, resultat: Optional[str]) -> str:
    extrait = (resultat or "").strip()[:1500]
    return f"""Une veille automatique cherche chaque semaine des pages web avec des mots-clés. L'utilisateur vient de préciser ce qu'il veut. Adapte les mots-clés.

VEILLE « {topic.name} » ({topic.scope.value if hasattr(topic.scope, 'value') else topic.scope})
Mots-clés actuels : {json.dumps(topic.keywords or [], ensure_ascii=False)}
Termes exclus actuels : {json.dumps(topic.excluded_keywords or [], ensure_ascii=False)}

CE QUE LA TÂCHE AVAIT DEMANDÉ (extrait) :
{extrait or '(pas de texte)'}

RÉPONSE DE L'UTILISATEUR :
{notes.strip()}

RÈGLES :
- Un mot-clé est une expression de recherche de 2 à 5 mots, telle qu'elle apparaît dans les pages visées (ex. « marché public identité visuelle », « appel d'offres site internet mairie »), en français.
- Ajoute ce que la réponse rend nécessaire (lieux, types de prestations, acheteurs, seuils), retire ce qu'elle contredit ou juge secondaire, exclus ce qu'elle écarte explicitement.
- {MAX_KEYWORDS} mots-clés au maximum après modification : préfère remplacer qu'empiler.
- Ne change rien d'autre que ce que la réponse justifie.

RÉPONDS UNIQUEMENT EN JSON :
{{"add_keywords": ["…"], "remove_keywords": ["…"], "add_excluded": ["…"]}}"""


async def proposer_evolution(topic: VeilleTopic, notes: str, resultat: Optional[str]) -> Dict[str, List[str]]:
    """Demande au modèle rapide les mots-clés à ajouter, retirer, exclure."""
    from app.services.modules.analyzer import AnalyzerModule
    from app.services.project_analyzer import ProjectAnalyzer

    analyzer = AnalyzerModule()
    reponse = await analyzer._generate_text_async(
        prompt_evolution(topic, notes, resultat), model=analyzer._FAST_FALLBACK_MODEL
    )
    data = ProjectAnalyzer._parse_json_lenient(reponse.strip()) or {}
    nettoyer = lambda cle: [str(k).strip() for k in (data.get(cle) or []) if str(k).strip()][:MAX_KEYWORDS]
    return {"add_keywords": nettoyer("add_keywords"), "remove_keywords": nettoyer("remove_keywords"),
            "add_excluded": nettoyer("add_excluded")}


def appliquer(topic: VeilleTopic, proposition: Dict[str, List[str]], notes: str, source_task_id: int) -> Dict:
    """Applique une proposition à un sujet de veille et avance sa prochaine occurrence."""
    keywords = list(topic.keywords or [])
    excluded = list(topic.excluded_keywords or [])
    retires = [k for k in proposition.get("remove_keywords", []) if k in keywords]
    keywords = [k for k in keywords if k not in retires]
    ajoutes = [k for k in proposition.get("add_keywords", []) if k not in keywords]
    keywords = (keywords + ajoutes)[:MAX_KEYWORDS]
    ajoutes = [k for k in ajoutes if k in keywords]
    exclus = [k for k in proposition.get("add_excluded", []) if k not in excluded]
    excluded += exclus

    topic.keywords = keywords
    topic.excluded_keywords = excluded
    history = list(topic.refinement_history or [])
    history.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "add_keywords": ajoutes,
        "remove_keywords": retires,
        "add_excluded": exclus,
        "remove_excluded": [],
        "user_notes": notes.strip(),
        "source_task_id": source_task_id,
    })
    topic.refinement_history = history
    # La prochaine occurrence part au prochain passage du planificateur (≤ 15 min)
    topic.next_scan = datetime.now(timezone.utc)
    return {
        "topic_id": topic.id, "name": topic.name,
        "keywords": keywords, "excluded_keywords": excluded,
        "added": ajoutes, "removed": retires, "excluded": exclus, "unchanged": False,
    }


async def appliquer_notes_aux_veilles(db: AsyncSession, task: Task) -> List[Dict]:
    """Traduit la réponse écrite sur `task` dans chaque veille active de son projet."""
    notes = (task.user_notes or "").strip()
    topics = (await db.execute(
        select(VeilleTopic).where(VeilleTopic.project_id == task.project_id, VeilleTopic.enabled == True)  # noqa: E712
    )).scalars().all()
    resultats = []
    for topic in topics:
        # Même réponse déjà appliquée depuis cette tâche : on ne refait pas
        # travailler le modèle (chaque passage faisait dériver les mots-clés)
        derniere = (topic.refinement_history or [None])[-1] or {}
        if derniere.get("source_task_id") == task.id and (derniere.get("user_notes") or "").strip() == notes:
            resultats.append({
                "topic_id": topic.id, "name": topic.name,
                "keywords": list(topic.keywords or []), "excluded_keywords": list(topic.excluded_keywords or []),
                "added": [], "removed": [], "excluded": [], "unchanged": True,
            })
            continue
        try:
            proposition = await proposer_evolution(topic, notes, task.generated_code)
        except Exception as e:
            # Sans modèle, la note entre quand même dans l'historique : la
            # génération des requêtes la lit à chaque occurrence
            logger.warning(f"Veille {topic.id} : proposition impossible ({e}), note seule enregistrée")
            proposition = {}
        resultats.append(appliquer(topic, proposition, notes, task.id))
    await db.flush()
    return resultats
