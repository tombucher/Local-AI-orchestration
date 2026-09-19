"""
API endpoints for Daily Reports
"""

from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.daily_report import DailyReport as DailyReportModel
from app.services.notifier import notify_briefing
from app.services.daily_review_service import DailyReviewService, DailyReport, ProjectStatus
from pydantic import BaseModel, Field


router = APIRouter()


# ============================================================
# SCHEMAS DE RÉPONSE
# ============================================================

class BlockerResponse(BaseModel):
    """Blocage dans un projet."""
    type: str
    description: str
    severity: str
    suggestion: str


class ProjectStatusResponse(BaseModel):
    """Statut d'un projet dans le rapport."""
    project_id: int
    project_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    ready_tasks: int
    failed_tasks: int
    completion_rate: float
    p1_tasks: int
    blockers: List[BlockerResponse] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    health_status: str
    # Proactivité : action évidente + relance des projets stagnants
    next_obvious_action: Optional[str] = None
    ready_task_titles: List[str] = Field(default_factory=list)
    is_stagnant: bool = False
    suggested_tasks: List[dict] = Field(default_factory=list)


class DailyReportResponse(BaseModel):
    """Rapport quotidien complet."""
    id: int
    user_id: int
    date: date
    summary: str
    total_projects: int
    active_projects: int
    total_tasks: int
    completed_today: int
    blockers_count: int
    projects: List[ProjectStatusResponse] = Field(default_factory=list)
    top_priorities: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class DailyReportListResponse(BaseModel):
    """Liste de rapports quotidiens."""
    total: int
    reports: List[DailyReportResponse]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/daily", response_model=DailyReportListResponse)
