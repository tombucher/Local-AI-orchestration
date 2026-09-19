"""
Orchestrateur unifié - Dispatch des tâches vers les modules appropriés

Gère tous les types de tâches :
- CODE_GENERATION → OllamaClient (génération de code)
- VEILLE_* → WebResearch + Analyzer
- DOCUMENT_WRITING → DocumentGenerator
- FUNDING_SEARCH → WebResearch + Analyzer + DocumentGenerator
- RESEARCH → LLM (plan de recherche structuré)
- ADMINISTRATIVE → LLM (checklist détaillée)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import aliased

from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.models.task_log import TaskLog, TaskEventType
from app.models.veille_topic import VeilleTopic, VeilleScope
from app.models.veille_result import VeilleResult, VeilleResultType, VeilleResultStatus
from app.models.user_settings import UserSettings
from app.models.project import Project
from app.services.llm_client import OllamaClient
from app.services.modules.web_research import WebResearchModule
from app.services.modules.analyzer import AnalyzerModule
from app.services.modules.document_generator import DocumentGeneratorModule
from app.services.web_search_service import WebSearchService
from app.core.config import settings as app_settings
from app.services.model_registry import resolve_model, think_kwargs

logger = logging.getLogger(__name__)


class UnifiedOrchestrator:
    """
    Orchestrateur unifié qui dispatche les tâches vers les modules appropriés

    Workflow:
    1. Récupère les tâches READY
    2. Selon le task_type, utilise le bon module
    3. Sauvegarde les résultats
    4. Log les événements
    """

    def __init__(self, db: AsyncSession):
        """
        Initialise l'orchestrateur avec tous les modules

        Args:
            db: Session de base de données async
        """
        self.db = db
        self.llm_client = OllamaClient()
        self.analyzer = AnalyzerModule()
        self.doc_generator = DocumentGeneratorModule()

    # Types de tâches traités automatiquement par le scheduler (sans intervention humaine)
    AUTO_PROCESS_TYPES = {
        TaskType.VEILLE,
        TaskType.VEILLE_TECH,
        TaskType.VEILLE_CULTURAL,
        TaskType.VEILLE_EVENTS,
        TaskType.RESEARCH,
        TaskType.ADMINISTRATIVE,
    }

    # Types nécessitant une validation manuelle avant d'être lancés
    MANUAL_TYPES = {
        TaskType.CODE_GENERATION,
        TaskType.DOCUMENT_WRITING,
        TaskType.FUNDING_SEARCH,
    }

    async def process_task_queue(self, batch_size: int = 5) -> int:
        """
        Job scheduler toutes les N minutes :
        1. Traite automatiquement les tâches READY de type autonome (veille, research, admin)
        2. Remet en READY les tâches FAILED éligibles au retry

        Les tâches CODE_GENERATION et DOCUMENT_WRITING restent en attente d'un déclenchement
        manuel par l'utilisateur via "Générer maintenant".

        Returns:
            Nombre de tâches traitées + retried
        """
        logger.info("⏰ Scheduler: processing task queue...")
        total = 0

        # 1. Traitement automatique des tâches READY de type autonome
        auto_processed = await self._process_auto_tasks(batch_size)
        if auto_processed > 0:
            logger.info(f"🚀 Auto-processed {auto_processed} tasks (veille/research/admin)")
            total += auto_processed

        # 2. Retry automatique des tâches FAILED éligibles
        retried = await self._retry_failed_tasks()
        if retried and retried > 0:
            logger.info(f"🔄 Retried {retried} failed tasks")
            total += retried
        elif auto_processed == 0:
            logger.info("✅ No tasks to process")

        await self.db.commit()
        return total

    async def _process_auto_tasks(self, batch_size: int) -> int:
        """Traite automatiquement les tâches READY de type autonome (veille, research, admin)."""
        stmt = (
            select(Task)
            .filter(Task.status == TaskStatus.READY)
            .filter(Task.task_type.in_([t.value for t in self.AUTO_PROCESS_TYPES]))
            .order_by(Task.created_at.asc())
            .limit(batch_size)
        )
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        if not tasks:
            return 0

        processed = 0
        for task in tasks:
            try:
                logger.info(f"🤖 Auto-processing task {task.id} ({task.task_type.value}): {task.title}")
                await self.handle_task(task)
                await self.db.flush()
                processed += 1
            except Exception as e:
                logger.error(f"❌ Auto-processing failed for task {task.id}: {e}", exc_info=True)
                await self.handle_failure(task, e)
                await self.db.flush()

        return processed

    async def handle_task(self, task: Task) -> None:
        """
        Dispatche la tâche vers le bon module selon son type

        Args:
            task: Tâche à traiter
        """
        logger.info(f"🚀 Handling task {task.id}: {task.title} (type: {task.task_type})")

        # Health check Ollama avant de lancer la génération
        if not await self.llm_client.health_check():
            raise RuntimeError("Ollama is not available — aborting task generation")

        # Update status
        task.status = TaskStatus.GENERATING
        task.started_at = datetime.utcnow()
        await self.db.flush()

        # Log start
        await self._log_event(
            task_id=task.id,
            event_type=TaskEventType.CODE_GENERATION_STARTED,
            details={'task_type': task.task_type.value}
        )

        # Dispatch selon le type
        if task.task_type == TaskType.CODE_GENERATION:
            await self._handle_code_generation(task)

        elif task.task_type in [TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS]:
            await self._handle_veille(task)

        elif task.task_type == TaskType.DOCUMENT_WRITING:
            await self._handle_document_writing(task)

        elif task.task_type == TaskType.FUNDING_SEARCH:
            await self._handle_funding_search(task)

        elif task.task_type == TaskType.RESEARCH:
            await self._handle_research(task)

        elif task.task_type == TaskType.ADMINISTRATIVE:
            await self._handle_administrative(task)

        else:
            # Gérer gracieusement les types non implémentés au lieu de crasher la queue
            logger.warning(f"⚠️ Task type {task.task_type} not yet implemented, marking as FAILED")
            task.status = TaskStatus.FAILED
            task.validation_notes = f"Task type {task.task_type} not yet implemented"
            await self._log_event(
                task_id=task.id,
                event_type=TaskEventType.GENERATION_FAILED,
                details={'error': f"Task type {task.task_type} not yet implemented", 'error_type': 'NotImplementedError'}
            )
            return

        # Transition vers le bon statut selon le type de tâche :
        # - CODE_GENERATION → MANUAL_REVIEW (le code doit être validé par un humain)
        # - Tous les autres types → COMPLETED (contenu informatif, pas de validation)
        if task.task_type == TaskType.CODE_GENERATION:
            task.status = TaskStatus.MANUAL_REVIEW
            next_status = "MANUAL_REVIEW"
        else:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            next_status = "COMPLETED"

        await self._log_event(
            task_id=task.id,
            event_type=TaskEventType.CODE_GENERATED,
            details={
                'result_length': len(task.generated_code or ''),
                'next_status': next_status,
            }
        )

        logger.info(f"✅ Task {task.id} ({task.task_type.value}) → {next_status}")

    async def _handle_code_generation(self, task: Task) -> None:
        """Gère la génération de code (module existant)"""
        logger.info(f"💻 Generating code for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_task_model(project.user_id)

        code = await self.llm_client.generate_code(task, model_override=model)
        task.generated_code = code

    async def _handle_veille(self, task: Task) -> None:
        """Gère les tâches de veille — type unifié

        Recherche web via DuckDuckGo, guidée par les keywords et le contexte du projet.
        Produit un Rapport Radar structuré (pépites + stats + affinage).
        """
        logger.info(f"🔍 Running unified veille for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_task_model(project.user_id)

        # Extraire keywords et exclusions
        keywords = self._extract_keywords(task)
        excluded_keywords = []

        # Si lié à un VeilleTopic, récupérer les exclusions et keywords affinés
        veille_topic = None
        if task.veille_topic_id:
            stmt = select(VeilleTopic).where(VeilleTopic.id == task.veille_topic_id)
            result = await self.db.execute(stmt)
            veille_topic = result.scalar_one_or_none()
            if veille_topic:
                # Utiliser les keywords du topic si disponibles (affinés au fil du temps)
                if veille_topic.keywords:
                    keywords = veille_topic.keywords
                excluded_keywords = veille_topic.excluded_keywords or []

        # Veille visuelle (moodboard) : pipeline images dédié
        if veille_topic and veille_topic.scope == VeilleScope.VISUAL:
            await self._handle_visual_veille(task, veille_topic, project, model)
            return

        # Générer des requêtes DuckDuckGo ciblées via LLM (fallback basique si LLM off)
        queries = await self._generate_veille_queries(task, model, veille_topic)
        web_search = WebSearchService()

        # Phase 1 : Recherche web via DuckDuckGo (parallélisée avec asyncio.gather)
        async def _search_one(query: str) -> list:
            try:
                ddg_results = await web_search.search_text(query, max_results=7)
                results = [
                    {
                        'title': r.get('title', 'Sans titre'),
                        'url': r.get('href', ''),
                        'description': r.get('body', ''),
                        'source_platform': 'DuckDuckGo',
                    }
                    for r in ddg_results
                ]
                logger.info(f"🔎 DDG query '{query}' → {len(results)} résultats")
                return results
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
                return []

        search_results = await asyncio.gather(*[_search_one(q) for q in queries])
        raw_results = [r for batch in search_results for r in batch]

        # RSS optionnel si configuré
        if task.task_metadata and task.task_metadata.get('rss_feeds'):
            async with WebResearchModule() as research:
                for feed_url in task.task_metadata['rss_feeds']:
                    try:
                        feed_results = await research.fetch_rss_feed(feed_url)
                        for fr in feed_results:
                            raw_results.append({
                                'title': fr.get('title', ''),
                                'url': fr.get('link', fr.get('url', '')),
                                'description': fr.get('description', fr.get('summary', '')),
                                'source_platform': 'RSS',
                            })
                    except Exception as e:
                        logger.warning(f"RSS feed failed: {feed_url}: {e}")

        # Dédoublonner par URL
        seen_urls = set()
        unique_results = []
        for r in raw_results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
            elif not url:
                unique_results.append(r)

        total_scanned = len(unique_results)
        logger.info(f"📊 Total brut : {total_scanned} résultats uniques avant analyse")

        # Phase 2 : Analyse de pertinence
        analyzed_results = []
        # Réutilise le topic déjà lié à la tâche, sinon récupère/crée par scope
        if veille_topic is not None:
            topic = veille_topic
        else:
            topic = await self._get_or_create_veille_topic(
                project_id=project.id,
                scope=VeilleScope.NEWS,  # Scope générique pour veille unifiée
                keywords=keywords
            )

        # Lier la tâche au topic si pas déjà fait
        if not task.veille_topic_id:
            task.veille_topic_id = topic.id
            veille_topic = topic

        # Phase 2+3 dans un savepoint transactionnel : si l'analyse ou le radar
        # échoue, on rollback les VeilleResult insérés au lieu de laisser des orphelins.
        savepoint = await self.db.begin_nested()
        try:
            # Objectif précis de cette tâche de veille (titre + description)
            task_objective = task.description.strip() if task.description else task.title

            for result in unique_results[:20]:
                analysis = await self.analyzer.analyze_relevance(
                    content=result,
                    project_context={
                        'name': project.name,
                        'description': project.description,
                        'type': project.type.value,
                        'excluded_keywords': excluded_keywords,
                        'task_objective': task_objective,
                    },
                    keywords=keywords,
                    model=model
                )

                # Sauvegarder si pertinent (score >= 0.5)
                if analysis['relevance_score'] >= 0.5:
                    ai_summary = await self.analyzer.generate_summary(
                        result.get('description', '')[:2000],
                        model=model
                    )

                    veille_result = VeilleResult(
                        topic_id=topic.id,
                        task_id=task.id,
                        result_type=VeilleResultType.NEWS_ARTICLE,
                        title=result.get('title', 'Sans titre'),
                        url=result.get('url'),
                        description=result.get('description', ''),
                        source_platform=result.get('source_platform', ''),
                        ai_summary=ai_summary,
                        relevance_score=analysis['relevance_score'] * 100,
                        key_points=analysis['key_points'],
                        relevance_reason=analysis['reason'],
                        status=VeilleResultStatus.NEW
                    )
                    self.db.add(veille_result)
                    await self.db.flush()

                    # Accumuler pour le Radar
                    analyzed_results.append({
                        'title': result.get('title', 'Sans titre'),
                        'url': result.get('url', ''),
                        'description': result.get('description', ''),
                        'relevance_score': analysis['relevance_score'],
                        'reason': analysis['reason'],
                        'key_points': analysis['key_points'],
                        'ai_summary': ai_summary,
                        'source_platform': result.get('source_platform', ''),
                        'result_id': veille_result.id,
                    })

            logger.info(f"✅ {len(analyzed_results)} résultats pertinents sauvegardés")

            # Phase 3 : Générer le Rapport Radar
            radar = await self.analyzer.generate_radar_report(
                analyzed_results=analyzed_results,
                project_context={
                    'name': project.name,
                    'description': project.description,
                    'type': project.type.value,
                    'excluded_keywords': excluded_keywords,
                },
                keywords=keywords,
                total_scanned=total_scanned,
                model=model
            )

            task.radar_report = radar
            await savepoint.commit()
        except Exception as e:
            await savepoint.rollback()
            logger.error(f"❌ Veille analysis/radar failed for task {task.id}, rolled back VeilleResults: {e}")
            raise
        # Fallback texte pour l'affichage classique
        task.generated_code = (
            f"🔍 Rapport Radar — {len(analyzed_results)} pépites trouvées sur {total_scanned} résultats scannés.\n\n"
            + "\n".join(
                f"• [{r.get('relevance_score', 0)*100:.0f}%] {r.get('title', '')}\n  {r.get('url', '')}"
                for r in analyzed_results[:10]
            )
        )

    async def _handle_visual_veille(self, task: Task, topic, project, model: str) -> None:
        """Veille visuelle : collecte de références d'images libres (moodboard).

        Sources sans clé API (Openverse, Art Institute of Chicago, Met Museum,
        Wikimedia Commons) + flux RSS design (ceux de topic.sources, sinon défaut).
        Filtrage léger par métadonnées — pas de scoring LLM image par image
        (trop lent en local).
        """
        logger.info(f"🖼 Running visual veille for task {task.id} (topic {topic.id})")

        keywords = topic.keywords or self._extract_keywords(task)
        excluded = [k.casefold() for k in (topic.excluded_keywords or [])]

        # Requêtes anglaises courtes (les APIs d'images répondent mieux en anglais)
        queries = await self._generate_visual_queries(task, keywords)

        async with WebResearchModule() as research:
            images = await research.search_visual_references(
                queries,
                keywords=keywords,
                feeds=[src for src in (topic.sources or []) if str(src).startswith("http")] or None,
            )

        # Filtrage par exclusions (titre/description)
        if excluded:
            images = [
                img for img in images
                if not any(
                    exc in f"{img.get('title', '')} {img.get('description', '')}".casefold()
                    for exc in excluded
                )
            ]

        for img in images:
            self.db.add(VeilleResult(
                topic_id=topic.id,
                task_id=task.id,
                result_type=VeilleResultType.VISUAL_REFERENCE,
                title=img.get('title', 'Sans titre')[:500],
                url=img.get('url'),
                description=img.get('description', ''),
                image_url=img.get('image_url'),
                thumbnail_url=img.get('thumbnail_url'),
                license=img.get('license'),
                source_platform=img.get('source_platform'),
                # Pas de scoring LLM par image : score neutre, l'utilisateur trie
                relevance_score=50.0,
                status=VeilleResultStatus.NEW,
            ))

        await self.db.flush()
        task.generated_code = (
            f"Veille visuelle : {len(images)} références collectées "
            f"({', '.join(sorted(set(i.get('source_platform', '') for i in images)))})."
        )
        logger.info(f"🖼 Visual veille done: {len(images)} references saved")

    async def _generate_visual_queries(self, task: Task, keywords: List[str]) -> List[str]:
        """Génère 2-3 requêtes anglaises courtes pour les APIs d'images."""
        base = ", ".join(keywords[:5]) if keywords else task.title
        prompt = f"""Translate and condense into 3 short English image-search queries (2-4 words each) for finding visual references about: {base}

One query per line, no numbering, no quotes, English only."""
        try:
            response = await self.analyzer._generate_text_async(
                prompt, model=self.analyzer._FAST_FALLBACK_MODEL
            )
            queries = [
                line.strip().lstrip('-•*0123456789.) ').strip('"\'« »')
                for line in response.strip().split('\n')
                if 2 < len(line.strip()) < 60
            ][:3]
            if queries:
                logger.info(f"🖼 Visual queries: {queries}")
                return queries
        except Exception as e:
            logger.warning(f"Visual query generation failed: {e}")
        return [" ".join(keywords[:3])] if keywords else [task.title]

    async def _handle_document_writing(self, task: Task) -> None:
        """Gère la rédaction de documents"""
        logger.info(f"📄 Generating document for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_text_model(project.user_id)

        metadata = task.task_metadata or {}
        sections = metadata.get('sections', [
            {"name": "Introduction", "max_words": 200},
            {"name": "Contenu principal", "max_words": 500},
            {"name": "Conclusion", "max_words": 150}
        ])

        document = await self.doc_generator.generate_document(
            document_type=metadata.get('document_type', 'generic'),
            context={
                'project_name': project.name,
                'project_description': project.description,
                **metadata.get('context', {})
            },
            sections=sections,
            model=model
        )

        task.generated_code = document

    async def _handle_funding_search(self, task: Task) -> None:
        """Gère la recherche de financements (appels à projets, résidences, subventions).

        Recherche via DuckDuckGo avec des requêtes orientées appels à projets —
        search_data_gouv() ne renvoyait que des datasets, hors-sujet ici.
        """
        logger.info(f"💰 Searching funding for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_task_model(project.user_id)

        keywords = self._extract_keywords(task)

        # Recherche web orientée financements
        queries = await self._generate_funding_queries(task)
        web_search = WebSearchService()

        async def _search_one(query: str) -> list:
            try:
                ddg_results = await web_search.search_text(query, max_results=7)
                logger.info(f"💰 DDG funding query '{query}' → {len(ddg_results)} résultats")
                return [
                    {
                        'title': r.get('title', 'Sans titre'),
                        'url': r.get('href', ''),
                        'description': r.get('body', ''),
                        'source_platform': 'DuckDuckGo',
                    }
                    for r in ddg_results
                ]
            except Exception as e:
                logger.warning(f"DuckDuckGo funding search failed for '{query}': {e}")
                return []

        search_results = await asyncio.gather(*[_search_one(q) for q in queries])
        results = [r for batch in search_results for r in batch]

        # Source structurée : Aides-Territoires (deadlines fiables), si clé configurée
        async with WebResearchModule() as research:
            at_results = await research.search_aides_territoires(
                keywords=keywords or [task.title],
                api_key=app_settings.AIDES_TERRITOIRES_API_KEY or None,
            )
        results = at_results + results

        # Dédoublonner par URL
        seen_urls = set()
        unique_results = []
        for r in results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        results = unique_results

        # Analyse et filtrage
        filtered_count = 0
        deadlines_found = 0
        async with WebResearchModule() as research:
            for result in results[:10]:
                analysis = await self.analyzer.analyze_relevance(
                    content=result,
                    project_context={
                        'name': project.name,
                        'description': project.description,
                        'type': project.type.value
                    },
                    keywords=keywords,
                    model=model
                )

                if analysis['relevance_score'] < 0.7:
                    continue

                # Extraction des détails depuis la PAGE (le snippet DDG ne
                # contient presque jamais la deadline) — sauf si la source
                # structurée (Aides-Territoires) la fournit déjà
                deadline_dt = self._parse_deadline(result.get('deadline'))
                page_text = ""
                if result.get('url') and not deadline_dt:
                    page_text = await research.fetch_page_text(result['url'])

                funding_details = await self.analyzer.extract_key_information(
                    content=page_text or result.get('description', ''),
                    info_type='funding_details',
                    model=model
                )
                if not deadline_dt:
                    deadline_dt = self._parse_deadline(funding_details.get('deadline'))
                if deadline_dt:
                    deadlines_found += 1

                topic = await self._get_or_create_veille_topic(
                    project_id=project.id,
                    scope=VeilleScope.FUNDING,
                    keywords=keywords
                )

                veille_result = VeilleResult(
                    topic_id=topic.id,
                    task_id=task.id,
                    result_type=VeilleResultType.CALL_FOR_PROPOSALS,
                    title=result.get('title', 'Sans titre'),
                    url=result.get('url'),
                    description=result.get('description', ''),
                    ai_summary=await self.analyzer.generate_summary(
                        (page_text or result.get('description', ''))[:2000],
                        model=model
                    ),
                    relevance_score=analysis['relevance_score'] * 100,
                    key_points=analysis['key_points'],
                    relevance_reason=analysis['reason'],
                    result_metadata=funding_details,
                    deadline=deadline_dt,
                    status=VeilleResultStatus.ACTIONABLE
                )
                self.db.add(veille_result)
                filtered_count += 1

        await self.db.flush()

        # Résumé
        summary = (
            f"Recherche de financements : {filtered_count} opportunités trouvées"
            f"{f', {deadlines_found} avec date limite identifiée' if deadlines_found else ''}."
        )
        task.generated_code = summary

    @staticmethod
    def _parse_deadline(value) -> Optional[datetime]:
        """Parse une deadline 'YYYY-MM-DD' (ou ISO) renvoyée par le LLM ou une API.
        Retourne None pour 'non spécifié' et les dates passées de plus d'un an."""
        if not value or not isinstance(value, str):
            return None
        value = value.strip()[:10]
        try:
            dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if dt < datetime.now(timezone.utc) - timedelta(days=365):
            return None
        return dt

    async def _handle_research(self, task: Task) -> None:
        """Génère un plan de recherche structuré via LLM"""
        logger.info(f"🔬 Generating research plan for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_text_model(project.user_id)

        # Enrichit le llm_prompt avec des instructions spécifiques research
        original_prompt = task.llm_prompt or task.description or task.title
        task.llm_prompt = f"""{original_prompt}

INSTRUCTIONS SUPPLÉMENTAIRES:
Génère un plan de recherche structuré avec:
1. Objectif de la recherche
2. Sources à consulter (sites web, bases de données, APIs, etc.)
3. Méthodologie étape par étape
4. Points clés à explorer
5. Critères d'évaluation des résultats
6. Livrables attendus
Sois concret et actionnable. Format Markdown."""

        result = await self.llm_client.generate_text(task, model_override=model)
        task.llm_prompt = original_prompt  # Restaure le prompt original
        task.generated_code = result if result and result.strip() else f"[Recherche à effectuer]\n\n{original_prompt}"

    async def _handle_administrative(self, task: Task) -> None:
        """Génère une checklist administrative détaillée via LLM"""
        logger.info(f"📋 Generating administrative checklist for task {task.id}")

        project = await self._get_project(task.project_id)
        model = await self._get_text_model(project.user_id)

        original_prompt = task.llm_prompt or task.description or task.title
        task.llm_prompt = f"""{original_prompt}

INSTRUCTIONS SUPPLÉMENTAIRES:
Génère une checklist administrative détaillée avec:
1. Résumé de la tâche (une phrase)
2. Étapes concrètes numérotées (avec sous-étapes si nécessaire)
3. Outils/ressources recommandés
4. Points d'attention (risques, délais, pièges)
5. Critères de complétion
6. Estimation de temps par étape
Sois concret et directement applicable. Format Markdown."""

        result = await self.llm_client.generate_text(task, model_override=model)
        task.llm_prompt = original_prompt  # Restaure le prompt original
        task.generated_code = result if result and result.strip() else f"[Tâche administrative]\n\n{original_prompt}"

    async def _get_task_model(self, user_id: int) -> str:
        """Récupère le modèle préféré de l'utilisateur pour le code"""
        user_settings = await self._get_user_settings(user_id)
        preferred = user_settings.ollama_model_code if user_settings else app_settings.OLLAMA_MODEL_CODE
        return resolve_model(preferred, "code")

    async def _get_text_model(self, user_id: int) -> str:
        """Récupère le modèle préféré de l'utilisateur pour la génération de texte.
        Utilise ollama_model_text si défini, sinon fallback sur ollama_model_code."""
        user_settings = await self._get_user_settings(user_id)
        if not user_settings:
            preferred = app_settings.OLLAMA_MODEL_CODE
        elif user_settings.ollama_model_text:
            preferred = user_settings.ollama_model_text
        else:
            preferred = user_settings.ollama_model_code
        return resolve_model(preferred, "texte")

    async def handle_failure(self, task: Task, error: Exception) -> None:
        """Gestion de l'échec avec tracking du retry"""
        task.retry_count = (task.retry_count or 0) + 1
        task.last_failed_at = datetime.utcnow()
        task.status = TaskStatus.FAILED
        # Rendre l'erreur visible dans l'UI (TaskDetail affiche validation_notes)
        task.validation_notes = f"Échec ({task.retry_count}/3) : {str(error)[:500]}"

        logger.error(f"❌ Task {task.id} failed (attempt {task.retry_count}/3): {error}")

        await self._log_event(
            task_id=task.id,
            event_type=TaskEventType.GENERATION_FAILED,
            details={
                'error': str(error),
                'error_type': type(error).__name__,
                'retry_count': task.retry_count
            }
        )
        await self.db.flush()

    @staticmethod
    def _get_retry_cooldown_minutes(retry_count: int) -> int:
        """Backoff exponentiel : 1min → 5min → 15min selon le nombre de retries"""
        cooldowns = {0: 1, 1: 5, 2: 15}
        return cooldowns.get(retry_count, 15)

    async def _retry_failed_tasks(self, max_retries: int = 3) -> int:
        """Remet en READY les tâches FAILED éligibles au retry (batch configurable).

        Utilise un backoff exponentiel : cooldown croissant selon retry_count.
        """
        now = datetime.utcnow()
        batch_size = app_settings.ORCHESTRATOR_BATCH_SIZE

        # Récupérer les tâches FAILED candidates (retry_count < max et last_failed_at défini)
        stmt = (
            select(Task)
            .filter(Task.status == TaskStatus.FAILED)
            .filter(Task.retry_count < max_retries)
            .filter(Task.last_failed_at != None)  # noqa: E711
            .order_by(Task.last_failed_at.asc())
            .limit(batch_size * 2)  # Marge pour filtrer par cooldown
        )
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        retried = 0
        for task in candidates:
            if retried >= batch_size:
                break

            # Backoff exponentiel par tâche
            cooldown = self._get_retry_cooldown_minutes(task.retry_count)
            cutoff = now - timedelta(minutes=cooldown)

            if task.last_failed_at > cutoff:
                continue  # Cooldown pas encore écoulé

            task.status = TaskStatus.READY
            retried += 1
            logger.info(
                f"🔄 Task {task.id} reset to READY "
                f"(retry {task.retry_count}/{max_retries}, cooldown was {cooldown}min)"
            )
            await self._log_event(
                task_id=task.id,
                event_type=TaskEventType.CODE_GENERATION_STARTED,
                details={'action': 'auto_retry', 'retry_count': task.retry_count, 'cooldown_minutes': cooldown}
            )

        if retried > 0:
            await self.db.flush()

        return retried

    # Helper methods

    async def _get_project(self, project_id: int) -> Project:
        """Récupère un projet"""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def _get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Récupère les settings utilisateur"""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_create_veille_topic(
        self,
        project_id: int,
        scope: VeilleScope,
        keywords: List[str]
    ) -> VeilleTopic:
        """Récupère ou crée un topic de veille"""
        # Cherche un topic existant — first() et non scalar_one_or_none() :
        # plusieurs topics peuvent partager le même scope sur un projet
        stmt = (
            select(VeilleTopic)
            .where(VeilleTopic.project_id == project_id)
            .where(VeilleTopic.scope == scope)
            .order_by(VeilleTopic.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        topic = result.scalars().first()

        if not topic:
            # Crée un nouveau topic
            topic = VeilleTopic(
                project_id=project_id,
                name=f"Veille {scope.value}",
                scope=scope,
                keywords=keywords,
                scan_frequency="manual",
                enabled=True
            )
            self.db.add(topic)
            await self.db.flush()

        return topic

    def _extract_keywords(self, task: Task) -> List[str]:
        """Extrait les keywords d'une tâche"""
        if task.task_metadata and task.task_metadata.get('keywords'):
            return task.task_metadata['keywords']

        # Sinon, extrait des mots-clés basiques depuis la description
        if task.description:
            words = task.description.split()
            return [w for w in words if len(w) > 4][:10]

        return [task.title]

    async def _generate_funding_queries(self, task: Task) -> List[str]:
        """Génère des requêtes DDG orientées appels à projets / résidences / subventions."""
        description = (task.description or "").strip()
        title = (task.title or "").strip()
        objective = f"{title}\n{description}" if description and description != title else title
        year = datetime.now(timezone.utc).year

        prompt = f"""Tu es un expert en recherche de financements pour des projets artistiques et technologiques en France. Génère 4 requêtes de recherche DuckDuckGo pour trouver des appels à projets, résidences, subventions ou bourses correspondant au projet ci-dessous.

PROJET :
{objective}

EXEMPLES DE BONNES REQUÊTES :
- appel à projets art numérique {year}
- résidence artiste installation lumière {year}
- subvention DRAC création numérique
- bourse fondation art technologie {year}

RÈGLES :
- Toutes en français (les financeurs visés sont français/européens)
- Inclure des termes comme : appel à projets, résidence, subvention, bourse, aide
- Court et naturel (4-8 mots par requête)
- Une requête par ligne, SANS tiret, SANS numérotation, SANS guillemets

Requêtes :"""

        try:
            query_model = self.analyzer._FAST_FALLBACK_MODEL
            response = await self.analyzer._generate_text_async(prompt, model=query_model)
            lines = []
            for line in response.strip().split('\n'):
                line = line.strip().lstrip('-•*0123456789.) ').strip('"\'« »')
                if line and 5 < len(line) < 120:
                    lines.append(line)
            if lines:
                logger.info(f"💰 Requêtes funding LLM générées : {lines[:4]}")
                return lines[:4]
        except Exception as e:
            logger.warning(f"Funding query generation failed, using fallback: {e}")

        keywords = self._extract_keywords(task)
        base = " ".join(keywords[:4]) if keywords else title
        return [
            f"appel à projets {base} {year}",
            f"résidence {base}",
            f"subvention {base} culture",
        ]

    def _build_veille_queries_fallback(self, keywords: List[str], task: Task) -> List[str]:
        """Fallback : construit des requêtes basiques si le LLM est indisponible"""
        base_kw = " ".join(keywords[:5])
        queries = [base_kw]
        if task.title and len(task.title) > 5:
            queries.append(task.title)
        if len(keywords) >= 2:
            queries.append(f"{' '.join(keywords[:3])} 2025 2026")
        return queries[:3]

    async def _generate_veille_queries(self, task: Task, model: str, veille_topic=None) -> List[str]:
        """
        Génère 4 requêtes de recherche ciblées via LLM.
        Utilise le titre ET la description de la tâche, plus l'historique
        d'affinage utilisateur et les résultats écartés (exemples négatifs).
        Fallback sur _build_veille_queries_fallback si le LLM échoue.
        """
        description = (task.description or "").strip()
        title = (task.title or "").strip()
        objective = f"{title}\n{description}" if description and description != title else title

        # Contexte d'affinage : derniers ajustements utilisateur + résultats écartés
        refinement_context = ""
        if veille_topic is not None:
            parts = []
            history = list(veille_topic.refinement_history or [])[-3:]
            for h in history:
                if h.get("add_keywords"):
                    parts.append(f"l'utilisateur a AJOUTÉ les mots-clés : {', '.join(h['add_keywords'])}")
                if h.get("remove_keywords"):
                    parts.append(f"l'utilisateur a RETIRÉ les mots-clés : {', '.join(h['remove_keywords'])}")
                if h.get("add_excluded"):
                    parts.append(f"l'utilisateur veut EXCLURE : {', '.join(h['add_excluded'])}")
                if h.get("user_notes"):
                    parts.append(f"note utilisateur : {h['user_notes']}")
            if veille_topic.excluded_keywords:
                parts.append(f"termes à éviter absolument : {', '.join(veille_topic.excluded_keywords)}")

            # Titres des résultats écartés récents = exemples de hors-sujet
            dismissed_stmt = (
                select(VeilleResult.title)
                .where(
                    VeilleResult.topic_id == veille_topic.id,
                    VeilleResult.status == VeilleResultStatus.DISMISSED,
                )
                .order_by(VeilleResult.updated_at.desc())
                .limit(5)
            )
            dismissed = (await self.db.execute(dismissed_stmt)).scalars().all()
            if dismissed:
                parts.append(
                    "exemples de résultats JUGÉS HORS-SUJET par l'utilisateur : "
                    + " ; ".join(f"« {t} »" for t in dismissed)
                )
            if parts:
                refinement_context = (
                    "\nAFFINAGE UTILISATEUR (à respecter impérativement) :\n- "
                    + "\n- ".join(parts) + "\n"
                )

        prompt = f"""Tu es un expert en veille et recherche sur internet. Génère 4 requêtes de recherche DuckDuckGo efficaces pour trouver ce qui est demandé ci-dessous.

OBJECTIF :
{objective}
{refinement_context}
EXEMPLES DE BONNES REQUÊTES (style naturel, courtes, qui fonctionnent bien sur DDG) :
- "open source sans-serif fonts GitHub free"
- "best free geometric sans serif typeface 2025"
- "Google Fonts sans-serif bold high impact"
- "polices gratuites sans empattement contemporaines"

RÈGLES :
- 2 requêtes en anglais, 2 en français
- Court et naturel (4-7 mots max par requête)
- Termes concrets : noms de sites (GitHub, Google Fonts, Behance), formats (.otf, .ttf), critères
- ÉVITER : "guide", "tutoriel", "définition", "actualité", "formation"
- Une requête par ligne, SANS tiret, SANS numérotation, SANS guillemets

Requêtes :"""

        try:
            # Utilise le modèle rapide (mistral) pour les requêtes — tâche courte et structurée,
            # pas besoin d'un gros modèle thinking. L'AnalyzerModule a le bon fallback intégré.
            query_model = self.analyzer._FAST_FALLBACK_MODEL
            response = await self.analyzer._generate_text_async(prompt, model=query_model)
            import re as _re
            lines = []
            for line in response.strip().split('\n'):
                line = line.strip().lstrip('-•*0123456789.) ').strip('"\'« »')
                # Supprimer les labels de langue ajoutés par le LLM (ex: " - English", " - Français")
                line = _re.sub(r'\s*[-–—]\s*(English|French|Anglais|Fran[çc]ais)\s*$', '', line, flags=_re.IGNORECASE).strip()
                if line and len(line) > 5:
                    lines.append(line)
            # Filtrer les lignes qui ressemblent à des explications (trop longues)
            queries = [l for l in lines if len(l) < 120][:4]
            if queries:
                logger.info(f"🧠 Requêtes veille LLM générées : {queries}")
                return queries
            else:
                logger.warning(f"LLM query generation returned empty/unparseable response (model={model}): {repr(response[:200])}")
        except Exception as e:
            logger.warning(f"LLM query generation failed, using fallback: {e}")

        keywords = self._extract_keywords(task)
        fallback = self._build_veille_queries_fallback(keywords, task)
        logger.info(f"🔙 Fallback veille queries: {fallback}")
        return fallback

    async def _log_event(self, task_id: int, event_type: TaskEventType, details: dict) -> None:
        """Log un événement"""
        log = TaskLog(
            task_id=task_id,
            event_type=event_type,
            details=details
        )
        self.db.add(log)
        await self.db.flush()
