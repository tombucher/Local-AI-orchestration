"""
SQLAlchemy model for Time Entries
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, DateTime, Text,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TimeEntry(Base):
    """
    Entrées de temps pour projets professionnels
    
    Permet tracking précis du temps passé sur projets/tâches
    Un seul timer actif (ended_at=NULL) par user à la fois
    """
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)  # NULL = timer en cours
    
    # Calculé lors de l'arrêt du timer
    duration_seconds = Column(Integer, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    project = relationship("Project", back_populates="time_entries")
    task = relationship("Task", back_populates="time_entries")
    user = relationship("User", back_populates="time_entries")

    def __repr__(self) -> str:
        status = "running" if self.ended_at is None else f"{self.duration_seconds}s"
        return f"<TimeEntry(id={self.id}, project_id={self.project_id}, status={status})>"
