"""
Le briefing du jour : généré une fois par jour et par utilisateur, quoi qu'il arrive.

Il était manqué dès que le Mac dormait à 8 h (tolérance d'une seconde du
planificateur) : aucun briefing les 25 et 26/09/2026. Désormais le planificateur
rattrape un passage manqué, et l'ouverture de l'outil le prépare s'il manque.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Optional, Set
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.daily_report import DailyReport as DailyReportModel
from app.services.daily_review_service import DailyReviewService

logger = logging.getLogger(__name__)

# Utilisateurs dont le briefing est en cours de préparation (un seul à la fois)
_en_preparation: Set[int] = set()


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def today_local() -> date:
    return datetime.now(local_tz()).date()


async def today_report(db: AsyncSession, user_id: int) -> Optional[DailyReportModel]:
    return (await db.execute(
        select(DailyReportModel).where(DailyReportModel.user_id == user_id,
                                       DailyReportModel.date == today_local())
    )).scalars().first()


async def build_and_store_report(db: AsyncSession, user_id: int, replace: bool = False):
    """Génère le briefing du jour et l'enregistre. Renvoie (modèle BDD, rapport)."""
    existing = await today_report(db, user_id)
    if existing and not replace:
        return existing, None
    if existing:
        await db.delete(existing)
        await db.commit()

    report = await DailyReviewService(db).generate_daily_report(user_id)
    report_db = DailyReportModel(
        user_id=report.user_id,
        date=today_local(),
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
    await db.refresh(report_db)
    return report_db, report


def is_preparing(user_id: int) -> bool:
    return user_id in _en_preparation


async def _prepare(user_id: int) -> None:
    try:
        async with AsyncSessionLocal() as db:
            await build_and_store_report(db, user_id)
        logger.info(f"☀️ Briefing du jour préparé pour l'utilisateur {user_id}")
    except Exception as e:
        logger.error(f"❌ Briefing de l'utilisateur {user_id} en échec : {e}", exc_info=True)
    finally:
        _en_preparation.discard(user_id)


async def ensure_today_report(db: AsyncSession, user_id: int) -> str:
    """'ready' si le briefing du jour existe, sinon lance sa préparation → 'preparing'."""
    if await today_report(db, user_id):
        return "ready"
    if user_id not in _en_preparation:
        _en_preparation.add(user_id)
        asyncio.create_task(_prepare(user_id))
    return "preparing"
