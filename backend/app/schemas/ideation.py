"""
Pydantic schemas for Ideation (Socratic Dialogue)
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.models.ideation_message import MessageRole


class IdeationMessageBase(BaseModel):
    """Champs de base pour un message d'idéation"""
    role: MessageRole
    content: str = Field(..., min_length=1)
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class IdeationMessageCreate(BaseModel):
    """Schema pour créer un message utilisateur"""
    content: str = Field(..., min_length=1, description="Contenu du message utilisateur")


class IdeationMessageResponse(IdeationMessageBase):
    """Schema de réponse pour un message d'idéation"""
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class IdeationConversationResponse(BaseModel):
    """Schema de réponse contenant tout l'historique de conversation"""
    project_id: int
    messages: List[IdeationMessageResponse]
    total_messages: int
    ideation_completed: bool
    ideation_completed_at: Optional[datetime] = None


class IdeationStartRequest(BaseModel):
    """Schema pour démarrer une phase d'idéation"""
    project_id: int


class IdeationStartResponse(BaseModel):
    """Schema de réponse après démarrage d'idéation"""
    project_id: int
    status: str
    welcome_message: IdeationMessageResponse
    initial_response: IdeationMessageResponse


class IdeationSendMessageRequest(BaseModel):
    """Schema pour envoyer un message dans la conversation"""
    message: str = Field(..., min_length=1)


class IdeationSendMessageResponse(BaseModel):
    """Schema de réponse après envoi d'un message"""
    user_message: IdeationMessageResponse
    assistant_message: IdeationMessageResponse


class IdeationStreamChunk(BaseModel):
    """Schema pour un chunk de streaming"""
    content: str
    done: bool = False


class IdeationCompleteRequest(BaseModel):
    """Schema pour finaliser la phase d'idéation"""
    pass  # Pas de payload nécessaire, juste l'ID du projet dans le path


class IdeationCompleteResponse(BaseModel):
    """Schema de réponse après finalisation de l'idéation"""
    project_id: int
    status: str
    ideation_completed_at: datetime
    messages_count: int
    next_step: str = "planning"


class IdeationContextExtracted(BaseModel):
    """
    Schema du contexte extrait par devstral après l'idéation.
    Correspond au format JSON attendu par l'extracteur.
    """
    project_name: Optional[str] = None
    project_type: Optional[str] = Field(
        None,
        description="professional|personal|research"
    )
    description: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    target_users: Optional[str] = None
    key_features: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(
        default_factory=lambda: {
            "technical": [],
            "temporal": None,
            "budget": None
        }
    )
    success_criteria: List[str] = Field(default_factory=list)
    scope: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "in_scope": [],
            "out_of_scope": []
        }
    )
    additional_context: Optional[str] = None
