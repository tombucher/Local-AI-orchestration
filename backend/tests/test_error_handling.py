import json
"""
Tests pour la gestion des erreurs centralisée

Ce module teste le système de gestion des erreurs personnalisées
pour s'assurer que les exceptions sont correctement transformées
en réponses JSON standardisées.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.exceptions import (
    EntityNotFoundError,
    AgentProcessingError,
    DatabaseError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError
)
from app.api.errors import (
    app_exception_handler,
    entity_not_found_handler,
    request_validation_error_handler
)
from app.models import User, Project

client = TestClient(app)

@pytest.mark.asyncio
async def test_entity_not_found_error():
    """Test que EntityNotFoundError est correctement gérée"""
    # Créer une exception
    exc = EntityNotFoundError("Project", "123")

    # Créer une requête mock
    class MockRequest:
        pass

    # Appeler le handler
    response = await entity_not_found_handler(MockRequest(), exc)

    # Vérifier la réponse
    assert response.status_code == 404
    data = response.body.decode()
    assert "entity_not_found" in data
    assert "Project with ID 123 not found" in data
    assert "entity_type" in data
    assert "entity_id" in data

@pytest.mark.asyncio
async def test_agent_processing_error():
    """Test que AgentProcessingError est correctement gérée"""
    exc = AgentProcessingError("456", "code_generator", "LLM timeout")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 500
    data = response.body.decode()
    assert "agent_processing_error" in data
    assert "Agent code_generator failed to process task 456" in data
    assert "task_id" in data
    assert "agent_type" in data
    assert "original_error" in data

@pytest.mark.asyncio
async def test_validation_error():
    """Test que ValidationError est correctement gérée"""
    exc = ValidationError("email", "Invalid email format")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 422
    data = response.body.decode()
    assert "validation_error" in data
    assert "Validation error for field email" in data
    assert "field" in data
    assert "error_details" in data

@pytest.mark.asyncio
async def test_database_error():
    """Test que DatabaseError est correctement gérée"""
    exc = DatabaseError("create", "Project", "Connection timeout")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 500
    data = response.body.decode()
    assert "database_error" in data
    assert "Database error during create of Project" in data
    assert "operation" in data
    assert "entity_type" in data
    assert "original_error" in data

@pytest.mark.asyncio
async def test_authentication_error():
    """Test que AuthenticationError est correctement gérée"""
    exc = AuthenticationError("invalid_credentials")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 401
    data = response.body.decode()
    assert "invalid_credentials" in data
    assert "Authentication failed" in data
    assert "error_type" in data

@pytest.mark.asyncio
async def test_authorization_error():
    """Test que AuthorizationError est correctement gérée"""
    exc = AuthorizationError("Project", "delete")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 403
    data = response.body.decode()
    assert "authorization_error" in data
    assert "Permission denied to delete on Project" in data
    assert "resource_type" in data
    assert "action" in data

@pytest.mark.asyncio
async def test_conflict_error():
    """Test que ConflictError est correctement gérée"""
    exc = ConflictError("Project", "Name already exists")

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 409
    data = response.body.decode()
    assert "conflict_error" in data
    assert "Conflict with existing Project" in data
    assert "resource_type" in data
    assert "conflict_details" in data

@pytest.mark.asyncio
async def test_rate_limit_error():
    """Test que RateLimitError est correctement gérée"""
    exc = RateLimitError(100, 60)

    class MockRequest:
        pass

    response = await app_exception_handler(MockRequest(), exc)

    assert response.status_code == 429
    data = response.body.decode()
    assert "rate_limit_exceeded" in data
    assert "Rate limit exceeded. Try again in 60 seconds" in data
    assert "limit" in data
    assert "retry_after" in data

@pytest.mark.asyncio
async def test_request_validation_error():
    """Test que les erreurs de validation FastAPI sont correctement gérées"""
    from fastapi.exceptions import RequestValidationError

    # Créer une erreur de validation mock
    errors = [
        {
            "loc": ["body", "email"],
            "msg": "field required",
            "type": "value_error.missing"
        },
        {
            "loc": ["body", "password"],
            "msg": "ensure this value has at least 8 characters",
            "type": "value_error.any_str.min_length",
            "ctx": {"limit_value": 8}
        }
    ]
    exc = RequestValidationError(errors)

    class MockRequest:
        pass

    response = await request_validation_error_handler(MockRequest(), exc)

    assert response.status_code == 422
    data = response.body.decode()
    assert "validation_error" in data
    assert "Request validation failed" in data
    assert "errors" in data
    assert "email" in data
    assert "password" in data

@pytest.mark.asyncio
async def test_entity_not_found_endpoint(client, auth_headers):
    """Test un endpoint réel qui utilise EntityNotFoundError"""
    # Essayer de récupérer un projet qui n'existe pas
    response = await client.get("/api/v1/projects/999999", headers=auth_headers)

    # Vérifier que l'erreur est correctement formatée
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"] == "entity_not_found"
    assert "message" in data
    assert "Project with ID 999999 not found" in data["message"]
    assert "details" in data
    assert data["details"]["entity_type"] == "Project"
    assert data["details"]["entity_id"] == "999999"

@pytest.mark.asyncio
async def test_error_format_consistency():
    """Test que toutes les erreurs ont un format cohérent"""
    errors_to_test = [
        EntityNotFoundError("Task", "789"),
        AgentProcessingError("123", "web_research", "Network error"),
        DatabaseError("update", "User", "Constraint violation"),
        ValidationError("name", "Too short"),
        AuthenticationError("expired_token"),
        AuthorizationError("Task", "view"),
        ConflictError("User", "Email already used"),
        RateLimitError(50, 30)
    ]

    for exc in errors_to_test:
        class MockRequest:
            pass

        response = await app_exception_handler(MockRequest(), exc)

        # Vérifier que toutes les réponses ont le format attendu
        data = response.body.decode()
        assert "error" in data
        assert "message" in data
        assert "details" in data

        # Vérifier que le code d'erreur est présent
        error_data = json.loads(response.body)
        assert error_data["error"] != ""
        assert error_data["message"] != ""
        assert isinstance(error_data["details"], dict)