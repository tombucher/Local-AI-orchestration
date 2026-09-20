"""
API endpoints for Projects
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError, ValidationError, ConflictError
from app.api.deps import get_current_user
from app.models import User, Project, Task, TimeEntry, ProjectStatus, TaskStatus
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats, ProjectList
)
from app.schemas.project import (
    TaskPreview, ProjectFinalizationPreview, PreviewFinalizationRequest,
    TaskValidationInput, FinalizeValidationRequest
)
from app.schemas.unified_project import (
    StartProjectChatRequest, StartProjectChatResponse,
    FinalizeProjectRequest, FinalizeProjectResponse, TaskGenerated
)
from app.schemas.project_analysis import (
    ProjectAnalysisResponse, CreateTasksRequest, CreateTasksResponse,
    TaskSuggestionSchema, VeilleSuggestionSchema, BlockerSchema,
    RefineTaskRequest, RefineTaskResponse
)
from app.models.task_log import TaskLog, TaskEventType
from app.services.project_analyzer import ProjectAnalyzer, TaskSuggestion, AnalysisError
from app.services.critical_path import CriticalPathService
from app.services.maturity import MaturityService
from app.models.veille_topic import VeilleTopic, VeilleScope

router = APIRouter()


@router.get("/", response_model=ProjectList)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    type: Optional[str] = None,
    status: Optional[ProjectStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Liste tous les projets de l'utilisateur avec pagination

    Filtres disponibles:
    - type: professional, personal, research
    - status: active, archived, paused

    Par défaut, exclut les projets archivés
    """
    # Requête de base
    query = select(Project).where(Project.user_id == current_user.id)

    # Filtres
    if type:
        query = query.where(Project.type == type)
    if status:
        query = query.where(Project.status == status)
    else:
        # Par défaut, exclure les projets archivés
        query = query.where(Project.status != ProjectStatus.ARCHIVED)
    
    # Tri par date de mise à jour décroissante
    query = query.order_by(Project.updated_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()

    # Enrichir avec les statistiques de tâches
    project_responses = []
    for project in projects:
        # Compter les tâches totales (excluant CANCELLED)
        total_tasks_query = select(func.count(Task.id)).where(
            and_(
                Task.project_id == project.id,
                Task.status != TaskStatus.CANCELLED
            )
        )
        total_tasks_result = await db.execute(total_tasks_query)
        tasks_total = total_tasks_result.scalar() or 0

        # Compter les tâches complétées
        completed_tasks_query = select(func.count(Task.id)).where(
            and_(
                Task.project_id == project.id,
                Task.status == TaskStatus.COMPLETED
            )
        )
        completed_tasks_result = await db.execute(completed_tasks_query)
        tasks_completed = completed_tasks_result.scalar() or 0

        # Créer ProjectResponse avec les stats
        project_dict = {
            **project.__dict__,
            'tasks_total': tasks_total,
            'tasks_completed': tasks_completed
        }
        project_responses.append(ProjectResponse(**project_dict))

    return ProjectList(
        items=project_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Créer un nouveau projet
    
    Pour les projets professionnels, financial_config est requis
    """
    # Créer le projet
    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        type=project_in.type,
        features=project_in.features.model_dump(),
        financial_config=project_in.financial_config.model_dump() if project_in.financial_config else None
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupérer les détails d'un projet"""
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise EntityNotFoundError("Project", str(project_id))
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Modifier un projet"""
    # Récupérer le projet
    query = select(Project).where(
        and_(
            Project.id == project_id,
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
    
    # Mettre à jour les champs fournis
    update_data = project_in.model_dump(exclude_unset=True)

    # model_dump() convertit déjà tout en dict, pas besoin de reconvertir
    # Les champs features et financial_config sont déjà des dict après model_dump()

    for field, value in update_data.items():
        setattr(project, field, value)

    try:
        await db.commit()
        await db.refresh(project)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Archiver un projet (soft delete)

    Change le status à 'archived' au lieu de supprimer
    Archive également toutes les tâches associées en les annulant
    """
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise EntityNotFoundError("Project", str(project_id))

    # Archiver le projet
    project.status = ProjectStatus.ARCHIVED

    # Annuler toutes les tâches associées qui ne sont pas déjà terminées ou annulées
    from app.models.task import Task, TaskStatus
    tasks_query = select(Task).where(
        and_(
            Task.project_id == project_id,
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        )
    )
    tasks_result = await db.execute(tasks_query)
    tasks = tasks_result.scalars().all()

    for task in tasks:
        task.status = TaskStatus.CANCELLED

    await db.commit()


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les statistiques d'un projet
    
    Inclut:
    - Nombre total de tâches
    - Répartition par status
    - Répartition par priorité
    - Temps total (si projet PRO)
    - Coût estimé (si projet PRO)
    """
    # Vérifier que le projet existe et appartient à l'user
    query = select(Project).where(
        and_(
            Project.id == project_id,
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
    
    # Count total tasks
    total_tasks_query = select(func.count()).where(Task.project_id == project_id)
    total_tasks_result = await db.execute(total_tasks_query)
    total_tasks = total_tasks_result.scalar()
    
    # Tasks by status
    tasks_by_status_query = select(
        Task.status,
        func.count(Task.id)
    ).where(Task.project_id == project_id).group_by(Task.status)
    tasks_by_status_result = await db.execute(tasks_by_status_query)
    tasks_by_status = {str(status): count for status, count in tasks_by_status_result}
    
    # Tasks by priority
    tasks_by_priority_query = select(
        Task.priority,
        func.count(Task.id)
    ).where(Task.project_id == project_id).group_by(Task.priority)
    tasks_by_priority_result = await db.execute(tasks_by_priority_query)
    tasks_by_priority = {str(priority): count for priority, count in tasks_by_priority_result}
    
    # Time entries (si projet PRO)
    total_time = None
    estimated_cost = None
    
    if project.type.value == "professional":
        time_query = select(func.sum(TimeEntry.duration_seconds)).where(
            and_(
                TimeEntry.project_id == project_id,
                TimeEntry.ended_at.is_not(None)
            )
        )
        time_result = await db.execute(time_query)
        total_time = time_result.scalar() or 0
        
        # Calculer coût estimé
        if project.financial_config and 'hourly_rate' in project.financial_config:
            hourly_rate = project.financial_config['hourly_rate']
            estimated_cost = (total_time / 3600) * hourly_rate
    
    return ProjectStats(
        total_tasks=total_tasks,
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority,
        total_time_seconds=total_time,
        estimated_cost=estimated_cost
    )


@router.post("/{project_id}/analyze", response_model=ProjectAnalysisResponse)
async def analyze_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyse un projet avec l'IA et retourne des suggestions intelligentes.

    L'IA analyse:
    - La description du projet
    - Les tâches existantes
    - Les blocages potentiels

    Et génère:
    - 10-15 suggestions de tâches avec sous-tâches
    - 2-3 suggestions de veille automatique
    - Détection de blocages
    - Top 3 des actions prioritaires
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Analyser le projet
    analyzer = ProjectAnalyzer(db, user_id=current_user.id)
    try:
        analysis = await analyzer.analyze_project(project_id)
    except AnalysisError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    # Convertir en schema de réponse
    return ProjectAnalysisResponse(
        project_id=analysis.project_id,
        analyzed_at=analysis.analyzed_at,
        summary=analysis.summary,
        task_suggestions=[
            TaskSuggestionSchema(**task.dict()) for task in analysis.task_suggestions
        ],
        veille_suggestions=[
            VeilleSuggestionSchema(**veille.dict()) for veille in analysis.veille_suggestions
        ],
        blockers=[
            BlockerSchema(**blocker.dict()) for blocker in analysis.blockers
        ],
        next_actions=analysis.next_actions,
        estimated_total_hours=analysis.estimated_total_hours,
    )


@router.post("/{project_id}/create-suggested-tasks", response_model=CreateTasksResponse)
async def create_suggested_tasks(
    project_id: int,
    request: CreateTasksRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crée des tâches à partir des suggestions d'analyse.

    Le frontend doit d'abord appeler /analyze pour obtenir les suggestions,
    puis appeler cet endpoint avec les indices des tâches à créer.

    Crée également automatiquement les veille_topics suggérés.
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    analyzer = ProjectAnalyzer(db, user_id=current_user.id)

    if request.tasks is not None:
        # Mode normal : le frontend envoie les suggestions issues de /analyze
        selected_suggestions = [
            TaskSuggestion(**t.model_dump()) for t in request.tasks
        ]
        veille_suggestions = request.veille or []
    elif request.task_indices is not None:
        # Fallback déprécié : re-génère l'analyse (lent et non déterministe)
        analysis = await analyzer.analyze_project(project_id)
        if any(idx >= len(analysis.task_suggestions) for idx in request.task_indices):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid task indices"
            )
        selected_suggestions = [
            analysis.task_suggestions[idx] for idx in request.task_indices
        ]
        veille_suggestions = analysis.veille_suggestions
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide 'tasks' (suggestions from /analyze) or 'task_indices'"
        )

    # Créer les tâches
    created_tasks = await analyzer.create_tasks_from_suggestions(
        project_id,
        selected_suggestions
    )

    # Créer les veille_topics automatiquement
    created_veille_count = 0
    for veille_suggestion in veille_suggestions:
        # Vérifier si un topic similaire existe déjà
        existing_query = select(VeilleTopic).where(
            and_(
                VeilleTopic.project_id == project_id,
                VeilleTopic.scope == VeilleScope(veille_suggestion.scope)
            )
        )
        existing_result = await db.execute(existing_query)
        # .first() et non scalar_one_or_none() : des doublons de scope existent
        # en base sur d'anciens projets (MultipleResultsFound → 500)
        existing_topic = existing_result.scalars().first()

        if not existing_topic:
            # Créer le nouveau topic, planifié immédiatement pour le 1er scan
            new_topic = VeilleTopic(
                project_id=project_id,
                name=f"Veille {veille_suggestion.scope}",
                scope=VeilleScope(veille_suggestion.scope),
                description=veille_suggestion.reason,
                keywords=veille_suggestion.keywords,
                scan_frequency=veille_suggestion.scan_frequency,
                enabled=True,
                next_scan=datetime.now(timezone.utc),
            )
            db.add(new_topic)
            created_veille_count += 1

    await db.commit()

    task_ids = [task.id for task in created_tasks]

    return CreateTasksResponse(
        created_count=len(created_tasks),
        task_ids=task_ids,
        message=f"{len(created_tasks)} tâche(s) et {created_veille_count} veille(s) créées avec succès"
    )


@router.get("/{project_id}/visual-references")
async def get_visual_references(
    project_id: int,
    include_dismissed: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Références visuelles (moodboard) collectées par la veille visuelle du projet."""
    from app.models.veille_result import VeilleResult, VeilleResultType, VeilleResultStatus
    from app.schemas.veille_result import VeilleResultResponse

    # Vérifier la propriété du projet
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = (
        select(VeilleResult)
        .join(VeilleTopic, VeilleResult.topic_id == VeilleTopic.id)
        .where(
            VeilleTopic.project_id == project_id,
            VeilleResult.result_type == VeilleResultType.VISUAL_REFERENCE,
        )
        .order_by(VeilleResult.created_at.desc())
    )
    if not include_dismissed:
        query = query.where(VeilleResult.status != VeilleResultStatus.DISMISSED)

    result = await db.execute(query)
    items = [VeilleResultResponse.model_validate(r) for r in result.unique().scalars().all()]
    return {"items": items, "total": len(items)}


@router.post("/refine-task", response_model=RefineTaskResponse)
async def refine_task_suggestion(
    request: RefineTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Raffine une suggestion de tâche avec l'IA.

    L'utilisateur peut demander:
    - Plus de détails dans la description
    - Plus de sous-tâches
    - Changement de priorité ou durée estimée
    - Ajustement du type de tâche

    L'IA génère une version améliorée selon les instructions.
    """
    analyzer = ProjectAnalyzer(db, user_id=current_user.id)

    # Convertir le schema en TaskSuggestion
    task_suggestion = TaskSuggestion(**request.task_data.model_dump())

    # Raffiner la tâche
    refined_task = await analyzer.refine_task_suggestion(
        task_suggestion,
        request.user_prompt
    )

    # Convertir en schema pour la réponse
    refined_schema = TaskSuggestionSchema(**refined_task.model_dump())

    return RefineTaskResponse(refined_task=refined_schema)


@router.post("/start-chat", response_model=StartProjectChatResponse, status_code=status.HTTP_201_CREATED)
async def start_project_chat(
    request: StartProjectChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Démarre un nouveau projet en mode dialogue unifié.

    Au lieu de remplir un formulaire, l'utilisateur dialogue directement avec l'IA
    qui va:
    1. Poser des questions pour comprendre le projet
    2. Extraire automatiquement: titre, description, type, fonctionnalités
    3. Approfondir avec l'idéation socratique
    4. Générer les tâches automatiquement

    Returns:
        - project_id: ID du projet créé
        - conversation_id: ID pour suivre le dialogue
        - welcome_message: Message de bienvenue
        - initial_question: Première question de l'IA
    """
    from app.services.ideation_service import IdeationService

    # Créer un projet minimal en statut IDEATION
    # Le nom sera mis à jour automatiquement une fois extrait du dialogue
    project = Project(
        user_id=current_user.id,
        name="Nouveau projet",  # Nom temporaire
        description=None,
        type="personal",  # Type par défaut, sera mis à jour
        status=ProjectStatus.IDEATION,
        features={"code_gen": True, "veille": False, "git_auto": False}
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Démarrer l'idéation
    ideation_service = IdeationService(db, user_id=current_user.id)
    result = await ideation_service.start_ideation(project.id)

    return StartProjectChatResponse(
        project_id=project.id,
        conversation_id=project.id,  # Pour l'instant, même ID
        welcome_message=result["welcome_message"].content,
        initial_question=result["initial_response"].content
    )


@router.get("/{project_id}/critical-path")
async def get_critical_path(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calcule le chemin critique pour un projet

    Cette fonction :
    1. Récupère toutes les tâches du projet
    2. Calcule l'ordre topologique des tâches
    3. Identifie les tâches critiques (marge nulle)
    4. Retourne les tâches ordonnées avec leurs dates et statut critique

    Returns:
        - ordered_tasks: Liste des tâches avec leurs dates et statut critique
        - critical_tasks: Liste des IDs des tâches critiques
        - total_duration: Durée totale estimée du projet
        - has_cycle: Booléen indiquant si un cycle a été détecté

    Raises:
        HTTPException 400: Si un cycle est détecté dans les dépendances
        HTTPException 404: Si le projet n'existe pas
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Récupérer toutes les tâches du projet (non annulées)
    tasks_query = select(Task).where(
        and_(
            Task.project_id == project_id,
            Task.status != TaskStatus.CANCELLED
        )
    )
    result = await db.execute(tasks_query)
    tasks = result.scalars().all()

    if not tasks:
        return {
            'ordered_tasks': [],
            'critical_tasks': [],
            'total_duration': 0,
            'has_cycle': False
        }

    # Calculer le chemin critique
    critical_path_service = CriticalPathService()

    try:
        critical_path_data = await critical_path_service.calculate_critical_path(tasks, db)

        # Créer un log pour le calcul
        await critical_path_service.create_critical_path_log(
            db=db,
            project_id=project_id,
            user_id=current_user.id,
            critical_path_data=critical_path_data
        )

        return critical_path_data

    except ValueError as e:
        if "Cycle detected" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cycle detected in task dependencies. Cannot calculate critical path."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


# ============================================================================
# Nouveaux endpoints pour le workflow "Finaliser la Vision" avec validation
# ============================================================================

@router.post("/preview-finalization", response_model=ProjectFinalizationPreview, status_code=status.HTTP_200_OK)
async def preview_finalization(
    request: PreviewFinalizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Génère un aperçu de finalisation sans persister en base.

    Cette fonction :
    1. Récupère le projet en status IDEATION
    2. Extrait nom/description via IdeationService.extract_project_info()
    3. Analyse avec ProjectAnalyzer.analyze_project()
    4. Retourne preview avec tâches + mots-clés veille

    ⚠️ Aucune modification en base de données
    """
    from app.services.ideation_service import IdeationService

    # 1. Récupérer le projet
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    if project.status != ProjectStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet doit être en phase IDEATION. Status actuel: {project.status}"
        )

    # 2. Extraire les infos du dialogue
    ideation_service = IdeationService(db, user_id=current_user.id)
    try:
        project_info = await ideation_service.extract_project_info(project.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'extraction des infos: {str(e)}"
        )

    # 3. Analyser et générer les tâches suggérées
    analyzer = ProjectAnalyzer(db, user_id=current_user.id)
    try:
        # Construire le contexte à partir des infos extraites du dialogue
        # (le projet en DB a encore name="Nouveau projet" car non finalisé)
        description = project_info.get("description", project.description or "")
        project_context = {
            "name": project_info.get("name", f"Projet {project.id}"),
            "description": description,
            "existing_tasks": [],  # Pas de tâches existantes en phase IDEATION
            "task_count": 0,
        }

        # Récupérer l'historique d'idéation pour enrichir la génération de tâches
        from app.models.ideation_message import MessageRole
        history = await ideation_service.get_conversation_history(project.id)
        transcript_for_analysis = [
            {"role": msg.role.value, "content": msg.content}
            for msg in history
            if msg.role != MessageRole.SYSTEM
        ]
        ideation_summary = analyzer._summarize_ideation_transcript(transcript_for_analysis)

        analysis_json = await analyzer._generate_analysis(project_context, ideation_context=ideation_summary)
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du projet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

    # 4. Convertir en TaskPreview
    tasks_preview = []
    for task_data in analysis_json.get("tasks", []):
        try:
            tasks_preview.append(
                TaskPreview(
                    title=task_data.get("title", "Tâche sans titre"),
                    description=task_data.get("description", ""),
                    task_type=task_data.get("task_type", "research"),
                    priority=task_data.get("priority", "P2"),
                    estimated_duration=task_data.get("estimated_duration"),
                    llm_prompt=task_data.get("llm_prompt", ""),
                    subtasks=task_data.get("subtasks", [])
                )
            )
        except Exception as e:
            logger.warning(f"Skipping invalid task from LLM: {e}")
            continue

    # 5. Extraire mots-clés pour la veille
    veille_keywords = []
    for veille in analysis_json.get("veille", []):
        if isinstance(veille, dict) and "keywords" in veille:
            veille_keywords.extend(veille["keywords"])

    return ProjectFinalizationPreview(
        suggested_name=project_info.get("name", f"Projet {project.id}"),
        suggested_description=project_info.get("description", description),
        project_type=project_info.get("type", project.type.value),
        tasks=tasks_preview,
        veille_keywords=list(set(veille_keywords))  # Dédupliquer
    )


@router.post("/finalize-with-validation", response_model=FinalizeProjectResponse, status_code=status.HTTP_200_OK)
async def finalize_with_validation(
    request: FinalizeValidationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalise le projet avec validation utilisateur.

    Cette fonction :
    1. Met à jour le projet (nom, description, status=ACTIVE)
    2. Crée uniquement les tâches approuvées (approved=True)
    3. Crée les VeilleTopic si enable_veille=True
    4. Retourne le projet finalisé avec tâches
    """
    from datetime import datetime
    from app.services.ideation_service import IdeationService

    # 1. Récupérer et valider
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    if project.status != ProjectStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le projet doit être en phase IDEATION. Status actuel: {project.status}"
        )

    # 2. Mettre à jour le projet
    project.name = request.project_name
    project.description = request.project_description
    project.status = ProjectStatus.ACTIVE
    project.ideation_completed_at = datetime.now()

    # 3. Sauvegarder le transcript de l'idéation
    ideation_service = IdeationService(db, user_id=current_user.id)
    try:
        history = await ideation_service.get_conversation_history(project.id)
        transcript = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "meta": msg.meta
            }
            for msg in history
        ]
        project.ideation_transcript = transcript
    except Exception as e:
        # Non-bloquant : continuer même si le transcript échoue
        print(f"Warning: Failed to save transcript: {e}")

    # 4. Créer les tâches approuvées
    created_tasks = []
    for task_input in request.tasks:
        if not task_input.approved:
            continue  # Skip les tâches rejetées

        new_task = Task(
            project_id=project.id,
            title=task_input.title,
            description=task_input.description,
            task_type=task_input.task_type,
            priority=task_input.priority,
            status=TaskStatus.CREATED,
            estimated_duration=task_input.estimated_duration,
            llm_prompt=task_input.llm_prompt
        )
        db.add(new_task)
        created_tasks.append(new_task)

    # 5. P1: Créer les VeilleTopic si activé
    if request.enable_veille and request.veille_keywords:
        for keyword in request.veille_keywords:
            veille_topic = VeilleTopic(
                project_id=project.id,
                scope=VeilleScope.TECH,  # Default, peut être affiné
                keywords=[keyword],
                scan_frequency="daily"
            )
            db.add(veille_topic)

    await db.commit()
    await db.refresh(project)

    # Refresh des tâches pour récupérer les IDs
    for task in created_tasks:
        await db.refresh(task)

    # 6. Retourner le résultat
    return FinalizeProjectResponse(
        project_id=project.id,
        project_name=project.name,
        project_description=project.description or "",
        tasks_count=len(created_tasks),
        tasks=[
            TaskGenerated(
                id=task.id,
                title=task.title,
                description=task.description or "",
                task_type=task.task_type.value,
                priority=task.priority.value,
                estimated_duration=task.estimated_duration
            )
            for task in created_tasks
        ],
        message=f"Projet '{project.name}' finalisé avec {len(created_tasks)} tâches créées !"
    )


@router.post("/finalize", response_model=FinalizeProjectResponse, status_code=status.HTTP_200_OK)
async def finalize_project(
    request: FinalizeProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalise un projet en mode dialogue unifié.

    Cette fonction :
    1. Extrait les informations du projet depuis le dialogue (nom, description, type, features)
    2. Met à jour le projet avec ces informations
    3. Appelle ProjectAnalyzer pour générer les tâches
    4. Crée les tâches en base de données
    5. Marque l'idéation comme terminée (status → ACTIVE)
    """
    from app.services.ideation_service import IdeationService

    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            and_(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    if project.status not in [ProjectStatus.IDEATION, ProjectStatus.PLANNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in IDEATION or PLANNING status to be finalized. Current status: {project.status}"
        )

    # 1. Extraire les infos du projet depuis le dialogue
    ideation_service = IdeationService(db, user_id=current_user.id)
    try:
        extracted_info = await ideation_service.extract_project_info(project.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract project info: {str(e)}"
        )

    # 2. Mettre à jour le projet avec les infos extraites
    project.name = extracted_info.get("name", project.name)
    project.description = extracted_info.get("description", project.description)
    project.type = extracted_info.get("type", project.type)

    # Mettre à jour les features
    if "features" in extracted_info:
        project.features = extracted_info["features"]

    await db.commit()
    await db.refresh(project)

    # 3. Analyser le projet et générer les tâches
    analyzer = ProjectAnalyzer(db, user_id=current_user.id)
    try:
        analysis = await analyzer.analyze_project(project.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze project: {str(e)}"
        )

    # 4. Créer les tâches en BDD
    try:
        tasks = await analyzer.create_tasks_from_suggestions(
            project.id,
            analysis.task_suggestions
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tasks: {str(e)}"
        )

    # 5. Marquer l'idéation comme terminée et passer directement en ACTIVE
    # (au lieu de PLANNING comme le fait complete_ideation normalement)
    history = await ideation_service.get_conversation_history(project.id)

    # Convertir en format JSON sérialisable
    from datetime import datetime
    transcript = [
        {
            "role": msg.role.value,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "meta": msg.meta
        }
        for msg in history
    ]

    # Mettre à jour le projet directement en ACTIVE (pas PLANNING)
    project.status = ProjectStatus.ACTIVE
    project.ideation_transcript = transcript
    project.ideation_completed_at = datetime.now()

    await db.commit()
    await db.refresh(project)

    # Construire la réponse
    return FinalizeProjectResponse(
        project_id=project.id,
        project_name=project.name,
        project_description=project.description or "",
        tasks_count=len(tasks),
        tasks=[
            TaskGenerated(
                id=task.id,
                title=task.title,
                description=task.description or "",
                task_type=task.task_type.value,
                priority=task.priority.value,
                estimated_duration=task.estimated_duration
            )
            for task in tasks
        ],
        message=f"Projet '{project.name}' finalisé avec succès ! {len(tasks)} tâches générées."
    )

@router.get("/{project_id}/maturity-analysis")
async def get_maturity_analysis(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyse la maturité d'un projet et retourne des conseils d'amélioration

    Cette fonction :
    1. Calcule le score de maturité actuel
    2. Analyse les critères de maturité (dépendances, descriptions, deadlines, chemin critique)
    3. Génère des conseils personnalisés pour améliorer le score

    Returns:
        - maturity_score: Score de maturité actuel (0-100)
        - criteria_analysis: Analyse détaillée par critère
        - improvement_suggestions: Conseils personnalisés pour améliorer le score
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    query = select(Project).where(
        and_(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Calculer le score de maturité
    maturity_service = MaturityService()
    maturity_score = await maturity_service.calculate_maturity_score(project, db)

    # Analyser les critères de maturité
    criteria_analysis = await maturity_service.analyze_maturity_criteria(project, db)

    # Générer des conseils d'amélioration
    improvement_suggestions = await maturity_service.generate_improvement_suggestions(project, db)

    return {
        'maturity_score': maturity_score,
        'criteria_analysis': criteria_analysis,
        'improvement_suggestions': improvement_suggestions
    }
