"""
Schemas pour l'analyse intelligente de projets.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.task import TaskType, TaskPriority


# ============================================================
# SCHEMAS POUR L'ANALYSE DE PROJET
# ============================================================

class SubTaskSchema(BaseModel):
    """Sous-tâche dans une checklist."""
    description: str
    estimated_hours: Optional[int] = None


class TaskSuggestionSchema(BaseModel):
    """Suggestion de tâche générée par l'IA."""
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    estimated_duration: Optional[int] = None
    subtasks: List[str] = Field(default_factory=list)
    llm_prompt: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    dependency_titles: List[str] = Field(default_factory=list)


class VeilleSuggestionSchema(BaseModel):
    """Suggestion de veille automatique."""
    scope: str
    keywords: List[str]
    scan_frequency: str
    reason: str


class BlockerSchema(BaseModel):
    """Blocage détecté."""
    type: str
    description: str
    severity: str
    suggestion: str


class ProjectAnalysisResponse(BaseModel):
    """Résultat complet de l'analyse d'un projet."""
    project_id: int
    analyzed_at: datetime
    summary: str
    task_suggestions: List[TaskSuggestionSchema] = Field(default_factory=list)
    veille_suggestions: List[VeilleSuggestionSchema] = Field(default_factory=list)
    blockers: List[BlockerSchema] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    estimated_total_hours: Optional[int] = None

    class Config:
        from_attributes = True


class CreateTasksRequest(BaseModel):
    """Requête pour créer des tâches à partir de suggestions.

    Le frontend envoie les suggestions complètes (`tasks`/`veille`) obtenues
    via /analyze. `task_indices` est l'ancien mode (relançait toute l'analyse,
    non déterministe) conservé en fallback.
    """
    tasks: Optional[List[TaskSuggestionSchema]] = None
    veille: Optional[List[VeilleSuggestionSchema]] = None
    task_indices: Optional[List[int]] = Field(
        default=None, description="(déprécié) Indices des tâches à créer (0-based)"
    )


class CreateTasksResponse(BaseModel):
    """Réponse après création de tâches."""
    created_count: int
    task_ids: List[int]
    message: str


class RefineTaskRequest(BaseModel):
    """Requête pour raffiner une tâche avec l'IA."""
    task_data: TaskSuggestionSchema
    user_prompt: str = Field(..., description="Instructions pour raffiner la tâche")


class RefineTaskResponse(BaseModel):
    """Réponse après raffinement de tâche."""
    refined_task: TaskSuggestionSchema
