"""
API v1 router initialization
"""
from fastapi import APIRouter

from app.api.v1 import projects, tasks, time, settings, ideation

api_router = APIRouter()

# Inclure tous les routers
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(time.router)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(ideation.router, prefix="/ideation", tags=["ideation"])

__all__ = ["api_router"]
