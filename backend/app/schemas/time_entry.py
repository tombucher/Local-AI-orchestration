"""
Pydantic schemas for Time Entries
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TimeEntryStart(BaseModel):
    """Schema pour démarrer un timer"""
    project_id: int = Field(..., gt=0)
    task_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = None


class TimeEntryStop(BaseModel):
    """Schema pour arrêter un timer"""
    notes: Optional[str] = None


class TimeEntryResponse(BaseModel):
    """Schema pour réponse API"""
    id: int
    project_id: int
    task_id: Optional[int] = None
    user_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TimeEntryWithDetails(TimeEntryResponse):
    """TimeEntry avec détails projet/task"""
    project_name: str
    task_title: Optional[str] = None


class TimeEntryList(BaseModel):
    """Liste paginée d'entrées de temps"""
    items: list[TimeEntryResponse]
    total: int
    page: int
    page_size: int


class TimeEntrySummary(BaseModel):
    """Résumé des temps pour un projet/période"""
    total_seconds: int
    total_hours: float
    entries_count: int
    by_task: Optional[dict[int, int]] = None  # task_id: seconds
