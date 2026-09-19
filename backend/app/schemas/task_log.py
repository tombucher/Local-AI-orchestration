"""
Pydantic schemas for Task Logs
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.task_log import TaskEventType


class TaskLogCreate(BaseModel):
    """Schema pour création d'un log (usage interne)"""
    task_id: int
    event_type: TaskEventType
    details: Optional[dict] = None
    user_id: Optional[int] = None


class TaskLogResponse(BaseModel):
    """Schema pour réponse API"""
    id: int
    task_id: int
    event_type: TaskEventType
    timestamp: datetime
    details: Optional[dict] = None
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


class TaskLogList(BaseModel):
    """Liste de logs pour une tâche"""
    items: list[TaskLogResponse]
    total: int
