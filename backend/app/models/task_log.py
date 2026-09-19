"""
SQLAlchemy model for Task Logs
"""
from datetime import datetime
import enum

from sqlalchemy import (
    Column, Integer, DateTime, Enum as SQLEnum,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TaskEventType(str, enum.Enum):
    """Types d'événements trackés pour les tâches"""
    CREATED = "created"
    PROMPT_GENERATED = "prompt_generated"
    CODE_GENERATION_STARTED = "code_generation_started"
    # GENERATION_STARTED = "generation_started"  # SUPPRIMÉ - Alias inutile causant confusion avec enum DB
    CODE_GENERATED = "code_generated"
    GENERATION_FAILED = "generation_failed"  # Ajout pour orchestrator
    VALIDATED = "validated"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHANGED = "status_changed"
    COMMENT_ADDED = "comment_added"


class TaskLog(Base):
    """
    Historique complet des événements d'une tâche
    
    Permet audit trail et debugging
    """
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    event_type = Column(SQLEnum(TaskEventType), nullable=False, index=True)
    
    # Détails de l'événement (JSON flexible)
    details = Column(JSON, nullable=True, default={})
    
    # User qui a déclenché l'événement (nullable pour événements auto)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relations
    task = relationship("Task", back_populates="logs")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<TaskLog(id={self.id}, task_id={self.task_id}, event={self.event_type}, timestamp={self.timestamp})>"
