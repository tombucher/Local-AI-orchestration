"""
API endpoints for Ideation (Socratic Dialogue)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Project, ProjectStatus
from app.schemas import (
    IdeationMessageResponse, IdeationConversationResponse,
    IdeationStartRequest, IdeationStartResponse,
    IdeationSendMessageRequest, IdeationSendMessageResponse,
    IdeationCompleteResponse
)
from app.services.ideation_service import IdeationService

router = APIRouter()


@router.post("/start", response_model=IdeationStartResponse, status_code=status.HTTP_201_CREATED)
async def start_ideation(
    request: IdeationStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Démarre la phase d'idéation socratique pour un projet.

    Le projet doit être en statut IDEATION pour démarrer.
    Retourne un message de bienvenue système pour guider l'utilisateur.

    Args:
        request: Contient l'ID du projet
        current_user: Utilisateur authentifié
        db: Session de base de données

    Returns:
        Message de bienvenue et statut du projet

    Raises:
        404: Si le projet n'existe pas ou n'appartient pas à l'utilisateur
        400: Si le projet n'est pas en statut IDEATION
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    if project.status != ProjectStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in IDEATION status. Current status: {project.status}"
        )

    # Démarrer l'idéation (génère automatiquement la première réponse de l'IA)
    service = IdeationService(db, user_id=current_user.id)
    result = await service.start_ideation(request.project_id)

    return IdeationStartResponse(
        project_id=request.project_id,
        status="ideation_started",
        welcome_message=IdeationMessageResponse.model_validate(result["welcome_message"]),
        initial_response=IdeationMessageResponse.model_validate(result["initial_response"])
    )


@router.get("/conversation/{project_id}", response_model=IdeationConversationResponse)
async def get_conversation(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère l'historique complet de la conversation d'idéation d'un projet.

    Args:
        project_id: ID du projet
        current_user: Utilisateur authentifié
        db: Session de base de données

    Returns:
        Historique complet des messages avec métadonnées

    Raises:
        404: Si le projet n'existe pas ou n'appartient pas à l'utilisateur
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Récupérer l'historique
    service = IdeationService(db, user_id=current_user.id)
    messages = await service.get_conversation_history(project_id)

    # Convertir en schemas de réponse
    message_responses = [
        IdeationMessageResponse.model_validate(msg) for msg in messages
    ]

    return IdeationConversationResponse(
        project_id=project_id,
        messages=message_responses,
        total_messages=len(message_responses),
        ideation_completed=project.ideation_completed_at is not None,
        ideation_completed_at=project.ideation_completed_at
    )


@router.post("/send/{project_id}", response_model=IdeationSendMessageResponse)
async def send_message(
    project_id: int,
    request: IdeationSendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Envoie un message utilisateur et génère une réponse de l'assistant.
    Version NON-STREAMING (retourne la réponse complète).

    Args:
        project_id: ID du projet
        request: Contient le message utilisateur
        current_user: Utilisateur authentifié
        db: Session de base de données

    Returns:
        Le message utilisateur et la réponse de l'assistant

    Raises:
        404: Si le projet n'existe pas
        400: Si le projet n'est pas en statut IDEATION
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    if project.status != ProjectStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in IDEATION status. Current status: {project.status}"
        )

    # Envoyer le message et générer la réponse
    service = IdeationService(db, user_id=current_user.id)

    # 1. Sauvegarder le message utilisateur
    user_message = await service.send_user_message(project_id, request.message)

    # 2. Générer la réponse de l'assistant (non-streaming)
    assistant_message = await service.generate_assistant_response(project_id)

    return IdeationSendMessageResponse(
        user_message=IdeationMessageResponse.model_validate(user_message),
        assistant_message=IdeationMessageResponse.model_validate(assistant_message)
    )


@router.post("/send-stream/{project_id}")
async def send_message_stream(
    project_id: int,
    request: IdeationSendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Envoie un message utilisateur et stream la réponse de l'assistant.
    Version STREAMING pour interface fluide.

    Args:
        project_id: ID du projet
        request: Contient le message utilisateur
        current_user: Utilisateur authentifié
        db: Session de base de données

    Returns:
        Stream de chunks de texte (Server-Sent Events)

    Raises:
        404: Si le projet n'existe pas
        400: Si le projet n'est pas en statut IDEATION
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    if project.status != ProjectStatus.IDEATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in IDEATION status. Current status: {project.status}"
        )

    # Envoyer le message utilisateur (non-async ici, juste sauvegarder)
    service = IdeationService(db, user_id=current_user.id)
    await service.send_user_message(project_id, request.message)

    # Créer le générateur pour le streaming
    async def stream_generator():
        """Générateur pour streamer les chunks de réponse"""
        async for chunk in service.generate_assistant_response_stream(project_id):
            # Format Server-Sent Events (SSE)
            yield f"data: {chunk}\n\n"

        # Signal de fin
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/complete/{project_id}", response_model=IdeationCompleteResponse)
async def complete_ideation(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalise la phase d'idéation et passe le projet en statut PLANNING.

    Cette action:
    1. Sauvegarde le transcript complet en cache (project.ideation_transcript)
    2. Change le statut du projet vers PLANNING
    3. Enregistre la date de complétion

    Args:
        project_id: ID du projet
        current_user: Utilisateur authentifié
        db: Session de base de données

    Returns:
        Confirmation de la finalisation

    Raises:
        404: Si le projet n'existe pas
        400: Si le projet n'est pas en statut IDEATION
    """
    # Vérifier que le projet existe et appartient à l'utilisateur
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    if project.status not in [ProjectStatus.IDEATION, ProjectStatus.PLANNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in IDEATION or PLANNING status to complete. Current status: {project.status}"
        )

    # Finaliser l'idéation
    service = IdeationService(db, user_id=current_user.id)
    messages = await service.get_conversation_history(project_id)
    updated_project = await service.complete_ideation(project_id)

    return IdeationCompleteResponse(
        project_id=project_id,
        status=updated_project.status.value,
        ideation_completed_at=updated_project.ideation_completed_at,
        messages_count=len(messages),
        next_step="planning"
    )
