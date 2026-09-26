"""
API endpoints for User Settings
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings as app_settings
from app.api.deps import get_current_user
from app.models import User, UserSettings
from app.models.rss_feed import RssFeed
from app.schemas import (
    UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse, OllamaModelInfo
)
from app.schemas.rss_feed import (
    FeedCheckResult, RssFeedCreate, RssFeedResponse, RssFeedUpdate,
)
from app.services.feed_library import inspect_feed
from app.services import project_folders
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


# ════════════════════════════════════════════════════════════
# Bibliothèque de flux RSS
# Les sources de veille utiles dépendent du sujet : c'est l'utilisateur qui
# enrichit sa bibliothèque au fil de ses trouvailles. Chaque flux est vérifié
# à l'ajout et ses thèmes déduits de son contenu.
# ════════════════════════════════════════════════════════════

@router.get("/feeds", response_model=List[RssFeedResponse])
async def list_feeds(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flux RSS enregistrés par l'utilisateur, les plus récents d'abord."""
    result = await db.execute(
        select(RssFeed).where(RssFeed.user_id == current_user.id).order_by(RssFeed.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/feeds/preview", response_model=FeedCheckResult)
async def preview_feed(
    payload: RssFeedCreate,
    current_user: User = Depends(get_current_user),
):
    """Vérifie un flux sans l'enregistrer — pour afficher un aperçu avant l'ajout."""
    return FeedCheckResult(**await inspect_feed(payload.url))


@router.post("/feeds", response_model=RssFeedResponse, status_code=status.HTTP_201_CREATED)
async def add_feed(
    payload: RssFeedCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ajoute un flux après vérification. Un flux injoignable ou vide est refusé."""
    existing = await db.execute(
        select(RssFeed).where(RssFeed.user_id == current_user.id, RssFeed.url == payload.url)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce flux est déjà dans ta bibliothèque",
        )

    check = await inspect_feed(payload.url)
    if not check["ok"]:
        # Refus explicite : mieux vaut le dire maintenant qu'un flux mort silencieux
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flux inutilisable — {check['status']}",
        )

    feed = RssFeed(
        user_id=current_user.id,
        url=payload.url,
        title=(payload.title or check["title"])[:255],
        tags=payload.tags if payload.tags is not None else check["tags"],
        enabled=True,
        last_checked=datetime.now(timezone.utc),
        last_status=check["status"],
        last_entry_count=check["entry_count"],
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    logger.info(f"📰 Flux ajouté par l'utilisateur {current_user.id} : {feed.url}")
    return feed


@router.patch("/feeds/{feed_id}", response_model=RssFeedResponse)
async def update_feed(
    feed_id: int,
    payload: RssFeedUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renomme un flux, ajuste ses thèmes ou l'active/désactive."""
    feed = await _get_own_feed(db, feed_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    await db.commit()
    await db.refresh(feed)
    return feed


@router.post("/feeds/{feed_id}/check", response_model=RssFeedResponse)
async def check_feed(
    feed_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-vérifie un flux et rafraîchit ses thèmes (les flux meurent sans prévenir)."""
    feed = await _get_own_feed(db, feed_id, current_user.id)
    check = await inspect_feed(feed.url)
    feed.last_checked = datetime.now(timezone.utc)
    feed.last_status = check["status"]
    feed.last_entry_count = check["entry_count"]
    if check["ok"]:
        feed.tags = check["tags"]
        if not feed.title:
            feed.title = check["title"][:255]
    await db.commit()
    await db.refresh(feed)
    return feed


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retire un flux de la bibliothèque."""
    feed = await _get_own_feed(db, feed_id, current_user.id)
    await db.delete(feed)
    await db.commit()


async def _get_own_feed(db: AsyncSession, feed_id: int, user_id: int) -> RssFeed:
    """Récupère un flux en garantissant qu'il appartient bien à l'utilisateur."""
    result = await db.execute(
        select(RssFeed).where(RssFeed.id == feed_id, RssFeed.user_id == user_id)
    )
    feed = result.scalars().first()
    if not feed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flux introuvable")
    return feed


# ------------------------------------------------------ dossier de projets --

class ProjectsFolderUpdate(BaseModel):
    path: Optional[str] = None  # relatif au dossier partagé ; None = désactiver


async def _own_settings(db: AsyncSession, user: User) -> UserSettings:
    user_settings = (await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id))).scalars().first()
    if not user_settings:
        user_settings = UserSettings(user_id=user.id, ollama_model_code=app_settings.OLLAMA_MODEL_CODE)
        db.add(user_settings)
        await db.flush()
    return user_settings


def _folder_state(folder: Optional[str]) -> dict:
    etat = {
        "available": project_folders.mount_available(),
        "root_display": project_folders.display_path(),
        "path": folder,
        "display": project_folders.display_path(folder) if folder else None,
        "projects": [],
    }
    if folder and etat["available"]:
        try:
            racine = project_folders.inside_mount(folder)
            etat["projects"] = [
                {"folder": f.parent.name, "file": f.name, "path": project_folders.relative(f)}
                for f in project_folders.scan(racine)
            ]
        except ValueError:
            pass
    return etat


@router.get("/projects-folder")
async def get_projects_folder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dossier de projets choisi, et les projets qu'il contient."""
    return _folder_state((await _own_settings(db, current_user)).projects_folder)


@router.get("/projects-folder/browse")
async def browse_projects_folder(
    path: str = Query("", description="Dossier relatif au dossier partagé"),
    current_user: User = Depends(get_current_user),
):
    """Sous-dossiers d'un dossier, pour choisir le dossier de projets."""
    if not project_folders.mount_available():
        raise HTTPException(status_code=409, detail="Aucun dossier du Mac n'est partagé avec l'outil.")
    try:
        return project_folders.browse(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/projects-folder")
async def set_projects_folder(
    payload: ProjectsFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Choisit (ou retire) le dossier de projets, puis synchronise aussitôt."""
    user_settings = await _own_settings(db, current_user)
    chemin = (payload.path or "").strip("/") or None
    if chemin is not None:
        try:
            dossier = project_folders.inside_mount(chemin)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not dossier.is_dir():
            raise HTTPException(status_code=400, detail="Ce dossier n'existe pas.")
        chemin = project_folders.relative(dossier)
    user_settings.projects_folder = chemin
    await db.commit()

    rapport = await project_folders.sync_user(db, current_user.id) if chemin else None
    return {**_folder_state(chemin), "report": rapport.as_dict() if rapport else None}


@router.post("/projects-folder/sync")
async def sync_projects_folder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synchronise tout de suite (sinon : automatiquement, toutes les 30 secondes)."""
    rapport = await project_folders.sync_user(db, current_user.id)
    return rapport.as_dict()
