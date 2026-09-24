"""
Tests pour les endpoints Tasks
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers: dict):
    """Test création tâche basique"""
    # Créer projet d'abord
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test Project",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    # Créer tâche
    data = {
        "project_id": project_id,
        "title": "Implémenter feature X",
        "description": "Description détaillée de la feature",
        "priority": "P1"
    }
    
    response = await client.post("/api/v1/tasks/", json=data, headers=auth_headers)
    assert response.status_code == 201
    
    result = response.json()
    assert result["title"] == data["title"]
    assert result["priority"] == "P1"
    assert result["status"] == "created"  # Status initial


@pytest.mark.asyncio
async def test_create_task_with_prompt(client: AsyncClient, auth_headers: dict):
    """Test création tâche avec prompt → status READY"""
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    data = {
        "project_id": project_id,
        "title": "Créer API endpoint",
        "llm_prompt": "Créer un endpoint FastAPI pour gérer les users",
        "priority": "P2"
    }
    
    response = await client.post("/api/v1/tasks/", json=data, headers=auth_headers)
    assert response.status_code == 201
    
    result = response.json()
    assert result["status"] == "ready"  # READY car prompt fourni
    assert result["llm_prompt"] == data["llm_prompt"]


@pytest.mark.asyncio
async def test_create_task_invalid_project(client: AsyncClient, auth_headers: dict):
    """Test erreur si projet inexistant"""
    data = {
        "project_id": 99999,
        "title": "Invalid",
        "priority": "P2"
    }
    
    response = await client.post("/api/v1/tasks/", json=data, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, auth_headers: dict):
    """Test liste tâches avec pagination"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    # Créer 5 tâches
    for i in range(5):
        await client.post("/api/v1/tasks/", json={
            "project_id": project_id,
            "title": f"Task {i}",
            "priority": "P2"
        }, headers=auth_headers)
    
    # Lister
    response = await client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    
    result = response.json()
    assert result["total"] == 5
    assert len(result["items"]) == 5


@pytest.mark.asyncio
async def test_list_tasks_with_filters(client: AsyncClient, auth_headers: dict):
    """Test filtres liste tâches"""
    # Setup projet
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    # Créer tâches avec différentes priorités
    await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Urgent",
        "priority": "P1"
    }, headers=auth_headers)
    
    await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Normal",
        "priority": "P3"
    }, headers=auth_headers)
    
    # Filtrer par priorité
    response = await client.get("/api/v1/tasks/?priority=P1", headers=auth_headers)
    assert response.status_code == 200
    
    result = response.json()
    assert result["total"] == 1
    assert result["items"][0]["priority"] == "P1"


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, auth_headers: dict):
    """Test récupération détails tâche"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Test Get",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Get
    response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == task_id


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, auth_headers: dict):
    """Test modification tâche"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Original",
        "priority": "P3"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Update
    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Modifié", "priority": "P1"},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    result = response.json()
    assert result["title"] == "Modifié"
    assert result["priority"] == "P1"


@pytest.mark.asyncio
async def test_validate_task_approved(client: AsyncClient, auth_headers: dict):
    """Test validation code (approuvé)"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    # Créer tâche en MANUAL_REVIEW
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Test Validation",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Mettre en MANUAL_REVIEW manuellement
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": "manual_review",
            "generated_code": "def hello(): return 'world'"
        },
        headers=auth_headers
    )
    
    # Valider (approuver)
    response = await client.post(
        f"/api/v1/tasks/{task_id}/validate",
        json={"approved": True, "notes": "Code OK"},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    result = response.json()
    assert result["status"] == "completed"
    assert result["validation_notes"] == "Code OK"
    assert result["completed_at"] is not None


@pytest.mark.asyncio
async def test_validate_task_rejected(client: AsyncClient, auth_headers: dict):
    """Test validation code (rejeté)"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Test Reject",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Mettre en MANUAL_REVIEW
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "status": "manual_review",
            "generated_code": "bad code"
        },
        headers=auth_headers
    )
    
    # Rejeter
    response = await client.post(
        f"/api/v1/tasks/{task_id}/validate",
        json={"approved": False, "notes": "Needs refactoring"},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    result = response.json()
    assert result["status"] == "ready"  # Retour pour régénération
    assert result["generated_code"] is None  # Code nettoyé
    assert result["validation_notes"] == "Needs refactoring"


@pytest.mark.asyncio
async def test_validate_task_wrong_status(client: AsyncClient, auth_headers: dict):
    """Test erreur si validation sur mauvais status"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Test",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    # Status = CREATED
    
    # Essayer de valider
    response = await client.post(
        f"/api/v1/tasks/{task_id}/validate",
        json={"approved": True},
        headers=auth_headers
    )
    assert response.status_code == 400  # Bad request


@pytest.mark.asyncio
async def test_cancel_task(client: AsyncClient, auth_headers: dict):
    """Test annulation tâche"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "À annuler",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Annuler
    response = await client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    
    result = response.json()
    assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_get_task_logs(client: AsyncClient, auth_headers: dict):
    """Test récupération historique tâche"""
    # Setup
    project_response = await client.post("/api/v1/projects/", json={
        "name": "Test",
        "type": "personal",
        "features": {"code_gen": True}
    }, headers=auth_headers)
    project_id = project_response.json()["id"]
    
    create_response = await client.post("/api/v1/tasks/", json={
        "project_id": project_id,
        "title": "Test Logs",
        "priority": "P2"
    }, headers=auth_headers)
    task_id = create_response.json()["id"]
    
    # Modifier status (crée des logs)
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "ready"},
        headers=auth_headers
    )
    
    # Récupérer logs
    response = await client.get(f"/api/v1/tasks/{task_id}/logs", headers=auth_headers)
    assert response.status_code == 200
    
    logs = response.json()
    assert len(logs) >= 2  # Au moins: created + status_changed
    assert logs[0]["event_type"] == "created"


def test_reponse_accepte_les_dependances_orm():
    """task.__dict__ porte la relation chargée : des objets Task, pas des IDs."""
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from app.schemas.task import TaskResponse

    reponse = TaskResponse(
        id=2, project_id=1, title="Note", status="created", created_at=datetime.now(timezone.utc),
        dependencies=[SimpleNamespace(id=7), SimpleNamespace(id=9)],
    )
    assert reponse.dependencies == [7, 9]
    assert TaskResponse(id=2, project_id=1, title="N", status="created",
                        created_at=datetime.now(timezone.utc), dependencies=None).dependencies == []


@pytest.mark.asyncio
async def test_generer_une_tache_avec_dependances(client, auth_headers, monkeypatch):
    """/generate répondait 500 pour toute tâche ayant des dépendances."""
    from app.api.v1 import tasks as tasks_api

    async def sans_generation(task_id):  # ne jamais toucher la vraie base
        return None
    monkeypatch.setattr(tasks_api, "_generate_code_background", sans_generation)

    projet = (await client.post("/api/v1/projects/", json={
        "name": "Deps", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    amont = (await client.post("/api/v1/tasks/", json={
        "project_id": projet, "title": "Structure HTML", "priority": "P2",
    }, headers=auth_headers)).json()["id"]
    aval = (await client.post("/api/v1/tasks/", json={
        "project_id": projet, "title": "Styles CSS", "priority": "P2", "dependency_ids": [amont],
    }, headers=auth_headers)).json()["id"]

    r = await client.post(f"/api/v1/tasks/{aval}/generate", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "generating"
    assert r.json()["dependencies"] == [amont]
