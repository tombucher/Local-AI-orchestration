"""
Scheduler pour l'exécution périodique des tâches d'orchestration
"""
import logging
from datetime import date, datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_

from app.core.database import AsyncSessionLocal
from app.core.logging import set_correlation_id
from app.services.unified_orchestrator import UnifiedOrchestrator
from app.services.notifier import notify_briefing
from app.services.daily_review_service import DailyReviewService
from app.models.user import User
from app.models.task import Task, TaskType, TaskStatus
from app.models.task_log import TaskLog, TaskEventType
from app.models.veille_topic import VeilleTopic
from app.models.daily_report import DailyReport as DailyReportModel
from app.core.config import settings

logger = logging.getLogger(__name__)

# Instance globale du scheduler
scheduler = AsyncIOScheduler()


async def process_queue_job() -> None:
    """
    Job APScheduler : traite la file d'attente des tâches

    Exécuté périodiquement pour traiter les tâches READY
    """
    set_correlation_id()  # Correlation ID unique par tick scheduler
    logger.info("⏰ Running scheduled job: process_queue")

    async with AsyncSessionLocal() as db:
        orchestrator = UnifiedOrchestrator(db)

        try:
            success_count = await orchestrator.process_task_queue(
                batch_size=settings.ORCHESTRATOR_BATCH_SIZE
            )
            logger.info(f"✅ Scheduled job completed: {success_count} tasks processed")
        except Exception as e:
            logger.error(f"❌ Queue processing error: {e}", exc_info=True)


async def generate_daily_reports_job() -> None:
    """
    Job APScheduler : génère les rapports quotidiens pour tous les utilisateurs actifs

    Exécuté chaque matin à 8h00
    """
    set_correlation_id()  # Correlation ID unique par job
    logger.info("📊 Running scheduled job: generate_daily_reports")
    today = date.today()

    async with AsyncSessionLocal() as db:
        try:
            # Récupérer tous les utilisateurs actifs
            query = select(User).where(User.is_active == True)
            result = await db.execute(query)
            users = result.scalars().all()

            logger.info(f"Generating daily reports for {len(users)} active users")

            reports_generated = 0
            for user in users:
                try:
                    # Vérifier si un rapport existe déjà pour aujourd'hui
                    existing_query = select(DailyReportModel).where(
                        DailyReportModel.user_id == user.id,
                        DailyReportModel.date == today
                    )
                    existing_result = await db.execute(existing_query)
                    existing_report = existing_result.scalar_one_or_none()

                    if existing_report:
                        logger.info(f"Report already exists for user {user.id}, skipping")
                        continue

                    # Générer le rapport
                    service = DailyReviewService(db)
                    report = await service.generate_daily_report(user.id)

                    # Stocker en BDD
                    report_db = DailyReportModel(
                        user_id=report.user_id,
                        date=report.date.date(),
                        summary=report.summary,
                        total_projects=report.total_projects,
                        active_projects=report.active_projects,
                        total_tasks=report.total_tasks,
                        completed_today=report.completed_today,
                        blockers_count=report.blockers_count,
                        projects_analysis=[p.dict() for p in report.projects],
                        top_priorities=report.top_priorities,
                        recommendations=report.recommendations,
                    )

                    db.add(report_db)
                    await db.commit()

                    reports_generated += 1
                    logger.info(f"✅ Generated daily report for user {user.id} ({user.email})")

                    # Push du briefing sur le téléphone (si NTFY_TOPIC configuré)
                    await notify_briefing(report)

                except Exception as e:
                    logger.error(f"❌ Error generating report for user {user.id}: {e}", exc_info=True)
                    # Continue avec les autres utilisateurs même en cas d'erreur
                    continue

            logger.info(f"✅ Daily reports job completed: {reports_generated}/{len(users)} reports generated")

        except Exception as e:
            logger.error(f"❌ Daily reports job failed: {e}", exc_info=True)


async def check_veille_recurrence_job() -> None:
    """
    Job APScheduler : vérifie les VeilleTopic qui doivent être rescannés
    et crée automatiquement de nouvelles tâches VEILLE en READY.
    """
    set_correlation_id()  # Correlation ID unique par job
    logger.info("🔄 Running scheduled job: check_veille_recurrence")

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()

            # Chercher les topics avec next_scan dépassé et pas de tâche active
            topics_query = (
                select(VeilleTopic)
                .where(VeilleTopic.enabled == True)
                .where(VeilleTopic.next_scan != None)  # noqa: E711
                .where(VeilleTopic.next_scan <= now)
            )
            result = await db.execute(topics_query)
            due_topics = result.scalars().all()

            if not due_topics:
                logger.info("✅ No veille topics due for scanning")
                return

            created_count = 0
            for topic in due_topics:
                # Vérifier qu'il n'y a pas déjà une tâche active pour ce topic
                active_check = (
                    select(Task)
                    .where(Task.veille_topic_id == topic.id)
                    .where(Task.status.in_([TaskStatus.READY, TaskStatus.GENERATING]))
                )
                active_result = await db.execute(active_check)
                if active_result.scalar_one_or_none():
                    logger.info(f"⏭️ Topic {topic.id} already has active task, skipping")
                    continue

                # Trouver la dernière tâche complétée pour ce topic (pour copier les params)
                last_task_query = (
                    select(Task)
                    .where(Task.veille_topic_id == topic.id)
                    .where(Task.status == TaskStatus.COMPLETED)
                    .order_by(Task.completed_at.desc())
                    .limit(1)
                )
                last_result = await db.execute(last_task_query)
                last_task = last_result.scalar_one_or_none()

                # Créer la nouvelle occurrence
                new_task = Task(
                    project_id=topic.project_id,
                    title=last_task.title if last_task else f"Veille — {topic.name}",
                    description=last_task.description if last_task else topic.description,
                    task_type=TaskType.VEILLE,
                    status=TaskStatus.READY,
                    veille_topic_id=topic.id,
                    task_metadata={
                        'keywords': topic.keywords or [],
                        'frequency': topic.scan_frequency,
                        'auto_generated': True,
                        'occurrence_from_topic': topic.id,
                    }
                )
                db.add(new_task)

                # Replanifier le topic — sinon le job recrée une tâche
                # à chaque tick de 15 min dès que la précédente est terminée
                topic.last_scan = now
                topic.next_scan = topic.calculate_next_scan()

                created_count += 1
                logger.info(
                    f"🆕 Created recurring veille task for topic {topic.id} ({topic.name}), "
                    f"next scan: {topic.next_scan}"
                )

            if created_count > 0:
                await db.commit()

            logger.info(f"✅ Veille recurrence check: {created_count} new tasks created from {len(due_topics)} due topics")

        except Exception as e:
            logger.error(f"❌ Veille recurrence check failed: {e}", exc_info=True)


