"""
Service d'analyse intelligente de projets avec IA.
Analyse les descriptions de projets pour suggérer des tâches, veilles, et détecter les blocages.
"""

import asyncio
import json
from app.services.model_registry import resolve_model, think_kwargs
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, insert
from ollama import Client

from app.models.task import Task, TaskPriority, TaskStatus, TaskType, task_dependencies
from app.models.project import Project

logger = logging.getLogger(__name__)


# ============================================================
# SCHEMAS PYDANTIC
# ============================================================

class SubTask(BaseModel):
    """Sous-tâche dans une checklist textuelle."""
    description: str
    estimated_hours: Optional[int] = None


class AnalysisError(RuntimeError):
    """L'analyse LLM n'a pas pu produire de résultat exploitable."""


class TaskSuggestion(BaseModel):
    """Suggestion de tâche générée par l'IA."""
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    estimated_duration: Optional[int] = None  # en heures
    subtasks: List[str] = Field(default_factory=list)  # Checklist textuelle
    llm_prompt: Optional[str] = None  # Pour CODE_GENERATION ou DOCUMENT_WRITING
    keywords: List[str] = Field(default_factory=list)  # Pour VEILLE_*
    dependency_titles: List[str] = Field(default_factory=list, description="Titres des tâches dont cette tâche dépend")


class VeilleSuggestion(BaseModel):
    """Suggestion de veille automatique."""
    scope: str  # 'tech', 'funding', 'cultural', 'academic', 'news', 'collaboration'
    keywords: List[str]
    scan_frequency: str  # 'daily', 'weekly', 'monthly'
    reason: str  # Pourquoi cette veille est pertinente


class Blocker(BaseModel):
    """Blocage détecté dans le projet."""
    type: str  # 'stuck_task', 'missing_resource', 'dependency', 'unclear_requirement'
    description: str
    severity: str  # 'low', 'medium', 'high'
    suggestion: str  # Comment débloquer


class ProjectAnalysis(BaseModel):
    """Résultat complet de l'analyse d'un projet."""
    project_id: int
    analyzed_at: datetime
    summary: str  # Résumé de la compréhension du projet par l'IA
    task_suggestions: List[TaskSuggestion] = Field(default_factory=list)
    veille_suggestions: List[VeilleSuggestion] = Field(default_factory=list)
    blockers: List[Blocker] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)  # Top 3 actions recommandées
    estimated_total_hours: Optional[int] = None


# ============================================================
# SERVICE PRINCIPAL
# ============================================================

