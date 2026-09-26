"""
Scheduler pour l'exécution périodique des tâches d'orchestration
"""
import logging
from datetime import date, datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_

from app.core.database import AsyncSessionLocal
from app.core.logging import set_correlation_id
from app.services.unified_orchestrator import UnifiedOrchestrator
from app.services.notifier import notify_briefing
from app.services import briefing
from app.services.task_progress import clear_progress, is_running
from app.models.user import User
from app.models.task import Task, TaskType, TaskStatus
from app.models.task_log import TaskLog, TaskEventType
from app.models.veille_topic import VeilleTopic
from app.models.daily_report import DailyReport as DailyReportModel
from app.core.config import settings

logger = logging.getLogger(__name__)

# Instance globale du scheduler
scheduler = AsyncIOScheduler()

# Chien de garde : délai avant de déclarer morte une tâche absente du processus
# (le temps qu'elle démarre), et durée maximale d'une tâche vivante.
WATCHDOG_GRACE = timedelta(minutes=2)
WATCHDOG_MAX_RUNTIME = timedelta(hours=2)


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
    Job APScheduler : briefing du jour pour chaque utilisateur actif.

    Exécuté chaque matin à BRIEFING_HOUR (fuseau TIMEZONE), et rattrapé au réveil
    du Mac si l'heure est passée pendant sa veille.
    """
    set_correlation_id()  # Correlation ID unique par job
    logger.info("📊 Running scheduled job: generate_daily_reports")

    async with AsyncSessionLocal() as db:
        try:
            users = (await db.execute(select(User).where(User.is_active == True))).scalars().all()
            logger.info(f"Generating daily reports for {len(users)} active users")

            reports_generated = 0
            for user in users:
                # Déjà en préparation depuis l'ouverture de l'outil
                if briefing.is_preparing(user.id):
                    continue
                briefing._en_preparation.add(user.id)
                try:
                    _, report = await briefing.build_and_store_report(db, user.id)
                    if report is None:
                        logger.info(f"Report already exists for user {user.id}, skipping")
                        continue
                    reports_generated += 1
                    logger.info(f"✅ Generated daily report for user {user.id}")
                    # Push du briefing sur le téléphone (si NTFY_TOPIC configuré)
                    await notify_briefing(report)
                except Exception as e:
                    await db.rollback()
                    logger.error(f"❌ Error generating report for user {user.id}: {e}", exc_info=True)
                finally:
                    briefing._en_preparation.discard(user.id)

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
    Job APScheduler : débloque les tâches GENERATING qui ne tournent plus.

    Une tâche est morte si elle ne vit plus dans ce processus (serveur redémarré
    pendant qu'elle tournait) : débloquée après un court délai de grâce. Une
    tâche vivante n'est interrompue qu'au-delà d'un plafond — une veille prend
    couramment 15 à 20 minutes, l'ancien seuil fixe de 15 min l'aurait tuée.

    L'ancienne version plantait à chaque passage (dates avec et sans fuseau) :
    aucune tâche coincée n'était jamais débloquée.
    """
    set_correlation_id()  # Correlation ID unique par job
    logger.info("🐕 Running scheduled job: watchdog_generating_tasks")

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            generating = (await db.execute(
                select(Task).where(Task.status == TaskStatus.GENERATING)
            )).unique().scalars().all()

            stuck = []
            for task in generating:
                started = task.started_at or now
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                elapsed = now - started
                if not is_running(task.id) and elapsed > WATCHDOG_GRACE:
                    stuck.append((task, elapsed, "interrompue : le serveur a redémarré pendant la génération"))
                elif elapsed > WATCHDOG_MAX_RUNTIME:
                    stuck.append((task, elapsed, "trop longue : le modèle ne répond plus"))

            if not stuck:
                logger.info("✅ No stuck GENERATING tasks found")
                return

            for task, elapsed, raison in stuck:
                minutes = elapsed.total_seconds() / 60
                logger.warning(f"⚠️ Task {task.id} {raison} ({minutes:.0f} min) — marking FAILED")
                task.status = TaskStatus.FAILED
                task.retry_count = (task.retry_count or 0) + 1
                task.last_failed_at = now
                clear_progress(task.id)
                db.add(TaskLog(
                    task_id=task.id,
                    event_type=TaskEventType.GENERATION_FAILED,
                    details={
                        'error': f"Génération {raison} ({minutes:.0f} min). Relance-la.",
                        'error_type': 'WatchdogTimeout',
                        'retry_count': task.retry_count,
                    }
                ))

            await db.commit()
            logger.info(f"🐕 Watchdog: reset {len(stuck)} stuck tasks to FAILED")

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
    # Heure locale de l'utilisateur, pas UTC. misfire_grace_time : un Mac en
    # veille à l'heure dite rattrape le briefing à son réveil (la tolérance par
    # défaut d'une seconde le faisait sauter).
    scheduler.add_job(
        generate_daily_reports_job,
        trigger=CronTrigger(hour=settings.BRIEFING_HOUR, minute=0, timezone=briefing.local_tz()),
        id='daily_reports',
        name='Generate daily reports',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=14 * 3600,
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
        max_instances=1,
        # Premier passage peu après le démarrage : c'est justement après un
        # redémarrage que des tâches restent coincées.
        next_run_time=datetime.now(timezone.utc) + WATCHDOG_GRACE + timedelta(seconds=30),
    )

    scheduler.start()
    logger.info(
        f"🚀 Scheduler started\n"
        f"   - Task queue processing: every {settings.ORCHESTRATOR_INTERVAL_MINUTES} min\n"
        f"   - Daily reports: every day at {settings.BRIEFING_HOUR}:00 ({settings.TIMEZONE})\n"
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
