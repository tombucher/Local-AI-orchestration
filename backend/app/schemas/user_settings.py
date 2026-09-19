"""
Schemas Pydantic pour UserSettings
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserSettingsBase(BaseModel):
    """Schema de base pour UserSettings"""
    ollama_model_code: str = Field(
        default="mistral:7b-instruct-q4_K_M",
        description="Modèle Ollama pour génération de code"
    )
    ollama_model_ideation: str = Field(
        default="devstral-small-2:latest",
        description="Modèle Ollama pour idéation/brainstorming"
    )
    ollama_model_analysis: str = Field(
        default="mistral:7b-instruct-q4_K_M",
        description="Modèle Ollama pour analyse de projet"
    )
    ollama_model_task_generation: str = Field(
        default="mistral:7b-instruct-q4_K_M",
        description="Modèle Ollama pour génération de tâches"
    )
    ollama_model_text: Optional[str] = Field(
        default=None,
        description="Modèle Ollama pour génération de texte (futur)"
    )


class UserSettingsCreate(UserSettingsBase):
    """
    Schema pour créer des paramètres utilisateur

    Attributes:
        ollama_model_code: Modèle Ollama pour code
        ollama_model_ideation: Modèle Ollama pour idéation
        ollama_model_analysis: Modèle Ollama pour analyse
        ollama_model_task_generation: Modèle Ollama pour génération de tâches
        ollama_model_text: Modèle Ollama pour texte (optionnel)
    """
    pass


class UserSettingsUpdate(BaseModel):
    """
    Schema pour mettre à jour les paramètres utilisateur

    Tous les champs sont optionnels pour permettre des mises à jour partielles
    """
    ollama_model_code: Optional[str] = None
    ollama_model_ideation: Optional[str] = None
    ollama_model_analysis: Optional[str] = None
    ollama_model_task_generation: Optional[str] = None
    ollama_model_text: Optional[str] = None


class UserSettingsResponse(UserSettingsBase):
    """
    Schema de réponse pour UserSettings

    Attributes:
        id: ID des paramètres
        user_id: ID de l'utilisateur
        ollama_model_code: Modèle Ollama pour code
        ollama_model_ideation: Modèle Ollama pour idéation
        ollama_model_analysis: Modèle Ollama pour analyse
        ollama_model_task_generation: Modèle Ollama pour génération de tâches
        ollama_model_text: Modèle Ollama pour texte
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OllamaModelInfo(BaseModel):
    """
    Information sur un modèle Ollama disponible

    Attributes:
        name: Nom du modèle
        size: Taille du modèle en bytes
        modified_at: Date de dernière modification
    """
    name: str
    size: int
    modified_at: datetime
