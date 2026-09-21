"""
API endpoints for Tasks
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session_maker
from app.api.deps import get_current_user
from app.models import User, Project, Task, TaskType, TaskPriority, TaskStatus
from app.models.project import ProjectStatus
from app.schemas.task_log import TaskLogResponse
from app.models.task_log import TaskLog, TaskEventType
from app.models.task import task_dependencies
from sqlalchemy import insert, delete
from app.services.task_progress import get_progress
from app.services.maturity import MaturityService
from app.schemas import (
    TaskCreate, TaskUpdate, TaskValidate, TaskResponse, TaskList,
    VeilleResultResponse, VeilleResultList, VeilleRefineRequest, VeilleResultUpdate
)
from app.models.veille_result import VeilleResult, VeilleResultStatus
from app.models.veille_topic import VeilleTopic

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_user_task_model(
    task_id: int,
    user_id: int,
    db: AsyncSession
) -> Task:
    """Helper pour récupérer le modèle Task avec vérification permissions (pour modifications)"""
    query = select(Task).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == user_id
        )
    )
    result = await db.execute(query)
    task = result.unique().scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


async def _get_user_task(
    task_id: int,
    user_id: int,
    db: AsyncSession
) -> TaskResponse:
    """Helper pour récupérer une tâche avec vérification permissions + nom projet + dépendances (pour lecture)"""
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == user_id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    # Récupérer les dépendances
    deps_query = select(task_dependencies.c.depends_on_id).where(
        task_dependencies.c.task_id == task_id
    )
    deps_result = await db.execute(deps_query)
    dependencies = [dep_id for (dep_id,) in deps_result.all()]

    # Convertir le dictionnaire et ajouter les dépendances
    task_dict = task.__dict__.copy()
    task_dict['project_name'] = project_name
    task_dict['dependencies'] = dependencies
    # Avancement d'une tâche en cours : le frontend interroge déjà cet endpoint
    # en boucle, inutile d'en ajouter un second.
    task_dict['progress'] = get_progress(task_id)

    return TaskResponse(**task_dict)


async def _create_task_log(
    db: AsyncSession,
    task_id: int,
    event_type: TaskEventType,
    user_id: Optional[int] = None,
    details: Optional[dict] = None
):
    """Helper pour créer un log de tâche"""
    log = TaskLog(
        task_id=task_id,
        event_type=event_type,
        user_id=user_id,
        details=details or {}
    )
    db.add(log)

async def _validate_dependencies(
    task_id: int,
    dependency_ids: list[int],
    user_id: int,
    db: AsyncSession
) -> None:
    """
    Valide les dépendances pour éviter les boucles et vérifier l'existence

    Args:
        task_id: ID de la tâche actuelle
        dependency_ids: Liste des IDs des tâches dépendantes
        user_id: ID de l'utilisateur (pour vérification permissions)
        db: Session de base de données

    Raises:
        HTTPException: Si validation échoue
    """
    # Vérification 1: Une tâche ne peut pas dépendre d'elle-même
    if task_id in dependency_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on itself"
        )

    # Vérification 2: Toutes les tâches dépendantes doivent exister et appartenir à l'utilisateur
    if dependency_ids:
        query = select(Task.id).join(Project).where(
            and_(
                Task.id.in_(dependency_ids),
                Project.user_id == user_id
            )
        )
        result = await db.execute(query)
        existing_deps = result.unique().scalars().all()

        missing_deps = set(dependency_ids) - set(existing_deps)
        if missing_deps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dependency tasks not found: {sorted(missing_deps)}"
            )

async def _update_task_dependencies(
    task_id: int,
    dependency_ids: list[int],
    db: AsyncSession
) -> None:
    """
    Met à jour les dépendances d'une tâche dans la table task_dependencies

    Args:
        task_id: ID de la tâche
        dependency_ids: Liste des IDs des tâches dépendantes
        db: Session de base de données
    """
    # Supprimer les dépendances existantes
    await db.execute(
        delete(task_dependencies)
        .where(task_dependencies.c.task_id == task_id)
    )

    # Ajouter les nouvelles dépendances
    if dependency_ids:
        await db.execute(
            insert(task_dependencies),
            [{"task_id": task_id, "depends_on_id": dep_id} for dep_id in dependency_ids]
        )


@router.get("/", response_model=TaskList)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Liste toutes les tâches de l'utilisateur avec pagination

    Filtres disponibles:
    - project_id: ID du projet
    - status: created, ready, generating, etc.
    - priority: P1, P2, P3

    Par défaut, exclut les tâches annulées et les projets archivés
    """
    # Requête de base avec join sur projects pour vérifier permissions
    # et exclure les projets archivés
    # Récupérer Task ET le nom du projet
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Project.user_id == current_user.id,
            Project.status != ProjectStatus.ARCHIVED
        )
    )

    # Filtres
    if project_id:
        query = query.where(Task.project_id == project_id)
    if status:
        query = query.where(Task.status == status)
    else:
        # Par défaut, exclure les tâches annulées
        query = query.where(Task.status != TaskStatus.CANCELLED)
    if priority:
        query = query.where(Task.priority == priority)

    # Tri: priorité puis date de création décroissante
    query = query.order_by(Task.priority.asc(), Task.created_at.desc())

    # Count total
    count_query = select(func.count(Task.id)).select_from(Task).join(Project).where(
        and_(
            Project.user_id == current_user.id,
            Project.status != ProjectStatus.ARCHIVED
        )
    )
    if project_id:
        count_query = count_query.where(Task.project_id == project_id)
    if status:
        count_query = count_query.where(Task.status == status)
    else:
        count_query = count_query.where(Task.status != TaskStatus.CANCELLED)
    if priority:
        count_query = count_query.where(Task.priority == priority)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.unique().all()

    # Construire les TaskResponse avec project_name
    tasks = []
    for task, project_name in rows:
        task_dict = {
            **task.__dict__,
            'project_name': project_name
        }
        tasks.append(TaskResponse(**task_dict))

    return TaskList(
        items=tasks,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Créer une nouvelle tâche
    
    Si llm_prompt fourni, status = READY
    Sinon, status = CREATED
    """
    # Vérifier que le projet existe et appartient à l'user
    query = select(Project).where(
        and_(
            Project.id == task_in.project_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    project = result.unique().scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Déterminer status initial
    # Les tâches non-code (veille, admin, research, funding, document) n'ont pas besoin de llm_prompt
    # pour être traitées — le handler génère le contexte. On les met directement en READY.
    non_code_types = [
        TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS,
        TaskType.ADMINISTRATIVE, TaskType.RESEARCH, TaskType.FUNDING_SEARCH,
        TaskType.DOCUMENT_WRITING,
    ]
    if task_in.llm_prompt or task_in.task_type in non_code_types:
        initial_status = TaskStatus.READY
    else:
        initial_status = TaskStatus.CREATED
    
    # Créer la tâche
    task = Task(
        project_id=task_in.project_id,
        title=task_in.title,
        description=task_in.description,
        task_type=task_in.task_type,
        priority=task_in.priority,
        status=initial_status,
        llm_prompt=task_in.llm_prompt,
        estimated_duration=task_in.estimated_duration,
        due_date=task_in.due_date,
        task_metadata=task_in.metadata or {}
    )
    
    db.add(task)
    await db.flush()  # Pour obtenir l'ID

    # Si c'est une tâche VEILLE, créer un VeilleTopic lié pour la récurrence
    if task_in.task_type == TaskType.VEILLE:
        metadata = task_in.metadata or {}
        frequency = metadata.get('frequency', 'weekly')
        veille_keywords = metadata.get('keywords', [])

        from app.models.veille_topic import VeilleTopic, VeilleScope
        # Scope choisi par l'utilisateur (visual, tech, funding...) — défaut news
        try:
            scope = VeilleScope(metadata.get('scope', 'news'))
        except ValueError:
            scope = VeilleScope.NEWS

        veille_topic = VeilleTopic(
            project_id=task_in.project_id,
            name=task_in.title,
            scope=scope,
            description=task_in.description,
            keywords=veille_keywords,
            excluded_keywords=metadata.get('excluded_keywords', []),
            scan_frequency=frequency,
            enabled=True,
        )
        # 'once' = one-shot : pas de récurrence planifiée. Sinon, planifier
        # le prochain scan — sans next_scan le job de récurrence ignore le topic.
        if frequency != 'once':
            veille_topic.next_scan = veille_topic.calculate_next_scan()
        db.add(veille_topic)
        await db.flush()
        task.veille_topic_id = veille_topic.id

    # Créer log
    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.CREATED,
        user_id=current_user.id,
        details={
            "initial_status": initial_status.value,
            "priority": task_in.priority.value
        }
    )

    # Gérer les dépendances si fournies
    if task_in.dependency_ids:
        await _validate_dependencies(task.id, task_in.dependency_ids, current_user.id, db)
        await _update_task_dependencies(task.id, task_in.dependency_ids, db)

    await db.commit()
    await db.refresh(task)

    # Mettre à jour le score de maturité du projet
    maturity_service = MaturityService()
    await maturity_service.update_project_maturity_score(task.project_id, db)

    # Récupérer le nom du projet pour la réponse
    result = await db.execute(select(Project.name).where(Project.id == task.project_id))
    project_name = result.scalar()

    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.get("/veille-deadlines")
async def get_upcoming_deadlines(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Prochaines échéances (appels à projets) toutes veilles confondues."""
    from datetime import datetime, timezone
    query = (
        select(VeilleResult)
        .join(VeilleTopic, VeilleResult.topic_id == VeilleTopic.id)
        .join(Project, VeilleTopic.project_id == Project.id)
        .where(
            Project.user_id == current_user.id,
            VeilleResult.deadline != None,  # noqa: E711
            VeilleResult.deadline >= datetime.now(timezone.utc),
            VeilleResult.status != VeilleResultStatus.DISMISSED,
        )
        .order_by(VeilleResult.deadline.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    items = [VeilleResultResponse.model_validate(r) for r in result.unique().scalars().all()]
    return {"items": items, "total": len(items)}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Récupérer les détails d'une tâche"""
    task = await _get_user_task(task_id, current_user.id, db)
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Modifier une tâche

    Si status changé, un log est créé automatiquement
    """
    task = await _get_user_task_model(task_id, current_user.id, db)
    
    # Sauvegarder ancien status
    old_status = task.status
    
    # Mettre à jour les champs fournis
    update_data = task_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        # Mapper metadata -> task_metadata
        if field == 'metadata':
            setattr(task, 'task_metadata', value)
        else:
            setattr(task, field, value)
    
    # Si status a changé, créer un log
    if 'status' in update_data and update_data['status'] != old_status:
        await _create_task_log(
            db=db,
            task_id=task.id,
            event_type=TaskEventType.STATUS_CHANGED,
            user_id=current_user.id,
            details={
                "old_status": old_status.value,
                "new_status": update_data['status'].value
            }
        )

    # Gérer les dépendances si fournies
    if 'dependency_ids' in update_data:
        await _validate_dependencies(task.id, update_data['dependency_ids'], current_user.id, db)
        await _update_task_dependencies(task.id, update_data['dependency_ids'], db)

    await db.commit()
    await db.refresh(task)

    # Mettre à jour le score de maturité du projet
    maturity_service = MaturityService()
    await maturity_service.update_project_maturity_score(task.project_id, db)

    # Récupérer le nom du projet pour le retour
    project_query = select(Project.name).where(Project.id == task.project_id)
    project_result = await db.execute(project_query)
    project_name = project_result.scalar_one()

    task_dict = {**task.__dict__, 'project_name': project_name}
    return TaskResponse(**task_dict)


async def _generate_code_background(task_id: int):
    """
    Fonction de génération de code en arrière-plan

    Exécutée de façon asynchrone pour ne pas bloquer la réponse HTTP
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🚀 Starting background generation for task {task_id}")
    print(f"🚀 Starting background generation for task {task_id}")  # Debug

    from app.services.unified_orchestrator import UnifiedOrchestrator

    # Créer une nouvelle session DB pour cette tâche background
    async with async_session_maker() as db:
        try:
            # Récupérer la tâche
            query = select(Task).where(Task.id == task_id)
            result = await db.execute(query)
            task = result.unique().scalar_one_or_none()

            if not task:
                logger.error(f"❌ Task {task_id} not found for background generation")
                return

            logger.info(f"📝 Task {task_id} ({task.task_type.value}) — routing via UnifiedOrchestrator")

            # UnifiedOrchestrator dispatche selon task_type (code, texte, veille, etc.)
            orchestrator = UnifiedOrchestrator(db)
            await orchestrator.handle_task(task)

            # Commit pour sauvegarder le résultat
            await db.commit()

            logger.info(f"✅ Background generation completed for task {task_id}")

        except Exception as e:
            logger.error(f"❌ Error in background generation for task {task_id}: {e}", exc_info=True)
            print(f"❌ Error in background generation for task {task_id}: {e}")
            # Mettre la tâche en erreur
            try:
                from app.services.task_progress import clear_progress
                clear_progress(task_id)
                task.status = TaskStatus.READY
                task.started_at = None
                await db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to rollback task status: {commit_error}")


@router.post("/{task_id}/generate", response_model=TaskResponse)
async def generate_task_code(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Déclencher la génération de code pour une tâche manuellement

    La tâche doit être en status READY.
    La génération se fait en arrière-plan pour ne pas bloquer l'interface.
    """
    # Récupérer la tâche avec vérification permissions
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    # Types de tâches pouvant être re-lancés depuis n'importe quel état non-actif
    RELAUNCHABLE_TYPES = {
        TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS,
        TaskType.RESEARCH, TaskType.ADMINISTRATIVE,
    }

    allowed_statuses = {TaskStatus.CREATED, TaskStatus.READY}
    if task.task_type in RELAUNCHABLE_TYPES:
        # Pour les veilles et tâches autonomes, on accepte aussi COMPLETED/FAILED/CANCELLED
        allowed_statuses |= {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    if task.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task cannot be (re)launched from status: {task.status.value}"
        )

    # Réinitialiser les champs si re-lancement depuis COMPLETED/FAILED/CANCELLED
    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        task.radar_report = None
        task.generated_code = None
        task.completed_at = None
        task.retry_count = 0
        task.last_failed_at = None
        task.validation_notes = None

    # Créer log de début
    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.CODE_GENERATION_STARTED,
        user_id=current_user.id,
        details={"manual_trigger": True, "from_status": task.status.value}
    )

    # Passer la tâche en status GENERATING immédiatement
    task.status = TaskStatus.GENERATING
    task.started_at = datetime.now(timezone.utc)

    # Commit pour que le changement de status soit visible immédiatement
    await db.commit()
    await db.refresh(task)

    # Lancer la génération en arrière-plan avec asyncio.create_task()
    # Ceci permet de lancer la tâche async en parallèle sans bloquer la réponse
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"🎯 Creating background task for task {task_id}")
    print(f"🎯 Creating background task for task {task_id}")  # Debug

    bg_task = asyncio.create_task(_generate_code_background(task_id))
    # Ajouter un callback pour logger les erreurs non attrapées
    bg_task.add_done_callback(lambda t: logger.error(f"Background task error: {t.exception()}") if t.exception() else None)

    # Retourner la tâche avec le nom du projet (status = GENERATING)
    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.post("/{task_id}/validate", response_model=TaskResponse)
async def validate_task(
    task_id: int,
    validation: TaskValidate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Valider ou rejeter le code généré

    - Si approved=True: status → COMPLETED
    - Si approved=False: status → READY (pour régénération)
    """
    # Récupérer la tâche avec vérification permissions
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    # Vérifier que la tâche est en attente de validation
    if task.status != TaskStatus.MANUAL_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task must be in MANUAL_REVIEW status (current: {task.status.value})"
        )

    if validation.approved:
        # Code validé → terminé
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.validation_notes = validation.notes

        # Si l'utilisateur a édité le code inline, sauvegarder la version modifiée
        if validation.edited_code is not None:
            task.generated_code = validation.edited_code

        # Calculer durée réelle
        if task.started_at:
            duration = (task.completed_at - task.started_at).total_seconds()
            task.actual_duration = int(duration)

        await _create_task_log(
            db=db,
            task_id=task.id,
            event_type=TaskEventType.VALIDATED,
            user_id=current_user.id,
            details={"notes": validation.notes}
        )

        # Si c'est une tâche veille avec un topic lié, programmer la prochaine occurrence
        if task.veille_topic_id and task.task_type in [
            TaskType.VEILLE, TaskType.VEILLE_TECH, TaskType.VEILLE_CULTURAL, TaskType.VEILLE_EVENTS
        ]:
            from app.models.veille_topic import VeilleTopic
            topic_query = select(VeilleTopic).where(VeilleTopic.id == task.veille_topic_id)
            topic_result = await db.execute(topic_query)
            veille_topic = topic_result.scalar_one_or_none()
            if veille_topic and veille_topic.enabled:
                from datetime import datetime as dt_module
                veille_topic.last_scan = dt_module.utcnow()
                veille_topic.next_scan = veille_topic.calculate_next_scan()
                logger.info(
                    f"📅 Veille topic {veille_topic.id} next scan scheduled: "
                    f"{veille_topic.next_scan} (frequency: {veille_topic.scan_frequency})"
                )

    else:
        # Code rejeté → retour en READY pour régénération
        task.status = TaskStatus.READY
        task.validation_notes = validation.notes
        task.generated_code = None  # Nettoyer le code rejeté

        await _create_task_log(
            db=db,
            task_id=task.id,
            event_type=TaskEventType.REJECTED,
            user_id=current_user.id,
            details={"notes": validation.notes}
        )

    await db.commit()
    await db.refresh(task)

    # Retourner la tâche avec le nom du projet
    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.post("/{task_id}/reject", response_model=TaskResponse)
async def reject_task(
    task_id: int,
    rejection: TaskValidate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Rejeter le code généré et demander une régénération

    Remet la tâche en status READY avec les notes de feedback
    """
    # Récupérer la tâche avec vérification permissions
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    # Vérifier que la tâche est en attente de validation
    if task.status != TaskStatus.MANUAL_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task must be in MANUAL_REVIEW status (current: {task.status.value})"
        )

    # Code rejeté → retour en READY pour régénération
    task.status = TaskStatus.READY
    task.validation_notes = rejection.notes
    task.generated_code = None  # Nettoyer le code rejeté
    task.started_at = None

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.REJECTED,
        user_id=current_user.id,
        details={"notes": rejection.notes}
    )

    await db.commit()
    await db.refresh(task)

    # Retourner la tâche avec le nom du projet
    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.post("/{task_id}/activate", response_model=TaskResponse)
async def activate_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Activer une tâche (CREATED → READY)

    Permet de mettre la tâche dans la file d'attente du scheduler
    sans déclencher immédiatement la génération.
    """
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(Task.id == task_id, Project.user_id == current_user.id)
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task, project_name = row

    if task.status != TaskStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only CREATED tasks can be activated (current: {task.status.value})"
        )

    task.status = TaskStatus.READY

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.STATUS_CHANGED,
        user_id=current_user.id,
        details={"action": "activate", "old_status": "CREATED", "new_status": "READY"}
    )

    await db.commit()
    await db.refresh(task)

    task_dict = {**task.__dict__, 'project_name': project_name}
    return TaskResponse(**task_dict)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marquer manuellement une tâche comme terminée (COMPLETED)

    Utile pour les tâches faites en dehors de l'orchestrateur (ex: admin,
    recherche manuelle, etc.). Possible depuis n'importe quel statut sauf
    COMPLETED ou CANCELLED.
    """
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(Task.id == task_id, Project.user_id == current_user.id)
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task, project_name = row

    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete a task in status {task.status.value}"
        )

    old_status = task.status
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)

    if task.started_at:
        duration = (task.completed_at - task.started_at).total_seconds()
        task.actual_duration = int(duration)

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.VALIDATED,
        user_id=current_user.id,
        details={"action": "manual_complete", "previous_status": old_status.value}
    )

    await db.commit()
    await db.refresh(task)

    # Mettre à jour le score de maturité du projet
    maturity_service = MaturityService()
    await maturity_service.update_project_maturity_score(task.project_id, db)

    task_dict = {**task.__dict__, 'project_name': project_name}
    return TaskResponse(**task_dict)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Annuler une tâche

    Peut être fait depuis n'importe quel status sauf COMPLETED
    """
    # Récupérer la tâche avec vérification permissions
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed task"
        )

    old_status = task.status
    task.status = TaskStatus.CANCELLED

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.CANCELLED,
        user_id=current_user.id,
        details={"previous_status": old_status.value}
    )

    await db.commit()
    await db.refresh(task)

    # Retourner la tâche avec le nom du projet
    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Relancer une tâche FAILED ou CANCELLED → READY
    """
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only FAILED or CANCELLED tasks can be retried (current: {task.status.value})"
        )

    old_status = task.status
    task.status = TaskStatus.READY

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.STATUS_CHANGED,
        user_id=current_user.id,
        details={"action": "retry", "previous_status": old_status.value}
    )

    await db.commit()
    await db.refresh(task)

    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.post("/{task_id}/stop", response_model=TaskResponse)
async def stop_generation(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Arrêter une génération en cours

    Remet la tâche en status READY si elle est en GENERATING
    """
    # Récupérer la tâche avec vérification permissions
    query = select(Task, Project.name.label('project_name')).join(Project).where(
        and_(
            Task.id == task_id,
            Project.user_id == current_user.id
        )
    )
    result = await db.execute(query)
    row = result.unique().one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task, project_name = row

    # Vérifier que la tâche est en GENERATING
    if task.status != TaskStatus.GENERATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only stop tasks in GENERATING status (current: {task.status.value})"
        )

    # Remettre en READY
    task.status = TaskStatus.READY
    task.started_at = None
    task.generated_code = None

    await _create_task_log(
        db=db,
        task_id=task.id,
        event_type=TaskEventType.STATUS_CHANGED,
        user_id=current_user.id,
        details={"old_status": "GENERATING", "new_status": "READY", "reason": "Generation stopped by user"}
    )

    await db.commit()
    await db.refresh(task)

    # Retourner la tâche avec le nom du projet
    task_dict = {
        **task.__dict__,
        'project_name': project_name
    }
    return TaskResponse(**task_dict)


