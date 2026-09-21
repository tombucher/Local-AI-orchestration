"""
Mémoire de projet — le « carnet » partagé par toutes les actions de l'orchestrateur.

Avant ce module, chaque action (veille, financements, moodboard) ne voyait que le
titre de sa propre tâche : une veille visuelle sans mots-clés cherchait littéralement
« veille visuelle » et ramenait n'importe quoi.

La mémoire est **assemblée à la demande** depuis ce que la base contient déjà
(description du projet, dialogue d'idéation, tâches, curation de l'utilisateur).
Elle n'est pas stockée : elle ne peut donc jamais être périmée, et elle se met à jour
toute seule dès que l'utilisateur garde ou écarte un résultat.

Volumétrie mesurée (sept. 2026) : le projet le plus fourni tient en ~1800 tokens,
pour une fenêtre de 16k–32k. Tout rentre : pas besoin de recherche vectorielle ici.
Le jour où le corpus de veille (déjà 500+ résultats sur un projet) devra être
interrogé, c'est à ce niveau qu'une couche de récupération viendra se brancher.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.veille_result import VeilleResult, VeilleResultStatus
from app.models.veille_topic import VeilleTopic

logger = logging.getLogger(__name__)

MAX_IDEATION_CHARS = 1500
MAX_TASK_TITLES = 12
MAX_CURATION_EXAMPLES = 6

# Mots vides écartés du vocabulaire du projet (scoring lexical)
STOPWORDS = {
    'avec', 'pour', 'dans', 'sans', 'sous', 'cette', 'cette', 'leur', 'plus', 'tout',
    'tous', 'être', 'avoir', 'faire', 'projet', 'création', 'permettant', 'consistant',
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'your', 'about',
}


@dataclass
class ProjectMemory:
    """Ce que l'orchestrateur sait d'un projet à un instant donné."""

    brief: str                                       # Bloc lisible injecté dans les prompts
    vocabulary: List[str] = field(default_factory=list)   # Termes signifiants du projet
    liked: List[str] = field(default_factory=list)        # Titres gardés par l'utilisateur
    disliked: List[str] = field(default_factory=list)     # Titres écartés

    def is_thin(self) -> bool:
        """Vrai si le projet n'a presque rien à dire (brief inexploitable)."""
        return len(self.vocabulary) < 3

    def extend_vocabulary(self, *texts: str) -> None:
        """Enrichit le vocabulaire, typiquement avec les requêtes anglaises générées.

        Le carnet est rédigé en français alors que les banques d'images indexent en
        anglais : sans cet apport, le recouvrement lexical rate presque tout.
        """
        extra: List[str] = []
        for text in texts:
            extra += _significant_words(text, min_length=3)
        self.vocabulary = _dedupe(self.vocabulary + extra, 90)


def _significant_words(text: str, min_length: int = 4) -> List[str]:
    words = re.findall(r"[a-zà-öø-ÿ0-9][\w'’-]{%d,}" % (min_length - 1), (text or '').casefold())
    return [w.strip("'’-") for w in words if w not in STOPWORDS]


def _dedupe(items: List[str], limit: int) -> List[str]:
    seen, out = set(), []
    for item in items:
        key = item.casefold()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _ideation_excerpt(project: Project) -> str:
    """Résumé du dialogue d'idéation : c'est là que l'intention du projet est la plus riche."""
    transcript = project.ideation_transcript
    if not transcript:
        return ''

    messages: List[str] = []
    if isinstance(transcript, list):
        for entry in transcript:
            if isinstance(entry, dict):
                content = (entry.get('content') or entry.get('message') or '').strip()
                # Seules les réponses de l'utilisateur portent son intention
                if content and entry.get('role') in (None, 'user'):
                    messages.append(content)
            elif isinstance(entry, str):
                messages.append(entry.strip())
    elif isinstance(transcript, str):
        messages.append(transcript)

    excerpt = ' — '.join(m for m in messages if m)
    return excerpt[:MAX_IDEATION_CHARS]