async def watchdog_generating_tasks_job() -> None:
    """
    Job APScheduler : détecte les tâches bloquées en GENERATING depuis trop longtemps
    et les remet en FAILED pour permettre un retry.

    Seuil : 15 minutes (une génération normale prend 3-5 min max).
    """
    set_correlation_id()  # Correlation ID unique par job
    logger.info("🐕 Running scheduled job: watchdog_generating_tasks")

    async with AsyncSessionLocal() as db:
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=15)

            # Trouver les tâches bloquées en GENERATING depuis > 15 min
            stmt = (
                select(Task)
                .where(
                    and_(
                        Task.status == TaskStatus.GENERATING,
                        Task.started_at != None,  # noqa: E711
                        Task.started_at <= cutoff,
                    )
                )
            )
            result = await db.execute(stmt)
            stuck_tasks = result.scalars().all()

            if not stuck_tasks:
                logger.info("✅ No stuck GENERATING tasks found")
                return

            for task in stuck_tasks:
                elapsed = datetime.utcnow() - task.started_at
                logger.warning(
                    f"⚠️ Task {task.id} stuck in GENERATING for {elapsed.total_seconds()/60:.1f} min — marking FAILED"
                )
                task.status = TaskStatus.FAILED
                task.retry_count = (task.retry_count or 0) + 1
                task.last_failed_at = datetime.utcnow()

                # Log l'événement
                log = TaskLog(
                    task_id=task.id,
                    event_type=TaskEventType.GENERATION_FAILED,
                    details={
                        'error': f'Watchdog: task stuck in GENERATING for {elapsed.total_seconds()/60:.1f} minutes',
                        'error_type': 'WatchdogTimeout',
                        'retry_count': task.retry_count,
                    }
                )
                db.add(log)

            await db.commit()
            logger.info(f"🐕 Watchdog: reset {len(stuck_tasks)} stuck tasks to FAILED")

        except Exception as e:
            logger.error(f"❌ Watchdog job failed: {e}", exc_info=True)


def start_scheduler() -> None:
    """
    Démarre le scheduler APScheduler

    Configure et lance les jobs:
    - Traitement de la file d'attente (toutes les X minutes)
    - Génération des rapports quotidiens (chaque jour à 8h00)
    - Vérification de la récurrence des veilles (toutes les 15 min)
    - Watchdog pour tâches bloquées en GENERATING (toutes les 5 min)
    """
    # Job 1: Traitement de la file d'attente
    scheduler.add_job(
        process_queue_job,
        trigger=IntervalTrigger(minutes=settings.ORCHESTRATOR_INTERVAL_MINUTES),
        id='process_queue',
        name='Process task queue',
        replace_existing=True,
        max_instances=1  # Une seule instance du job à la fois
    )

    # Job 2: Génération des rapports quotidiens à 8h00
    scheduler.add_job(
        generate_daily_reports_job,
        trigger=CronTrigger(hour=8, minute=0),  # Chaque jour à 8h00
        id='daily_reports',
        name='Generate daily reports',
        replace_existing=True,
        max_instances=1
    )

    # Job 3: Vérification de la récurrence des veilles (toutes les 15 min)
    scheduler.add_job(
        check_veille_recurrence_job,
        trigger=IntervalTrigger(minutes=15),
        id='check_veille_recurrence',
        name='Check veille recurrence',
        replace_existing=True,
        max_instances=1
    )

    # Job 4: Watchdog — détecte les tâches bloquées en GENERATING (toutes les 5 min)
    scheduler.add_job(
        watchdog_generating_tasks_job,
        trigger=IntervalTrigger(minutes=5),
        id='watchdog_generating',
        name='Watchdog: unstick GENERATING tasks',
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()
    logger.info(
        f"🚀 Scheduler started\n"
        f"   - Task queue processing: every {settings.ORCHESTRATOR_INTERVAL_MINUTES} min\n"
        f"   - Daily reports: every day at 8:00 AM\n"
        f"   - Veille recurrence check: every 15 min\n"
        f"   - Watchdog (stuck tasks): every 5 min"
    )


def stop_scheduler() -> None:
    """
    Arrête le scheduler APScheduler

    Appelé lors du shutdown de l'application
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Scheduler stopped")