@router.get("/{task_id}/veille-results", response_model=VeilleResultList)
async def get_task_veille_results(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer les résultats de veille associés à une tâche

    Cherche d'abord par task_id direct, puis en fallback par topic_id
    lié au même projet (pour les résultats créés avant l'ajout du task_id).
    Triés par score de pertinence décroissant.
    """
    # Vérifier que la tâche existe et appartient à l'user
    task_resp = await _get_user_task(task_id, current_user.id, db)

    # 1. Chercher par task_id direct
    query = (
        select(VeilleResult)
        .where(VeilleResult.task_id == task_id)
        .order_by(VeilleResult.relevance_score.desc())
    )
    result = await db.execute(query)
    veille_results = list(result.unique().scalars().all())

    # 2. Fallback: si aucun résultat avec task_id, chercher via topic_id du même projet
    if not veille_results:
        fallback_query = (
            select(VeilleResult)
            .join(VeilleTopic, VeilleResult.topic_id == VeilleTopic.id)
            .where(VeilleTopic.project_id == task_resp.project_id)
            .order_by(VeilleResult.relevance_score.desc())
        )
        result = await db.execute(fallback_query)
        veille_results = list(result.unique().scalars().all())

    items = [VeilleResultResponse.model_validate(vr) for vr in veille_results]

    return VeilleResultList(
        items=items,
        total=len(items),
        task_id=task_id
    )


@router.put("/veille-results/{result_id}", response_model=VeilleResultResponse)
async def update_veille_result(
    result_id: int,
    update: VeilleResultUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Met à jour le statut utilisateur d'un résultat de veille (épingler, écarter, noter)."""
    query = (
        select(VeilleResult)
        .join(VeilleTopic, VeilleResult.topic_id == VeilleTopic.id)
        .join(Project, VeilleTopic.project_id == Project.id)
        .where(VeilleResult.id == result_id, Project.user_id == current_user.id)
    )
    result = await db.execute(query)
    veille_result = result.unique().scalar_one_or_none()

    if not veille_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Veille result {result_id} not found"
        )

    if update.status is not None:
        veille_result.status = update.status
    if update.user_notes is not None:
        veille_result.user_notes = update.user_notes
    if update.user_rating is not None:
        veille_result.user_rating = update.user_rating

    await db.commit()
    await db.refresh(veille_result)
    return VeilleResultResponse.model_validate(veille_result)


@router.post("/{task_id}/veille-rescan")
async def rescan_veille(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Relance immédiatement la veille du topic lié : crée une nouvelle
    occurrence READY (traitée par le scheduler sous ~2 min)."""
    task_resp = await _get_user_task(task_id, current_user.id, db)

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one()
    if not task.veille_topic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette tâche n'est pas liée à un topic de veille"
        )

    topic_result = await db.execute(
        select(VeilleTopic).where(VeilleTopic.id == task.veille_topic_id)
    )
    topic = topic_result.scalar_one()

    # Éviter les doublons si une occurrence est déjà en cours
    active = await db.execute(
        select(Task).where(
            Task.veille_topic_id == topic.id,
            Task.status.in_([TaskStatus.READY, TaskStatus.GENERATING]),
        )
    )
    existing = active.scalars().first()
    if existing:
        return {"status": "already_running", "task_id": existing.id}

    new_task = Task(
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        task_type=TaskType.VEILLE,
        status=TaskStatus.READY,
        veille_topic_id=topic.id,
        task_metadata={
            'keywords': topic.keywords or [],
            'frequency': topic.scan_frequency,
            'manual_rescan': True,
        }
    )
    db.add(new_task)
    topic.last_scan = datetime.now(timezone.utc)
    topic.next_scan = topic.calculate_next_scan()
    await db.commit()
    await db.refresh(new_task)

    logger.info(f"🔄 Veille rescan: nouvelle tâche {new_task.id} pour topic {topic.id}")
    return {"status": "created", "task_id": new_task.id}


@router.put("/{task_id}/veille-refine")
async def refine_veille(
    task_id: int,
    refinement: VeilleRefineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Affiner les paramètres de veille pour les prochaines occurrences.

    Met à jour le VeilleTopic lié : ajoute/supprime des keywords,
    gère les exclusions, et enregistre l'historique d'affinage.
    """
    # Vérifier que la tâche existe et appartient à l'user
    task_resp = await _get_user_task(task_id, current_user.id, db)

    # Récupérer la tâche complète
    task_query = select(Task).where(Task.id == task_id)
    task_result = await db.execute(task_query)
    task = task_result.scalar_one_or_none()

    if not task or not task.veille_topic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This task is not linked to a veille topic"
        )

    # Récupérer le VeilleTopic
    topic_query = select(VeilleTopic).where(VeilleTopic.id == task.veille_topic_id)
    topic_result = await db.execute(topic_query)
    topic = topic_result.scalar_one_or_none()

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veille topic not found"
        )

    # Appliquer les modifications
    current_keywords = list(topic.keywords or [])
    current_excluded = list(topic.excluded_keywords or [])

    # Ajouter les nouveaux keywords
    for kw in refinement.add_keywords:
        if kw not in current_keywords:
            current_keywords.append(kw)

    # Retirer les keywords supprimés
    for kw in refinement.remove_keywords:
        if kw in current_keywords:
            current_keywords.remove(kw)

    # Ajouter les exclusions
    for kw in refinement.add_excluded:
        if kw not in current_excluded:
            current_excluded.append(kw)

    # Retirer les exclusions
    for kw in refinement.remove_excluded:
        if kw in current_excluded:
            current_excluded.remove(kw)

    topic.keywords = current_keywords
    topic.excluded_keywords = current_excluded

    # Enregistrer dans l'historique d'affinage
    history = list(topic.refinement_history or [])
    history.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "add_keywords": refinement.add_keywords,
        "remove_keywords": refinement.remove_keywords,
        "add_excluded": refinement.add_excluded,
        "remove_excluded": refinement.remove_excluded,
        "user_notes": refinement.user_notes,
    })
    topic.refinement_history = history

    await db.commit()

    logger.info(f"🔧 Veille topic {topic.id} refined: keywords={current_keywords}, excluded={current_excluded}")

    return {
        "status": "ok",
        "topic_id": topic.id,
        "keywords": current_keywords,
        "excluded_keywords": current_excluded,
        "refinement_count": len(history),
    }


@router.get("/{task_id}/logs", response_model=List[TaskLogResponse])
async def get_task_logs(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupérer l'historique complet d'une tâche

    Retourne tous les événements dans l'ordre chronologique
    """
    # Vérifier que la tâche existe et appartient à l'user
    task = await _get_user_task(task_id, current_user.id, db)

    # Récupérer tous les logs
    query = select(TaskLog).where(TaskLog.task_id == task_id).order_by(TaskLog.timestamp.asc())
    result = await db.execute(query)
    logs = result.unique().scalars().all()

    return logs


@router.get("/stats/service")
async def get_service_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Statistiques globales du service pour l'utilisateur

    Retourne le nombre de tâches par status pour voir l'activité en cours
    """
    # Compter les tâches par status pour cet utilisateur
    stats_query = (
        select(
            Task.status,
            func.count(Task.id).label('count')
        )
        .join(Project)
        .where(Project.user_id == current_user.id)
        .group_by(Task.status)
    )

    result = await db.execute(stats_query)
    stats_rows = result.all()

    # Construire le dictionnaire de stats
    stats = {
        'ready': 0,
        'generating': 0,
        'manual_review': 0,
        'completed': 0,
        'cancelled': 0
    }

    for status_val, count in stats_rows:
        stats[status_val.value.lower()] = count

    return stats


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprimer une tâche

    Supprime définitivement une tâche et tous ses logs associés
    """
    task = await _get_user_task_model(task_id, current_user.id, db)

    # Stocker le project_id avant la suppression
    project_id = task.project_id

    await db.delete(task)
    await db.commit()

    # Mettre à jour le score de maturité du projet après suppression
    maturity_service = MaturityService()
    await maturity_service.update_project_maturity_score(project_id, db)

    return None
