"""
Pydantic schemas for Tasks
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus, TaskType


class TaskBase(BaseModel):
    """Champs communs Task"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.P2


class TaskCreate(TaskBase):
    """Schema pour création d'une tâche"""
    project_id: int = Field(..., gt=0)
    task_type: TaskType = TaskType.CODE_GENERATION  # Type de tâche avec valeur par défaut
    llm_prompt: Optional[str] = None
    estimated_duration: Optional[int] = Field(None, gt=0, description="Durée estimée en secondes")
    due_date: Optional[datetime] = None
    metadata: Optional[dict] = Field(default_factory=dict)
    dependency_ids: list[int] = Field(default_factory=list, description="IDs des tâches dont cette tâche dépend")


class TaskUpdate(BaseModel):
    """Schema pour mise à jour d'une tâche (tous champs optionnels)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    llm_prompt: Optional[str] = None
    generated_code: Optional[str] = None
    validation_notes: Optional[str] = None
    estimated_duration: Optional[int] = Field(None, gt=0)
    due_date: Optional[datetime] = None
    metadata: Optional[dict] = Field(default_factory=dict)
    dependency_ids: Optional[list[int]] = Field(default_factory=list, description="IDs des tâches dont cette tâche dépend")


class TaskValidate(BaseModel):
    """Schema pour validation de code généré"""
    approved: bool
    notes: Optional[str] = None
    edited_code: Optional[str] = None  # Code modifié par l'utilisateur (édition inline)


class TaskResponse(TaskBase):
    """Schema pour réponse API avec toutes les infos"""
    id: int
    project_id: int
    project_name: Optional[str] = None  # Nom du projet (pour affichage)
    task_type: TaskType = TaskType.CODE_GENERATION
    status: TaskStatus
    llm_prompt: Optional[str] = None
    generated_code: Optional[str] = None
    validation_notes: Optional[str] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    retry_count: int = 0
    last_failed_at: Optional[datetime] = None
    metadata: Optional[dict] = Field(default_factory=dict, validation_alias="task_metadata")
    dependencies: list[int] = Field(default_factory=list, description="IDs des tâches dont cette tâche dépend")

    # Veille
    radar_report: Optional[dict] = None
    veille_topic_id: Optional[int] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class TaskWithProject(TaskResponse):
    """Task avec infos projet incluses"""
    project_name: str
    project_type: str


class TaskList(BaseModel):
    """Liste paginée de tâches"""
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
