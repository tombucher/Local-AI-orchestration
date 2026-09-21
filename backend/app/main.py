"""
Point d'entrée principal de l'application FastAPI
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.database import check_db_schema
from app.core.logging import setup_logging, set_correlation_id, get_correlation_id
from app.api.v1 import auth, projects, tasks, time, orchestrator, settings as settings_router, reports, ideation
from app.api.errors import register_exception_handlers
from app.services.scheduler import start_scheduler, stop_scheduler

# Configuration du logging structuré avec correlation IDs
setup_logging(log_level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Gestion du cycle de vie de l'application

    Initialise la base de données et le scheduler au démarrage
    """
    logger.info("🚀 Starting Orchestrateur IA API...")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Database: {settings.DATABASE_URL}")

    # Vérifier que le schéma correspond aux migrations.
    # Ne crée plus les tables : Alembic est seul maître du schéma, sinon les
    # nouveaux modèles étaient créés avant lui et chaque migration échouait.
    await check_db_schema()

    # Démarrer le scheduler pour l'orchestrateur
    logger.info("Starting task scheduler...")
    start_scheduler()

    logger.info("✅ Application started successfully")

    yield

    # Arrêter le scheduler proprement
    logger.info("👋 Shutting down application...")
    stop_scheduler()


# Créer l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware de catch-all pour les erreurs inattendues - DEVANT ÊTRE EN HAUT POUR ÊTRE EXÉCUTÉ EN DERNIER
class ExceptionCatcherMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui capture les exceptions non gérées et les transforme
    en réponses JSON standardisées
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Log l'erreur pour le débogage
            logger.error(f"Unhandled exception in middleware: {exc}", exc_info=True)

            # Retourne une réponse standardisée
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

# Middleware correlation ID : assigne un ID unique par requête pour le tracing
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Utiliser le header X-Correlation-ID si fourni, sinon en générer un
        cid = request.headers.get("X-Correlation-ID")
        cid = set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response

app.add_middleware(CorrelationIdMiddleware)

# Ajouter le middleware - EN HAUT POUR ÊTRE EXÉCUTÉ EN DERNIER
app.add_middleware(ExceptionCatcherMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Returns:
        Status de l'application
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV
    }


# Inclure les routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["auth"]
)

app.include_router(
    projects.router,
    prefix=f"{settings.API_V1_PREFIX}/projects",
    tags=["projects"]
)

app.include_router(
    tasks.router,
    prefix=f"{settings.API_V1_PREFIX}/tasks",
    tags=["tasks"]
)

app.include_router(
    time.router,
    prefix=f"{settings.API_V1_PREFIX}/time",
    tags=["time"]
)

app.include_router(
    orchestrator.router,
    prefix=f"{settings.API_V1_PREFIX}/orchestrator",
    tags=["orchestrator"]
)

app.include_router(
    settings_router.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["settings"]
)

app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_PREFIX}/reports",
    tags=["reports"]
)

app.include_router(
    ideation.router,
    prefix=f"{settings.API_V1_PREFIX}/ideation",
    tags=["Ideation"]
)

# Enregistrer les handlers d'exceptions
register_exception_handlers(app)

# Configuration CORS - DOIT ÊTRE TOUT EN BAS POUR ÊTRE EXÉCUTÉ EN PREMIER
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """
    Endpoint racine
    
    Returns:
        Message de bienvenue
    """
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs"
    }
