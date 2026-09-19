"""
API endpoints for User Settings
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings as app_settings
from app.api.deps import get_current_user
from app.models import User, UserSettings
from app.schemas import (
    UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse, OllamaModelInfo
)
from app.services.llm_client import OllamaClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ollama-models", response_model=List[OllamaModelInfo])
async def list_ollama_models(
    current_user: User = Depends(get_current_user)
):
    """
    Liste tous les modèles Ollama disponibles sur le serveur

    Retourne la liste des modèles installés avec leurs métadonnées
    """
    try:
        from app.services.model_registry import list_local_models_detailed
        models = [
            OllamaModelInfo(name=m["name"], size=m["size"], modified_at=m["modified_at"])
            for m in list_local_models_detailed(force=True)
        ]

        logger.info(f"✅ Listed {len(models)} Ollama models for user {current_user.id}")
        return models

    except Exception as e:
        logger.error(f"❌ Failed to list Ollama models: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Impossible de récupérer les modèles Ollama: {str(e)}"
        )


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère les paramètres de l'utilisateur connecté

    Si les paramètres n'existent pas encore, ils sont créés avec les valeurs par défaut
    """
    # Chercher les paramètres existants
    query = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()

    # Si pas de paramètres, créer avec valeurs par défaut
    if not user_settings:
        logger.info(f"Creating default settings for user {current_user.id}")
        user_settings = UserSettings(
            user_id=current_user.id,
            ollama_model_code=app_settings.OLLAMA_MODEL_CODE
        )
        db.add(user_settings)
        await db.commit()
        await db.refresh(user_settings)
        logger.info(f"✅ Created settings for user {current_user.id}")

    return user_settings


@router.put("", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour les paramètres de l'utilisateur connecté

    Permet de mettre à jour partiellement les paramètres (seulement les champs fournis)
    """
    # Récupérer les paramètres existants (ou créer si non existants)
    query = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(query)
    user_settings = result.scalar_one_or_none()

    # Si pas de paramètres, créer
    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.id,
            ollama_model_code=app_settings.OLLAMA_MODEL_CODE
        )
        db.add(user_settings)
        await db.flush()

    # Mettre à jour seulement les champs fournis
    update_data = settings_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user_settings, field, value)

    await db.commit()
    await db.refresh(user_settings)

    logger.info(f"✅ Updated settings for user {current_user.id}: {update_data}")
    return user_settings


@router.post("", response_model=UserSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_user_settings(
    settings_create: UserSettingsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crée explicitement les paramètres utilisateur

    Normalement, les paramètres sont créés automatiquement au premier GET/PUT,
    mais cet endpoint permet de les créer manuellement si nécessaire
    """
    # Vérifier si les paramètres existent déjà
    query = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(query)
    existing_settings = result.scalar_one_or_none()

    if existing_settings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Les paramètres utilisateur existent déjà. Utilisez PUT pour les mettre à jour."
        )

    # Créer les nouveaux paramètres
    user_settings = UserSettings(
        user_id=current_user.id,
        **settings_create.model_dump()
    )
    db.add(user_settings)
    await db.commit()
    await db.refresh(user_settings)

    logger.info(f"✅ Created settings for user {current_user.id}")
    return user_settings