async def build_project_memory(
    db: AsyncSession,
    project: Project,
    topic: Optional[VeilleTopic] = None,
) -> ProjectMemory:
    """Assemble le carnet du projet depuis la base.

    `topic` (optionnel) restreint les signaux de curation à cette veille précise.
    """
    lines: List[str] = [f"Projet : {project.name}"]
    vocabulary: List[str] = []

    if project.description:
        description = project.description.strip()
        lines.append(f"Description : {description}")
        vocabulary += _significant_words(description)

    intention = _ideation_excerpt(project)
    if intention:
        lines.append(f"Intention exprimée lors de l'idéation : {intention}")
        vocabulary += _significant_words(intention)

    features = project.features if isinstance(project.features, dict) else {}
    active_features = [key for key, value in features.items() if value]
    if active_features:
        lines.append(f"Volets activés : {', '.join(active_features)}")

    # --- Documents déposés par l'utilisateur --------------------------------
    from app.services.project_documents import load_documents, summarise_for_memory

    docs = await load_documents(db, project.id)
    if docs:
        resume = summarise_for_memory(docs)
        lines.append(resume)
        for doc in docs[:10]:
            vocabulary += _significant_words(f"{doc.name} {doc.note or ''}")

    # --- Ce sur quoi l'utilisateur travaille en ce moment -------------------
    tasks = (await db.execute(
        select(Task)
        .where(Task.project_id == project.id, Task.status != TaskStatus.CANCELLED)
        .order_by(Task.created_at.desc())
        .limit(MAX_TASK_TITLES)
    )).unique().scalars().all()
    if tasks:
        titles = _dedupe([t.title for t in tasks], MAX_TASK_TITLES)
        lines.append("Chantiers en cours : " + " ; ".join(titles))
        for title in titles:
            vocabulary += _significant_words(title)

    # --- Curation : ce que l'utilisateur garde et ce qu'il jette ------------
    # C'est la partie qui « s'auto-mets à jour » : aucun réglage à maintenir,
    # les préférences se déduisent des clics de l'utilisateur.
    curation_query = select(VeilleResult).join(VeilleTopic)
    curation_query = curation_query.where(
        VeilleTopic.id == topic.id if topic is not None else VeilleTopic.project_id == project.id
    )

    liked = (await db.execute(
        curation_query.where(
            VeilleResult.status.in_([VeilleResultStatus.SAVED, VeilleResultStatus.ACTIONABLE])
        ).order_by(VeilleResult.updated_at.desc()).limit(MAX_CURATION_EXAMPLES)
    )).unique().scalars().all()

    disliked = (await db.execute(
        curation_query.where(VeilleResult.status == VeilleResultStatus.DISMISSED)
        .order_by(VeilleResult.updated_at.desc()).limit(MAX_CURATION_EXAMPLES)
    )).unique().scalars().all()

    liked_titles = _dedupe([r.title for r in liked], MAX_CURATION_EXAMPLES)
    disliked_titles = _dedupe([r.title for r in disliked], MAX_CURATION_EXAMPLES)

    if liked_titles:
        lines.append("A retenu ces résultats (viser ce registre) : "
                     + " ; ".join(f"« {t} »" for t in liked_titles))
        for title in liked_titles:
            vocabulary += _significant_words(title)
    if disliked_titles:
        lines.append("A écarté ces résultats (hors-sujet, à ne pas reproduire) : "
                     + " ; ".join(f"« {t} »" for t in disliked_titles))

    # --- Réglages explicites de la veille -----------------------------------
    if topic is not None:
        if topic.description:
            lines.append(f"Objet de cette veille : {topic.description}")
        if topic.keywords:
            lines.append(f"Mots-clés demandés : {', '.join(topic.keywords)}")
            vocabulary += [k.casefold() for k in topic.keywords]
        if topic.excluded_keywords:
            lines.append(f"Termes à exclure : {', '.join(topic.excluded_keywords)}")

    memory = ProjectMemory(
        brief='\n'.join(lines),
        vocabulary=_dedupe(vocabulary, 60),
        liked=liked_titles,
        disliked=disliked_titles,
    )
    if memory.is_thin():
        logger.warning(
            f"🧠 Mémoire pauvre pour le projet {project.id} « {project.name} » "
            f"({len(memory.vocabulary)} termes) — les recherches seront approximatives"
        )
    return memory


def _matches(term: str, haystack: str) -> bool:
    """Présence du terme en mot entier (tolère le pluriel) — évite que « art » matche « smart »."""
    if len(term) < 3:
        return False
    return re.search(r'\b' + re.escape(term) + r's?\b', haystack) is not None


def score_against_memory(
    item: Dict[str, Any],
    memory: ProjectMemory,
    query_terms: Optional[List[List[str]]] = None,
) -> float:
    """Pertinence 0-100 d'un résultat.

    La note se calcule **par requête entière** : on retient la requête la mieux
    couverte, et le score est la part de ses termes distinctifs présents dans le
    titre. Croiser « haiku » ET « poster » vaut donc bien plus que croiser le seul
    mot « light », qui ramenait des lance-roquettes sur une veille lumière.

    Volontairement lexical et non sémantique : instantané et explicable. Un scoring
    LLM image par image serait bien trop lent en local.
    """
    queries = [q for q in (query_terms or []) if q]
    if not queries and not memory.vocabulary:
        return 50.0

    haystack = ' '.join(filter(None, [
        item.get('title', ''), item.get('description', ''),
    ])).casefold()
    if not haystack.strip():
        return 0.0

    # Signal 1 — couverture d'une requête entière : « Haiku Poster » couvre
    # totalement la requête « haiku poster ».
    best = 0.0
    for terms in queries:
        hits = sum(1 for term in terms if _matches(term, haystack))
        if hits:
            best = max(best, hits / len(terms))

    # Signal 2 — nombre de termes distinctifs croisés, toutes requêtes confondues :
    # « Typography Poster » n'épuise aucune requête mais en croise deux termes, ce
    # qui vaut mieux qu'un « Generation Light » accroché au seul mot « light ».
    flat = {term for terms in queries for term in terms}
    distinct_hits = sum(1 for term in flat if _matches(term, haystack))

    # Appoint du vocabulaire général du projet (jamais suffisant à lui seul)
    weak_hits = sum(1 for term in memory.vocabulary if term not in flat and _matches(term, haystack))

    if not best and not distinct_hits and not weak_hits:
        return 0.0

    score = min(95.0, max(95.0 * best, 35.0 * distinct_hits) + 6.0 * weak_hits)

    # Malus si le titre reprend un résultat déjà écarté par l'utilisateur
    title = (item.get('title') or '').casefold()
    if title and any(title in d.casefold() for d in memory.disliked):
        score *= 0.4

    return round(score, 1)
