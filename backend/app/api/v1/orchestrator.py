"""
API endpoints pour l'orchestrateur de génération de code
"""
import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.project import Project
from app.services.llm_client import OllamaClient
from app.services.unified_orchestrator import UnifiedOrchestrator
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class OrchestratorStatus(BaseModel):
    """Statut de l'orchestrateur"""
    running: bool
    queue_size: int
    ollama_available: bool
    interval_minutes: int


class QueueTask(BaseModel):
    """Tâche dans la file d'attente"""
    id: int
    title: str
    priority: str
    project_name: str
    created_at: datetime


class QueueStats(BaseModel):
    """Statistiques de la file d'attente"""
    ready: int
    generating: int
    manual_review: int
    failed: int


class ForceGenerateResponse(BaseModel):
    """Réponse de la génération forcée"""
    status: str
    task_id: int
    message: str


# Endpoints
@router.get("/status", response_model=OrchestratorStatus)
async def get_orchestrator_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère l'état de l'orchestrateur

    Returns:
        Statut avec queue size et disponibilité Ollama
    """
    # Compte les tâches READY de l'utilisateur
    stmt = (
        select(func.count(Task.id))
        .select_from(Task)
        .join(Project)
        .filter(
            and_(
                Task.status == TaskStatus.READY,
                Project.user_id == current_user.id
            )
        )
    )
    result = await db.execute(stmt)
    queue_size = result.scalar() or 0

    # Check Ollama
    llm_client = OllamaClient(host=settings.OLLAMA_HOST)
    ollama_ok = await llm_client.health_check()

    return OrchestratorStatus(
        running=True,  # Scheduler toujours actif
        queue_size=queue_size,
        ollama_available=ollama_ok,
        interval_minutes=settings.ORCHESTRATOR_INTERVAL_MINUTES
    )


@router.get("/queue", response_model=List[QueueTask])
async def get_task_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère la file d'attente des tâches READY

    Returns:
        Liste des tâches en attente de traitement
    """
    stmt = (
        select(Task, Project.name)
        .join(Project)
        .filter(
            and_(
                Task.status == TaskStatus.READY,
                Project.user_id == current_user.id
            )
        )
        .order_by(Task.priority.asc(), Task.created_at.asc())
        .limit(20)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        QueueTask(
            id=task.id,
            title=task.title,
            priority=task.priority.value,
            project_name=project_name,
            created_at=task.created_at
        )
        for task, project_name in rows
    ]


@router.get("/stats", response_model=QueueStats)
async def get_queue_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les statistiques de la file d'attente

    Returns:
        Nombre de tâches par statut
    """
    stats = {}

    for task_status in [TaskStatus.READY, TaskStatus.GENERATING, TaskStatus.MANUAL_REVIEW, TaskStatus.FAILED]:
        stmt = (
            select(func.count(Task.id))
            .select_from(Task)
            .join(Project)
            .filter(
                and_(
                    Task.status == task_status,
                    Project.user_id == current_user.id
                )
            )
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        stats[task_status.value] = count

    return QueueStats(
        ready=stats.get('ready', 0),
        generating=stats.get('generating', 0),
        manual_review=stats.get('manual_review', 0),
        failed=stats.get('failed', 0)
    )


@router.post("/tasks/{task_id}/generate", response_model=ForceGenerateResponse)
async def force_generate_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Force la génération immédiate d'une tâche (override queue)

    Bypasse le scheduler pour générer immédiatement le code

    Args:
        task_id: ID de la tâche à générer

    Returns:
        Résultat de la génération

    Raises:
        404: Tâche non trouvée
        400: Tâche pas dans le bon statut
        500: Erreur de génération
    """
    # Récupère la tâche
    stmt = (
        select(Task)
        .join(Project)
        .filter(
            and_(
                Task.id == task_id,
                Project.user_id == current_user.id
            )
        )
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    if task.status != TaskStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task must be READY (current status: {task.status.value})"
        )

    # Génération immédiate via UnifiedOrchestrator
    orchestrator = UnifiedOrchestrator(db)

    try:
        logger.info(f"🚀 Force generating task {task_id}")
        await orchestrator.handle_task(task)
        await db.commit()

        return ForceGenerateResponse(
            status="success",
            task_id=task_id,
            message=f"Task generated successfully for task {task_id}"
        )

    except Exception as e:
        logger.error(f"❌ Force generation failed for task {task_id}: {e}")
        await orchestrator.handle_failure(task, e)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


@router.get("/models", response_model=List[str])
async def list_available_models(
    current_user: User = Depends(get_current_user)
):
    """
    Liste les modèles Ollama disponibles

    Returns:
        Liste des noms de modèles
    """
    llm_client = OllamaClient(host=settings.OLLAMA_HOST)
    models = llm_client.list_models()

    return models
