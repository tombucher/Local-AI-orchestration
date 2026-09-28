"""
Schemas pour le dialogue unifié de création de projet

Ce module permet de créer un projet directement via un dialogue,
sans passer par le formulaire traditionnel.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class StartProjectChatRequest(BaseModel):
    """Requête pour démarrer un dialogue de création de projet"""
    # Espace de l'onglet d'où l'on crée le projet (Recherche, Mairie…), facultatif
    space: Optional[str] = Field(None, max_length=120)

    @field_validator('space')
    @classmethod
    def valider_espace(cls, v: Optional[str]) -> Optional[str]:
        from app.schemas.project import _espace_valide
        return _espace_valide(v)


class StartProjectChatResponse(BaseModel):
    """Réponse au démarrage du dialogue"""
    project_id: int
    conversation_id: int  # ID de la conversation d'idéation
    welcome_message: str
    initial_question: str

    model_config = {"from_attributes": True}


class FinalizeProjectRequest(BaseModel):
    """Requête pour finaliser le projet et générer les tâches"""
    project_id: int


class TaskGenerated(BaseModel):
    """Représentation d'une tâche générée"""
    id: int
    title: str
    description: str
    task_type: str
    priority: str
    estimated_duration: Optional[int] = None

    model_config = {"from_attributes": True}


class FinalizeProjectResponse(BaseModel):
    """Réponse à la finalisation du projet"""
    project_id: int
    project_name: str
    project_description: str
    tasks_count: int
    tasks: List[TaskGenerated]
    message: str

    model_config = {"from_attributes": True}
