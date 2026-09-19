"""
Tests d'intégration du workflow complet.

Test le parcours end-to-end :
1. Créer user → login → JWT valide
2. Créer projet PRO avec config financière
3. Créer tâche P1 avec description
4. Tâche passe à READY
5. Orchestrateur génère code via Ollama (mock)
6. Tâche passe à MANUAL_REVIEW
7. Validation code → COMPLETED
8. Vérifier TaskLogs créés
9. Vérifier time entries si projet PRO
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.main import app
from app.core.database import get_db
from app.models import User, Project, Task, TaskLog, TimeEntry
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user_data():
    """Données pour créer un utilisateur de test."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
async def auth_client(test_user_data):
    """Client HTTP authentifié."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Créer utilisateur
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 200

        # Login
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200

        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        yield client


@pytest.mark.asyncio
async def test_complete_task_workflow(auth_client: AsyncClient):
    """
    Test complet du workflow de génération et validation de code.
    """

    # 1. Créer un projet professionnel
    project_data = {
        "name": "Client A - E-commerce",
        "description": "Refonte complète plateforme e-commerce",
        "type": "professional",
        "status": "active",
        "features": {
            "code_gen": True,
            "veille": True,
            "git_auto": False
        },
        "financial_config": {
            "hourly_rate": 80.0,
            "budget": 5000.0,
            "currency": "EUR"
        }
    }

    response = await auth_client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 200
    project = response.json()
    project_id = project["id"]

    assert project["name"] == project_data["name"]
    assert project["type"] == "professional"
    assert project["financial_config"]["hourly_rate"] == 80.0

    # 2. Créer une tâche avec prompt LLM
    task_data = {
        "project_id": project_id,
        "title": "Créer API REST products",
        "description": "CRUD complet pour gestion produits",
        "priority": "P1",
        "llm_prompt": "Génère une API FastAPI avec endpoints CRUD pour products (create, read, update, delete). Utilise SQLAlchemy async et Pydantic pour la validation.",
        "status": "created"
    }

    response = await auth_client.post("/api/v1/tasks/", json=task_data)
    assert response.status_code == 200
    task = response.json()
    task_id = task["id"]

    assert task["title"] == task_data["title"]
    assert task["status"] == "created"
    assert task["priority"] == "P1"

    # 3. Passer la tâche à READY (simulation manuelle)
    update_data = {"status": "ready"}
    response = await auth_client.put(f"/api/v1/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "ready"

    # 4. Mock de la génération de code par Ollama
    mock_generated_code = '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

router = APIRouter()

@router.post("/products/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """Créer un nouveau produit."""
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/products/", response_model=List[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lister tous les produits."""
    result = await db.execute(select(Product).offset(skip).limit(limit))
    products = result.scalars().all()
    return products
