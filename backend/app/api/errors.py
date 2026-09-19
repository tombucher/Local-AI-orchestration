"""
Exception Handlers pour l'application Orchestrateur IA

Ce module contient les handlers qui transforment les exceptions personnalisées
en réponses JSON standardisées pour l'API.
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppException,
    EntityNotFoundError,
    AgentProcessingError,
    DatabaseError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError
)

logger = logging.getLogger(__name__)

async def app_exception_handler(request: Request, exc: AppException):
    """
    Handler pour les exceptions personnalisées de l'application

    Args:
        request: Requête FastAPI
        exc: Exception personnalisée

    Returns:
        JSONResponse: Réponse standardisée avec le format d'erreur
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
        # Headers CORS gérés par CORSMiddleware, pas besoin de les dupliquer ici
    )

async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    """
    Handler spécifique pour les entités non trouvées
    """
    return await app_exception_handler(request, exc)

async def agent_processing_handler(request: Request, exc: AgentProcessingError):
    """
    Handler spécifique pour les erreurs de traitement des agents IA
    """
    return await app_exception_handler(request, exc)

async def database_error_handler(request: Request, exc: DatabaseError):
    """
    Handler spécifique pour les erreurs de base de données
    """
    return await app_exception_handler(request, exc)

async def validation_error_handler(request: Request, exc: ValidationError):
    """
    Handler spécifique pour les erreurs de validation
    """
    return await app_exception_handler(request, exc)

async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """
    Handler spécifique pour les erreurs d'authentification
    """
    return await app_exception_handler(request, exc)

async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """
    Handler spécifique pour les erreurs d'autorisation
    """
    return await app_exception_handler(request, exc)

async def conflict_error_handler(request: Request, exc: ConflictError):
    """
    Handler spécifique pour les conflits de ressources
    """
    return await app_exception_handler(request, exc)

async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """
    Handler spécifique pour les erreurs de rate limiting
    """
    return await app_exception_handler(request, exc)

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handler pour les exceptions HTTP standard de Starlette

    Args:
        request: Requête FastAPI
        exc: Exception HTTP Starlette

    Returns:
        JSONResponse: Réponse standardisée
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "details": {}
        }
        # Headers CORS gérés par CORSMiddleware, pas besoin de les dupliquer ici
    )

async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handler pour les erreurs de validation des requêtes FastAPI

    Args:
        request: Requête FastAPI
        exc: Erreur de validation

    Returns:
        JSONResponse: Réponse standardisée avec les détails des erreurs
    """
    errors = []
    for error in exc.errors():
        field_path = " → ".join(str(part) for part in error.get("loc", []))
        errors.append({
            "field": field_path,
            "error_type": error.get("type", "validation_error"),
            "message": error.get("msg", "Validation failed")
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": {
                "errors": errors
            }
        }
        # Headers CORS gérés par CORSMiddleware, pas besoin de les dupliquer ici
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler générique pour toutes les exceptions non gérées

    Args:
        request: Requête FastAPI
        exc: Exception non gérée

    Returns:
        JSONResponse: Réponse standardisée pour les erreurs internes
    """
    # Log l'erreur pour le débogage
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": {
                "error_type": type(exc).__name__,
                "error_message": str(exc)
            }
        }
        # Headers CORS gérés par CORSMiddleware, pas besoin de les dupliquer ici
    )

def register_exception_handlers(app):
    """
    Enregistre tous les handlers d'exceptions sur l'application FastAPI

    Args:
        app: Application FastAPI
    """
    # Handlers pour les exceptions personnalisées
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)
    app.add_exception_handler(AgentProcessingError, agent_processing_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)

    # Handlers pour les exceptions FastAPI/Starlette
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    # Handler générique pour les exceptions non gérées
    app.add_exception_handler(Exception, generic_exception_handler)    # Handler générique pour les exceptions non gérées