async def list_daily_reports(
    limit: int = Query(30, ge=1, le=90),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Liste les rapports quotidiens de l'utilisateur.

    Par défaut, retourne les 30 derniers jours.
    """
    # Compter le total
    count_query = select(func.count(DailyReportModel.id)).where(
        DailyReportModel.user_id == current_user.id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Récupérer les rapports
    query = (
        select(DailyReportModel)
        .where(DailyReportModel.user_id == current_user.id)
        .order_by(desc(DailyReportModel.date))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    reports_db = result.scalars().all()

    # Convertir en réponse
    reports = []
    for report_db in reports_db:
        # Parser les projects_analysis JSON
        projects_json = report_db.projects_analysis or []
        projects = [
            ProjectStatusResponse(
                project_id=p.get("project_id"),
                project_name=p.get("project_name"),
                total_tasks=p.get("total_tasks", 0),
                completed_tasks=p.get("completed_tasks", 0),
                in_progress_tasks=p.get("in_progress_tasks", 0),
                ready_tasks=p.get("ready_tasks", 0),
                failed_tasks=p.get("failed_tasks", 0),
                completion_rate=p.get("completion_rate", 0.0),
                p1_tasks=p.get("p1_tasks", 0),
                blockers=[BlockerResponse(**b) for b in p.get("blockers", [])],
                recommended_actions=p.get("recommended_actions", []),
                health_status=p.get("health_status", "healthy"),
                next_obvious_action=p.get("next_obvious_action"),
                ready_task_titles=p.get("ready_task_titles", []),
                is_stagnant=p.get("is_stagnant", False),
                suggested_tasks=p.get("suggested_tasks", []),
            )
            for p in projects_json
        ]

        reports.append(
            DailyReportResponse(
                id=report_db.id,
                user_id=report_db.user_id,
                date=report_db.date,
                summary=report_db.summary,
                total_projects=report_db.total_projects,
                active_projects=report_db.active_projects,
                total_tasks=report_db.total_tasks,
                completed_today=report_db.completed_today,
                blockers_count=report_db.blockers_count,
                projects=projects,
                top_priorities=report_db.top_priorities or [],
                recommendations=report_db.recommendations or [],
                created_at=report_db.created_at,
            )
        )

    return DailyReportListResponse(total=total, reports=reports)


@router.get("/daily/latest", response_model=Optional[DailyReportResponse])
async def get_latest_daily_report(
current_user: User = Depends(get_current_user),
db: AsyncSession = Depends(get_db)
):
    """
    Récupère le dernier rapport quotidien (aujourd'hui ou le plus récent).
    """
    query = (
        select(DailyReportModel)
        .where(DailyReportModel.user_id == current_user.id)
        .order_by(desc(DailyReportModel.date))
        .limit(1)
    )
    result = await db.execute(query)
    report_db = result.scalar_one_or_none()
    if not report_db:
        return None

    # Parser les projects_analysis JSON
    projects_json = report_db.projects_analysis or []
    projects = []
    total_in_progress_tasks = 0

    for p in projects_json:
        # Calculer le nombre réel de tâches en cours pour ce projet
        # En utilisant uniquement les tâches qui sont effectivement en cours
        real_in_progress = p.get("in_progress_tasks", 0)
        total_in_progress_tasks += real_in_progress

        projects.append(
            ProjectStatusResponse(
                project_id=p.get("project_id"),
                project_name=p.get("project_name"),
                total_tasks=p.get("total_tasks", 0),
                completed_tasks=p.get("completed_tasks", 0),
                in_progress_tasks=real_in_progress,  # Utiliser la valeur réelle
                ready_tasks=p.get("ready_tasks", 0),
                failed_tasks=p.get("failed_tasks", 0),
                completion_rate=p.get("completion_rate", 0.0),
                p1_tasks=p.get("p1_tasks", 0),
                blockers=[BlockerResponse(**b) for b in p.get("blockers", [])],
                recommended_actions=p.get("recommended_actions", []),
                health_status=p.get("health_status", "healthy"),
                next_obvious_action=p.get("next_obvious_action"),
                ready_task_titles=p.get("ready_task_titles", []),
                is_stagnant=p.get("is_stagnant", False),
                suggested_tasks=p.get("suggested_tasks", []),
            )
        )

    # Calculer le nombre réel de projets actifs
    active_projects_count = sum(
        1 for p in projects
        if p.in_progress_tasks > 0 or p.ready_tasks > 0 or p.failed_tasks > 0
    )

    return DailyReportResponse(
        id=report_db.id,
        user_id=report_db.user_id,
        date=report_db.date,
        summary=report_db.summary,
        total_projects=report_db.total_projects,
        active_projects=active_projects_count,
        total_tasks=report_db.total_tasks,
        completed_today=report_db.completed_today,
        blockers_count=report_db.blockers_count,
        projects=projects,
        top_priorities=report_db.top_priorities or [],
        recommendations=report_db.recommendations or [],
        created_at=report_db.created_at,
    )


@router.post("/daily/generate", response_model=DailyReportResponse)
async def generate_daily_report(
    notify: bool = Query(False, description="Envoyer aussi le briefing via ntfy"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Génère manuellement un rapport quotidien (pour test ou re-génération).

    En production, ce sera déclenché automatiquement par le scheduler à 8h.
    """
    # Vérifier si un rapport existe déjà pour aujourd'hui
    today = date.today()
    existing_query = select(DailyReportModel).where(
        and_(
            DailyReportModel.user_id == current_user.id,
            DailyReportModel.date == today
        )
    )
    existing_result = await db.execute(existing_query)
    existing_report = existing_result.scalar_one_or_none()

    if existing_report:
        # Supprimer l'ancien pour regénérer
        await db.delete(existing_report)
        await db.commit()

    # Générer le nouveau rapport
    service = DailyReviewService(db)
    report = await service.generate_daily_report(current_user.id)
    if notify:
        await notify_briefing(report)

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
    await db.refresh(report_db)

    # Convertir en réponse
    projects = [
        ProjectStatusResponse(
            project_id=p.project_id,
            project_name=p.project_name,
            total_tasks=p.total_tasks,
            completed_tasks=p.completed_tasks,
            in_progress_tasks=p.in_progress_tasks,
            ready_tasks=p.ready_tasks,
            failed_tasks=p.failed_tasks,
            completion_rate=p.completion_rate,
            p1_tasks=p.p1_tasks,
            blockers=[BlockerResponse(**b.dict()) for b in p.blockers],
            recommended_actions=p.recommended_actions,
            health_status=p.health_status,
            next_obvious_action=p.next_obvious_action,
            ready_task_titles=p.ready_task_titles,
            is_stagnant=p.is_stagnant,
            suggested_tasks=p.suggested_tasks,
        )
        for p in report.projects
    ]

    return DailyReportResponse(
        id=report_db.id,
        user_id=report_db.user_id,
        date=report_db.date,
        summary=report_db.summary,
        total_projects=report_db.total_projects,
        active_projects=report_db.active_projects,
        total_tasks=report_db.total_tasks,
        completed_today=report_db.completed_today,
        blockers_count=report_db.blockers_count,
        projects=projects,
        top_priorities=report_db.top_priorities,
        recommendations=report_db.recommendations,
        created_at=report_db.created_at,
    )
