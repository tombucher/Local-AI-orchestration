"""
API endpoints for Time Entries (tracking temps)
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Project, Task, TimeEntry
from app.schemas import (
    TimeEntryStart, TimeEntryStop, TimeEntryResponse, TimeEntryList
)

router = APIRouter()


@router.post("/start", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def start_timer(
    timer_data: TimeEntryStart,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Démarrer un timer pour un projet
    
    Un seul timer actif par user à la fois.
    Si un timer est déjà actif, retourne une erreur.
    """
    # Vérifier qu'il n'y a pas déjà un timer actif
    query = select(TimeEntry).where(
        and_(
            TimeEntry.user_id == current_user.id,
            TimeEntry.ended_at.is_(None)
        )
    )
    result = await db.execute(query)
    active_timer = result.scalar_one_or_none()
    
    if active_timer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timer already running for project {active_timer.project_id}. Stop it first."
        )
    
    # Vérifier que le projet existe et appartient à l'user
    query = select(Project).where(
        and_(
            Project.id == timer_data.project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Si task_id fourni, vérifier qu'elle existe et appartient au projet
    if timer_data.task_id:
        query = select(Task).where(
            and_(
                Task.id == timer_data.task_id,
                Task.project_id == timer_data.project_id
            )
        )
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or doesn't belong to this project"
            )
    
    # Créer le timer
    timer = TimeEntry(
        project_id=timer_data.project_id,
        task_id=timer_data.task_id,
        user_id=current_user.id,
        started_at=datetime.utcnow(),
        notes=timer_data.notes
    )
    
    db.add(timer)
    await db.commit()
    await db.refresh(timer)
    
    return timer


@router.post("/stop", response_model=TimeEntryResponse)
async def stop_timer(
    timer_data: TimeEntryStop,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Arrêter le timer actif
    
    Calcule automatiquement la durée et la sauvegarde.
    """
    # Récupérer le timer actif
    query = select(TimeEntry).where(
        and_(
            TimeEntry.user_id == current_user.id,
            TimeEntry.ended_at.is_(None)
        )
    )
    result = await db.execute(query)
    timer = result.scalar_one_or_none()
    
    if not timer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active timer found"
        )
    
    # Arrêter le timer
    timer.ended_at = datetime.utcnow()
    duration = (timer.ended_at - timer.started_at).total_seconds()
    timer.duration_seconds = int(duration)
    
    # Mettre à jour les notes si fournies
    if timer_data.notes:
        timer.notes = timer_data.notes
    
    await db.commit()
    await db.refresh(timer)
    
    return timer


@router.get("/current", response_model=Optional[TimeEntryResponse])
async def get_current_timer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer le timer actuellement actif (si existe)
    
    Retourne None si aucun timer actif.
    """
    query = select(TimeEntry).where(
        and_(
            TimeEntry.user_id == current_user.id,
            TimeEntry.ended_at.is_(None)
        )
    )
    result = await db.execute(query)
    timer = result.scalar_one_or_none()
    
    return timer


@router.get("/entries", response_model=TimeEntryList)
async def list_time_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Liste les entrées de temps de l'utilisateur
    
    Filtres disponibles:
    - project_id: Entrées pour un projet spécifique
    - task_id: Entrées pour une tâche spécifique
    
    Seules les entrées terminées (ended_at != NULL) sont retournées.
    """
    # Requête de base
    query = select(TimeEntry).where(
        and_(
            TimeEntry.user_id == current_user.id,
            TimeEntry.ended_at.is_not(None)
        )
    )
    
    # Filtres
    if project_id:
        query = query.where(TimeEntry.project_id == project_id)
    if task_id:
        query = query.where(TimeEntry.task_id == task_id)
    
    # Tri par date de début décroissante
    query = query.order_by(TimeEntry.started_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return TimeEntryList(
        items=entries,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )
