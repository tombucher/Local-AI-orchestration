"""
Tests pour le service Orchestrator
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.orchestrator import TaskOrchestrator
from app.services.llm_client import OllamaClient
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.task_log import TaskLog, TaskEventType
from app.models.project import Project, ProjectType, ProjectStatus
from app.models.user import User


@pytest.fixture
async def test_user(db_session):
    """Crée un utilisateur de test"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_project(db_session, test_user):
    """Crée un projet de test"""
    project = Project(
        user_id=test_user.id,
        name="Test Project",
        type=ProjectType.PERSONAL,
        status=ProjectStatus.ACTIVE,
        features={"code_gen": True}
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_handle_task_success(db_session, test_project):
    """Test génération de code réussie"""
    # Mock Ollama client
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate_code = AsyncMock(return_value="def hello() -> str:\n    return 'Hello World'")

    # Créer une tâche READY
    task = Task(
        project_id=test_project.id,
        title="Generate hello function",
        description="Create a simple hello world function",
        status=TaskStatus.READY,
        priority=TaskPriority.P1,
        llm_prompt="Create a Python function that returns 'Hello World'"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Orchestrator
    orchestrator = TaskOrchestrator(db_session, mock_client)
    await orchestrator.handle_task(task)
    await db_session.commit()

    # Vérifications
    await db_session.refresh(task)
    assert task.status == TaskStatus.MANUAL_REVIEW
    assert task.generated_code == "def hello() -> str:\n    return 'Hello World'"
    assert task.started_at is not None

    # Vérifier que des logs ont été créés
    from sqlalchemy import select
    stmt = select(TaskLog).filter(TaskLog.task_id == task.id)
    result = await db_session.execute(stmt)
    logs = result.scalars().all()

    assert len(logs) == 2  # generation_started + code_generated
    assert logs[0].event_type == TaskEventType.CODE_GENERATION_STARTED
    assert logs[1].event_type == TaskEventType.CODE_GENERATED


@pytest.mark.asyncio
async def test_handle_task_failure(db_session, test_project):
    """Test échec de génération"""
    # Mock Ollama client qui échoue
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate_code = AsyncMock(side_effect=Exception("Ollama connection error"))

    task = Task(
        project_id=test_project.id,
        title="Test task",
        status=TaskStatus.READY,
        priority=TaskPriority.P1,
        llm_prompt="Generate something"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    orchestrator = TaskOrchestrator(db_session, mock_client)

    # Doit lever une exception
    with pytest.raises(Exception) as exc_info:
        await orchestrator.handle_task(task)

    assert "Ollama connection error" in str(exc_info.value)

    # Handle failure
    await orchestrator.handle_failure(task, exc_info.value)
    await db_session.commit()

    # Vérifications
    await db_session.refresh(task)
    assert task.status == TaskStatus.FAILED

    # Vérifier le log d'erreur
    from sqlalchemy import select
    stmt = select(TaskLog).filter(
        TaskLog.task_id == task.id,
        TaskLog.event_type == TaskEventType.GENERATION_FAILED
    )
    result = await db_session.execute(stmt)
    error_log = result.scalar_one_or_none()

    assert error_log is not None
    assert "Ollama connection error" in error_log.details.get('error', '')


@pytest.mark.asyncio
async def test_process_task_queue(db_session, test_project):
    """Test traitement de la file d'attente"""
    # Mock Ollama client
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate_code = AsyncMock(return_value="# Generated code")

    # Créer plusieurs tâches avec différentes priorités
    task_p1 = Task(
        project_id=test_project.id,
        title="P1 Task",
        status=TaskStatus.READY,
        priority=TaskPriority.P1,
        llm_prompt="Urgent task"
    )
    task_p2 = Task(
        project_id=test_project.id,
        title="P2 Task",
        status=TaskStatus.READY,
        priority=TaskPriority.P2,
        llm_prompt="Normal task"
    )
    task_p3 = Task(
        project_id=test_project.id,
        title="P3 Task",
        status=TaskStatus.READY,
        priority=TaskPriority.P3,
        llm_prompt="Low priority task"
    )

    db_session.add_all([task_p1, task_p2, task_p3])
    await db_session.commit()

    # Traiter la queue
    orchestrator = TaskOrchestrator(db_session, mock_client)
    success_count = await orchestrator.process_task_queue(batch_size=2)

    assert success_count == 2  # Seulement 2 traitées (batch_size=2)

    # Vérifier que P1 et P2 ont été traitées (pas P3)
    await db_session.refresh(task_p1)
    await db_session.refresh(task_p2)
    await db_session.refresh(task_p3)

    assert task_p1.status == TaskStatus.MANUAL_REVIEW
    assert task_p2.status == TaskStatus.MANUAL_REVIEW
    assert task_p3.status == TaskStatus.READY  # Pas encore traitée


@pytest.mark.asyncio
async def test_get_queue_stats(db_session, test_project):
    """Test récupération des statistiques"""
    # Créer des tâches avec différents statuts
    task_ready = Task(
        project_id=test_project.id,
        title="Ready task",
        status=TaskStatus.READY,
        priority=TaskPriority.P1,
        llm_prompt="Test"
    )
    task_manual_review = Task(
        project_id=test_project.id,
        title="Review task",
        status=TaskStatus.MANUAL_REVIEW,
        priority=TaskPriority.P1,
        llm_prompt="Test"
    )
    task_failed = Task(
        project_id=test_project.id,
        title="Failed task",
        status=TaskStatus.FAILED,
        priority=TaskPriority.P1,
        llm_prompt="Test"
    )

    db_session.add_all([task_ready, task_manual_review, task_failed])
    await db_session.commit()

    # Récupérer les stats
    mock_client = MagicMock(spec=OllamaClient)
    orchestrator = TaskOrchestrator(db_session, mock_client)
    stats = await orchestrator.get_queue_stats()

    assert stats['ready'] == 1
    assert stats['manual_review'] == 1
    assert stats['failed'] == 1
    assert stats['generating'] == 0