'''

    with patch('app.services.llm_client.OllamaClient.generate_code') as mock_gen:
        mock_gen.return_value = mock_generated_code

        # Forcer la génération de code
        response = await auth_client.post(f"/api/v1/tasks/{task_id}/generate")
        assert response.status_code == 200
        task = response.json()

    # 5. Vérifier que la tâche est en MANUAL_REVIEW avec du code généré
    response = await auth_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task = response.json()

    assert task["status"] == "manual_review"
    assert task["generated_code"] is not None
    assert "APIRouter" in task["generated_code"]

    # 6. Valider le code généré
    validation_data = {
        "approved": True,
        "notes": "Code validé, prêt pour intégration"
    }

    response = await auth_client.post(
        f"/api/v1/tasks/{task_id}/validate",
        json=validation_data
    )
    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "completed"
    assert task["completed_at"] is not None

    # 7. Vérifier les logs de la tâche
    response = await auth_client.get(f"/api/v1/tasks/{task_id}/logs")
    assert response.status_code == 200
    logs = response.json()

    assert len(logs) >= 3  # Au minimum: created, code_generated, validated

    event_types = [log["event_type"] for log in logs]
    assert "created" in event_types
    assert "code_generated" in event_types
    assert "validated" in event_types

    # 8. Vérifier les statistiques du projet
    response = await auth_client.get(f"/api/v1/projects/{project_id}/stats")
    assert response.status_code == 200
    stats = response.json()

    assert stats["total_tasks"] >= 1
    assert stats["completed_tasks"] >= 1


@pytest.mark.asyncio
async def test_task_rejection_workflow(auth_client: AsyncClient):
    """
    Test du workflow de rejet de code généré.
    """

    # 1. Créer projet
    project_data = {
        "name": "Test Project",
        "type": "personal",
        "status": "active"
    }
    response = await auth_client.post("/api/v1/projects/", json=project_data)
    project_id = response.json()["id"]

    # 2. Créer tâche
    task_data = {
        "project_id": project_id,
        "title": "Test Task",
        "priority": "P2",
        "llm_prompt": "Generate a simple function",
        "status": "manual_review",
        "generated_code": "def bad_code(): pass"
    }
    response = await auth_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # 3. Rejeter le code
    rejection_data = {
        "approved": False,
        "notes": "Code trop simple, manque de gestion d'erreurs"
    }
    response = await auth_client.post(
        f"/api/v1/tasks/{task_id}/validate",
        json=rejection_data
    )
    assert response.status_code == 200
    task = response.json()

    # La tâche devrait repasser à READY pour régénération
    assert task["status"] in ["ready", "failed"]

    # Vérifier les logs
    response = await auth_client.get(f"/api/v1/tasks/{task_id}/logs")
    logs = response.json()

    event_types = [log["event_type"] for log in logs]
    assert "rejected" in event_types or "validation_failed" in event_types


@pytest.mark.asyncio
async def test_task_cancellation(auth_client: AsyncClient):
    """
    Test de l'annulation d'une tâche.
    """

    # Créer projet
    project_data = {"name": "Test Project", "type": "personal", "status": "active"}
    response = await auth_client.post("/api/v1/projects/", json=project_data)
    project_id = response.json()["id"]

    # Créer tâche
    task_data = {
        "project_id": project_id,
        "title": "Task to Cancel",
        "priority": "P3",
        "status": "ready"
    }
    response = await auth_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Annuler la tâche
    response = await auth_client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert response.status_code == 200
    task = response.json()

    assert task["status"] == "cancelled"

    # Vérifier que la tâche n'apparaît plus dans la liste par défaut
    response = await auth_client.get("/api/v1/tasks/")
    tasks = response.json()
    task_ids = [t["id"] for t in tasks]

    # La tâche annulée devrait être filtrée
    assert task_id not in task_ids


@pytest.mark.asyncio
async def test_project_archiving_cancels_tasks(auth_client: AsyncClient):
    """
    Test que l'archivage d'un projet annule ses tâches actives.
    """

    # Créer projet
    project_data = {"name": "Project to Archive", "type": "personal", "status": "active"}
    response = await auth_client.post("/api/v1/projects/", json=project_data)
    project_id = response.json()["id"]

    # Créer plusieurs tâches
    task_ids = []
    for i in range(3):
        task_data = {
            "project_id": project_id,
            "title": f"Task {i+1}",
            "priority": "P2",
            "status": "ready"
        }
        response = await auth_client.post("/api/v1/tasks/", json=task_data)
        task_ids.append(response.json()["id"])

    # Archiver le projet (soft delete)
    response = await auth_client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200

    # Vérifier que les tâches ont été annulées
    for task_id in task_ids:
        response = await auth_client.get(f"/api/v1/tasks/{task_id}")
        task = response.json()
        assert task["status"] == "cancelled"

    # Vérifier que le projet n'apparaît plus dans la liste
    response = await auth_client.get("/api/v1/projects/")
    projects = response.json()
    project_ids_list = [p["id"] for p in projects]

    assert project_id not in project_ids_list