class ProjectAnalyzer:
    """Analyseur intelligent de projets avec modèle dynamique selon les préférences utilisateur."""

    DEFAULT_MODEL = "mistral:7b-instruct-q4_K_M"

    def __init__(self, db: AsyncSession, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id
        self.client = Client(host='http://host.docker.internal:11434')
        self.model = self.DEFAULT_MODEL
        self._model_loaded = False

    async def _chat(self, messages: list, options: dict) -> str:
        """Appel Ollama dans un thread (ne bloque pas l'event loop) avec le
        thinking natif désactivé pour les modèles qwen3.x — sinon la réponse
        part dans le champ thinking et le JSON arrive vide."""
        model = resolve_model(self.model, "analyse")
        kwargs = {"model": model, "messages": messages, "options": options, **think_kwargs(model)}
        response = await asyncio.to_thread(self.client.chat, **kwargs)
        content = (response['message'].get('content') or '').strip()
        if not content:
            thinking = response['message'].get('thinking') or ''
            raise ValueError(
                f"Le modèle {model} n'a produit aucun contenu "
                f"(thinking: {len(thinking)} chars)"
            )
        return content

    def _is_qwen3_model(self) -> bool:
        """Détecte si le modèle courant est un Qwen3."""
        return "qwen3" in self.model.lower()

    @staticmethod
    def _parse_json_lenient(content: str) -> Dict:
        """Parse du JSON produit par un LLM, en réparant les artefacts fréquents :
        accolades doublées ({{ }}), texte avant/après l'objet, virgules traînantes."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        repaired = content.strip()
        # Accolades doublées imitées depuis un template ({{ ... }})
        if repaired.startswith('{{'):
            repaired = repaired.replace('{{', '{').replace('}}', '}')
        # Isoler l'objet JSON le plus externe (texte parasite avant/après)
        start, end = repaired.find('{'), repaired.rfind('}')
        if start != -1 and end > start:
            repaired = repaired[start:end + 1]
        # Virgules traînantes avant } ou ]
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
        return json.loads(repaired)

    def _get_llm_options(self) -> dict:
        """Retourne les paramètres LLM optimisés pour le modèle courant."""
        if self._is_qwen3_model():
            return {
                "temperature": 0.6,
                "top_p": 0.9,
                "num_predict": 8192,
                "num_ctx": 32768,
                "stop": ["</s>"],
            }
        return {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 4096,
        }

    def _summarize_ideation_transcript(self, transcript: list, max_chars: int = 2000) -> str:
        """Résume le transcript d'idéation pour inclusion dans le prompt de génération."""
        relevant = [
            msg for msg in transcript
            if msg.get("role") in ("USER", "ASSISTANT")
        ]
        lines = []
        for msg in relevant:
            role = "Utilisateur" if msg["role"] == "USER" else "Assistant"
            content = msg.get("content", "")
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"{role}: {content}")
        summary = "\n".join(lines)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "\n[... conversation tronquée ...]"
        return summary

    def _build_system_prompt(self) -> str:
        """Retourne le system prompt adapté au modèle."""
        if self._is_qwen3_model():
            return (
                "Tu es un chef de projet technique expert spécialisé dans la décomposition "
                "de projets en tâches actionnables. Tu maîtrises le développement logiciel, "
                "le design, la recherche et l'administration de projets.\n"
                "Tu réponds UNIQUEMENT en JSON valide. Pas de markdown, pas de commentaires, "
                "pas de texte avant ou après le JSON."
            )
        return "Tu es un expert en gestion de projet. Tu réponds UNIQUEMENT en JSON valide, sans markdown ni explications supplémentaires."

    def _build_user_prompt(self, project_context: Dict, ideation_context: Optional[str] = None) -> str:
        """Construit le prompt utilisateur adapté au modèle."""
        if self._is_qwen3_model():
            return self._build_prompt_qwen3(project_context, ideation_context)
        return self._build_prompt_mistral(project_context, ideation_context)

    def _build_prompt_qwen3(self, project_context: Dict, ideation_context: Optional[str] = None) -> str:
        """Prompt optimisé pour qwen3-coder-next : concis, structuré, JSON strict."""
        prompt = f"""Analyse ce projet et génère un plan d'action complet décomposé en tâches.

PROJET: {project_context['name']}
DESCRIPTION: {project_context['description']}
TÂCHES EXISTANTES: {project_context['task_count']}
"""
        if ideation_context:
            prompt += f"""
CONTEXTE DE L'IDÉATION (conversation entre l'utilisateur et l'assistant):
{ideation_context}
"""

        prompt += """
TYPES VALIDES (utilise UNIQUEMENT ceux-ci): research | code_generation | document_writing | administrative | funding_search | veille
PRIORITÉS: P1 (fondations) | P2 (features) | P3 (polish)

SCHÉMA JSON ATTENDU:
{
  "summary": "Reformulation claire du projet avec objectifs",
  "tasks": [
    {
      "title": "Titre actionnable",
      "description": "Ce qui doit être fait et pourquoi",
      "task_type": "code_generation",
      "priority": "P1",
      "estimated_duration": 8,
      "subtasks": ["Action concrète 1", "Action concrète 2", "Action concrète 3"],
      "llm_prompt": "Prompt détaillé si code_generation ou document_writing, sinon chaîne vide",
      "keywords": [],
      "dependency_titles": []
    }
  ],
  "veille": [
    {
      "scope": "tech",
      "keywords": ["mot-clé très spécifique"],
      "scan_frequency": "weekly",
      "reason": "Pourquoi cette veille aide le projet"
    }
  ],
  "blockers": [
    {
      "type": "unclear_requirement",
      "description": "Description du blocage potentiel",
      "severity": "medium",
      "suggestion": "Comment résoudre"
    }
  ],
  "next_actions": ["Action prioritaire 1", "Action 2", "Action 3"]
}

RÈGLES:
- Réponds dans LA MÊME LANGUE que la description du projet
- task_type: UNIQUEMENT les 8 valeurs listées, n'invente PAS de nouveaux types
- Nombre de tâches adapté à la complexité (3 mini projet, 15-30 gros projet)
- 3-5 sous-tâches concrètes par tâche
- Couvre TOUS les aspects: design, dev, test, doc, déploiement
- dependency_titles: TITRES EXACTS des autres tâches, graphe acyclique, pas d'auto-référence
- Veilles: 1-3 max, uniquement si pertinentes, keywords très spécifiques
- llm_prompt: obligatoire pour code_generation et document_writing (prompt détaillé pour le LLM qui exécutera la tâche)

Retourne UNIQUEMENT le JSON."""
        return prompt

    def _build_prompt_mistral(self, project_context: Dict, ideation_context: Optional[str] = None) -> str:
        """Prompt détaillé pour mistral:7b et modèles moins capables."""
        prompt = f"""Tu es un chef de projet expert. Analyse ce projet EN PROFONDEUR et propose un plan d'action complet.

PROJET: {project_context['name']}
DESCRIPTION: {project_context['description']}
TÂCHES EXISTANTES: {project_context['task_count']}
"""
        if ideation_context:
            prompt += f"""
CONTEXTE DE L'IDÉATION (résumé de la conversation entre l'utilisateur et l'assistant IA):
{ideation_context}
"""

        prompt += """
MISSION:
1. Reformule le projet de manière claire et professionnelle
2. Identifie TOUS les aspects à traiter (technique, design, contenu, admin, etc.)
3. Décompose en tâches concrètes et actionnables de A à Z
4. Pour chaque tâche: titre clair, description précise, sous-tâches détaillées
5. Priorise intelligemment (fondations en P1, features en P2, polish en P3)
6. IDENTIFIE LES DÉPENDANCES LOGIQUES: Pour chaque tâche, indique les tâches dont elle dépend (ex: "Cette tâche doit être faite après telle autre")

TYPES DISPONIBLES (CHOISIS LE PLUS ADAPTÉ):
- research: Recherche, exploration, veille manuelle, création de mood boards, recherche visuelle, études
- code_generation: Écriture de code, développement logiciel, creative coding
- document_writing: Rédaction de textes, contenus, documentation, articles
- administrative: Organisation, planification, configuration, tests, déploiement
- funding_search: Recherche de financements, subventions, sponsors
- veille: Veille récurrente automatique (suivi web, liens commentés, monitoring de sujets)

IMPORTANT SUR LES TYPES:
- "Create mood boards", "Find inspiration", "Visual research" → research
- "Write code", "Develop feature", "Implement algorithm" → code_generation
- "Write article", "Document process", "Create content" → document_writing
- "Plan tasks", "Setup environment", "Test application" → administrative

IMPORTANT: Réponds dans LA MÊME LANGUE que la description du projet.

RÉPONDS EN JSON VALIDE (sans markdown, sans commentaires):
{
  "summary": "Reformulation claire et professionnelle du projet avec objectifs précis",
  "tasks": [
    {
      "title": "Titre clair et actionnable",
      "description": "Description détaillée de ce qui doit être fait et pourquoi",
      "task_type": "administrative",
      "priority": "P1",
      "estimated_duration": 8,
      "subtasks": [
        "Première action concrète à réaliser",
        "Deuxième action concrète",
        "Troisième action concrète",
        "Quatrième action si nécessaire",
        "Cinquième action si nécessaire"
      ],
      "llm_prompt": "Pour code_generation ou document_writing: prompt détaillé",
      "keywords": ["mot-clé1", "mot-clé2"],
      "dependency_titles": ["Titre de la tâche dont cette tâche dépend", "Autre titre si plusieurs dépendances"]
    }
  ],
  "veille": [
    {
      "scope": "tech",
      "keywords": ["mot-clé très spécifique 1", "mot-clé précis 2", "concept exact 3"],
      "scan_frequency": "weekly",
      "reason": "Explication détaillée de pourquoi cette veille automatique aidera le projet"
    }
  ],
  "blockers": [
    {
      "type": "unclear_requirement",
      "description": "Description du point qui pourrait bloquer",
      "severity": "medium",
      "suggestion": "Comment clarifier ou résoudre"
    }
  ],
  "next_actions": [
    "Première action prioritaire immédiate",
    "Deuxième action prioritaire",
    "Troisième action prioritaire"
  ]
}

RÈGLES STRICTES:
- Langue: MÊME LANGUE que le projet
- task_type: UNIQUEMENT les 8 valeurs listées (choisis le PLUS ADAPTÉ à la nature de la tâche!)
- Nombre de tâches: adapté à la complexité (2-3 pour mini projet, 15-30+ pour gros projet)
- Sous-tâches: 3-5 actions concrètes par tâche (pas juste 2!)
- Sois EXHAUSTIF: couvre TOUS les aspects (design, dev, test, doc, déploiement, etc.)
- Sois PRÉCIS: chaque tâche doit être claire et actionnable

RÈGLES POUR LES DÉPENDANCES:
- Identifie les dépendances LOGIQUES entre les tâches (ex: "La conception doit être faite avant le développement")
- Utilise les TITRES EXACTS des tâches dans dependency_titles (pas d'IDs, ils seront créés après)
- Une tâche peut dépendre de plusieurs autres tâches
- Si aucune dépendance, laisse dependency_titles vide: []
- Sois logique: une tâche ne peut pas dépendre d'elle-même
- Les dépendances doivent former un graphe acyclique (pas de dépendances circulaires)

RÈGLES POUR LES VEILLES AUTOMATIQUES:
- Les veilles sont des RECHERCHES AUTOMATIQUES RÉCURRENTES (ex: tous les vendredis)
- Suggère 1-3 veilles max, UNIQUEMENT si vraiment pertinentes
- Keywords: sois TRÈS SPÉCIFIQUE (ex: "Pantone color of the year 2026", "Design trends 2026", pas juste "design")
- Scope "cultural" pour: tendances design, couleurs de l'année, mouvements artistiques, inspirations visuelles
- Scope "tech" pour: nouvelles technologies, frameworks, outils de développement
- Scope "events" pour: conférences, salons, expositions pertinentes pour le projet
- Chaque veille doit avoir une RAISON CLAIRE expliquant comment elle aide concrètement le projet
"""
        return prompt

    async def _load_user_model_preference(self, usage: str = "task_generation"):
        """
        Charge le modèle préféré de l'utilisateur depuis ses settings.

        Args:
            usage: "task_generation" ou "analysis" — détermine quelle colonne lire
        """
        if self._model_loaded or not self.user_id:
            return

        try:
            from app.models.user_settings import UserSettings

            result = await self.db.execute(
                select(UserSettings).where(UserSettings.user_id == self.user_id)
            )
            user_settings = result.scalar_one_or_none()

            if user_settings:
                if usage == "task_generation" and user_settings.ollama_model_task_generation:
                    self.model = user_settings.ollama_model_task_generation
                elif usage == "analysis" and user_settings.ollama_model_analysis:
                    self.model = user_settings.ollama_model_analysis

                logger.info(f"📋 ProjectAnalyzer using model '{self.model}' for {usage} (user {self.user_id})")
            else:
                logger.info(f"📋 ProjectAnalyzer using default model '{self.model}' (no user settings)")

            self._model_loaded = True
        except Exception as e:
            logger.warning(f"Failed to load user model preference: {e}, using default '{self.model}'")

    async def analyze_project(self, project_id: int) -> ProjectAnalysis:
        """
        Analyse un projet et retourne des suggestions intelligentes.

        Étapes:
        1. Récupérer le projet et ses tâches existantes
        2. Construire le prompt pour Mistral
        3. Parser la réponse JSON
        4. Détecter les blocages
        5. Générer les suggestions d'actions
        """
        # Charger le modèle préféré de l'utilisateur
        await self._load_user_model_preference(usage="analysis")

        # 1. Récupérer le projet
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 2. Récupérer les tâches existantes pour contexte
        stmt_tasks = select(Task).where(Task.project_id == project_id)
        result_tasks = await self.db.execute(stmt_tasks)
        existing_tasks = result_tasks.scalars().all()

        # 3. Construire le contexte
        project_context = {
            "name": project.name,
            "description": project.description or "Pas de description fournie",
            "existing_tasks": [
                {
                    "title": task.title,
                    "type": task.task_type.value,
                    "status": task.status.value,
                    "priority": task.priority.value,
                }
                for task in existing_tasks
            ],
            "task_count": len(existing_tasks),
        }

        # 4. Enrichir avec le transcript d'idéation si disponible
        ideation_context = None
        if project.ideation_transcript:
            ideation_context = self._summarize_ideation_transcript(project.ideation_transcript)

        # 5. Générer l'analyse avec le LLM
        analysis_json = await self._generate_analysis(project_context, ideation_context=ideation_context)

        # 6. Détecter les blocages sur les tâches existantes
        blockers = await self._detect_blockers(existing_tasks)

        # 7. Construire le résultat final
        analysis = ProjectAnalysis(
            project_id=project_id,
            analyzed_at=datetime.now(timezone.utc),
            summary=analysis_json.get("summary", ""),
            task_suggestions=[
                TaskSuggestion(**task) for task in analysis_json.get("tasks", [])
            ],
            veille_suggestions=[
                VeilleSuggestion(**veille) for veille in analysis_json.get("veille", [])
            ],
            blockers=blockers + [Blocker(**b) for b in analysis_json.get("blockers", [])],
            next_actions=analysis_json.get("next_actions", []),
            estimated_total_hours=sum(
                task.get("estimated_duration", 0) for task in analysis_json.get("tasks", [])
            ),
        )

        return analysis

    async def _generate_analysis(self, project_context: Dict, ideation_context: Optional[str] = None) -> Dict:
        """Génère l'analyse via le modèle LLM configuré dans les préférences utilisateur."""

        # Charger le modèle préféré (task_generation pour la génération de tâches)
        await self._load_user_model_preference(usage="task_generation")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(project_context, ideation_context)
        options = self._get_llm_options()

        logger.info(f"🤖 _generate_analysis: model={self.model}, qwen3={self._is_qwen3_model()}, "
                     f"prompt_len={len(user_prompt)}, ideation={'oui' if ideation_context else 'non'}")

        try:
            content = await self._chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options=options,
            )

            # Nettoyer les tags <think> si présents (Qwen3 reasoning mode)
            if '<think>' in content:
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

            # Nettoyer le markdown si présent
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            # Parser le JSON (tolérant aux artefacts fréquents des LLM)
            analysis = self._parse_json_lenient(content)

            # Mapper les task_type invalides vers des valeurs valides (filet de sécurité)
            task_type_mapping = {
                'code': 'code_generation',
                'coding': 'code_generation',
                'development': 'code_generation',
                'dev': 'code_generation',
                'programming': 'code_generation',
                'design': 'research',
                'creative': 'research',
                'creative coding': 'code_generation',
                'ui': 'research',
                'ux': 'research',
                'graphic': 'research',
                'visual': 'research',
                'mood board': 'research',
                'moodboard': 'research',
                'documentation': 'document_writing',
                'doc': 'document_writing',
                'writing': 'document_writing',
                'content': 'document_writing',
                'marketing': 'document_writing',
                'communication': 'document_writing',
                'blog': 'document_writing',
                'polish': 'administrative',
                'testing': 'administrative',
                'test': 'administrative',
                'deployment': 'administrative',
                'deploy': 'administrative',
                'setup': 'administrative',
                'config': 'administrative',
                'organization': 'administrative',
                'research': 'research',
                'investigation': 'research',
                'exploration': 'research',
                'study': 'research',
            }

            valid_types = {'code_generation', 'document_writing', 'funding_search',
                           'veille', 'administrative', 'research'}

            # Mapping des anciens types vers le nouveau type unifié
            task_type_mapping['veille_tech'] = 'veille'
            task_type_mapping['veille_cultural'] = 'veille'
            task_type_mapping['veille_events'] = 'veille'
            task_type_mapping['monitoring'] = 'veille'
            task_type_mapping['watch'] = 'veille'
            task_type_mapping['surveillance'] = 'veille'

            for task in analysis.get("tasks", []):
                task_type = task.get("task_type", "").lower()
                if task_type in task_type_mapping:
                    corrected = task_type_mapping[task_type]
                    if task_type != corrected:
                        logger.info(f"task_type corrected: '{task_type}' -> '{corrected}' (model: {self.model})")
                    task["task_type"] = corrected
                elif task_type not in valid_types:
                    logger.warning(f"Unknown task_type '{task_type}' from model {self.model}, defaulting to 'research'")
                    task["task_type"] = "research"

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
            logger.error(f"Réponse brute: {content[:500]}")
            return {
                "summary": f"Analyse du projet {project_context['name']}",
                "tasks": [],
                "veille": [],
                "blockers": [],
                "next_actions": ["Analyser les besoins du projet", "Définir les objectifs", "Planifier les premières étapes"],
            }
        except Exception as e:
            logger.error(f"Erreur génération analyse: {e}")
            # Ne pas renvoyer un faux résultat vide : l'appelant doit voir l'échec
            raise AnalysisError(f"L'analyse IA a échoué : {e}") from e

    async def _detect_blockers(self, tasks: List[Task]) -> List[Blocker]:
        """Détecte les blocages dans les tâches existantes."""
        blockers = []
        now = datetime.now(timezone.utc)

        for task in tasks:
            # Blocage 1: Tâche P1 bloquée depuis >3 jours
            if task.priority == TaskPriority.P1 and task.status == TaskStatus.READY:
                if task.created_at and (now - task.created_at).days > 3:
                    blockers.append(Blocker(
                        type="stuck_task",
                        description=f"Tâche P1 '{task.title}' non démarrée depuis {(now - task.created_at).days} jours",
                        severity="high",
                        suggestion="Démarrer cette tâche immédiatement ou réviser sa priorité"
                    ))

            # Blocage 2: Tâche en cours depuis >7 jours
            if task.status == TaskStatus.GENERATING and task.started_at:
                if (now - task.started_at).days > 7:
                    blockers.append(Blocker(
                        type="stuck_task",
                        description=f"Tâche '{task.title}' en cours depuis {(now - task.started_at).days} jours",
                        severity="medium",
                        suggestion="Vérifier l'avancement ou annuler si plus pertinente"
                    ))

            # Blocage 3: Tâche en revue manuelle depuis >3 jours
            if task.status == TaskStatus.MANUAL_REVIEW and task.started_at:
                if (now - task.started_at).days > 3:
                    blockers.append(Blocker(
                        type="stuck_task",
                        description=f"Tâche '{task.title}' en attente de validation depuis {(now - task.started_at).days} jours",
                        severity="medium",
                        suggestion="Valider ou rejeter les résultats pour débloquer"
                    ))

        return blockers

    async def create_tasks_from_suggestions(
        self,
        project_id: int,
        suggestions: List[TaskSuggestion]
    ) -> List[Task]:
        """Crée les tâches en BDD à partir des suggestions avec gestion des dépendances."""
        created_tasks = []

        # Étape 1: Créer toutes les tâches d'abord (sans les dépendances)
        for suggestion in suggestions:
            # Construire la description avec les sous-tâches
            description_parts = [suggestion.description]

            if suggestion.subtasks:
                description_parts.append("\n\n**Checklist:**")
                for subtask in suggestion.subtasks:
                    description_parts.append(f"- [ ] {subtask}")

            full_description = "\n".join(description_parts)

            # Construire les metadata
            metadata = {}
            if suggestion.keywords:
                metadata["keywords"] = suggestion.keywords

            # Créer la tâche
            task = Task(
                project_id=project_id,
                title=suggestion.title,
                description=full_description,
                task_type=suggestion.task_type,
                priority=suggestion.priority,
                status=TaskStatus.READY,
                llm_prompt=suggestion.llm_prompt,
                estimated_duration=suggestion.estimated_duration,
                metadata=metadata,
            )

            self.db.add(task)
            created_tasks.append(task)

        # Commit pour obtenir les IDs des tâches créées
        await self.db.commit()

        # Étape 2: Créer un mapping titre -> ID pour établir les dépendances
        title_to_task_map = {task.title: task for task in created_tasks}

        # Étape 3: Établir les dépendances entre les tâches
        # Insertion directe dans la table d'association : après le commit ci-dessus les
        # objets sont expirés, et lire `task.dependencies` déclencherait un lazy-load
        # synchrone interdit en async (MissingGreenlet → 500).
        links = []
        seen = set()
        for suggestion in suggestions:
            current_task = title_to_task_map.get(suggestion.title)
            if not current_task:
                continue

            for dep_title in suggestion.dependency_titles:
                dependent_task = title_to_task_map.get(dep_title) if dep_title else None
                if not dependent_task or dependent_task.id == current_task.id:
                    continue  # Dépendance inconnue ou auto-référence
                pair = (current_task.id, dependent_task.id)
                if pair in seen:
                    continue
                seen.add(pair)
                links.append({"task_id": pair[0], "depends_on_id": pair[1]})

        if links:
            await self.db.execute(insert(task_dependencies).values(links))
            await self.db.commit()

        return created_tasks

    async def refine_task_suggestion(self, task: TaskSuggestion, user_prompt: str) -> TaskSuggestion:
        """Raffine une suggestion de tâche avec l'IA selon les instructions de l'utilisateur."""

        prompt = f"""L'utilisateur veut affiner cette tâche. Génère une version améliorée selon ses instructions.

TÂCHE ACTUELLE:
Titre: {task.title}
Description: {task.description}
Type: {task.task_type}
Priorité: {task.priority}
Durée estimée: {task.estimated_duration}h
Sous-tâches: {', '.join(task.subtasks) if task.subtasks else 'Aucune'}

INSTRUCTIONS UTILISATEUR:
{user_prompt}

IMPORTANT: Réponds dans LA MÊME LANGUE que la tâche actuelle. Si la tâche est en français, réponds en français. Si en anglais, réponds en anglais.

RÉPONDS EN JSON VALIDE avec la tâche raffinée (même structure):
{{
  "title": "Titre amélioré dans la langue de la tâche",
  "description": "Description plus détaillée dans la langue de la tâche",
  "task_type": "{task.task_type}",
  "priority": "{task.priority}",
  "estimated_duration": 8,
  "subtasks": ["Sous-tâche 1 dans la langue de la tâche", "Sous-tâche 2", "Sous-tâche 3"],
  "llm_prompt": "",
  "keywords": []
}}

RÈGLES:
- Utilise LA MÊME LANGUE que la tâche originale
- Garde le même type de tâche sauf si l'utilisateur demande de le changer
- Ajoute plus de détails et de sous-tâches si demandé
- Sois précis et actionnable
"""

        try:
            content = await self._chat(
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en décomposition de tâches. Tu réponds UNIQUEMENT en JSON valide."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 2048,
                }
            )

            # Nettoyer le markdown si présent
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            # Parser le JSON
            refined_data = json.loads(content)

            return TaskSuggestion(**refined_data)

        except Exception as e:
            print(f"❌ Erreur raffinement tâche: {e}")
            # Retourner la tâche originale en cas d'erreur
            return task
