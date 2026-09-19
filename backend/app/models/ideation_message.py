"""
SQLAlchemy model for Ideation Messages
Stocke l'historique des conversations socratiques avec l'IA
"""
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum as SQLEnum,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MessageRole(str, enum.Enum):
    """Rôles possibles dans le dialogue d'idéation"""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"  # Pour les messages système éventuels


class IdeationMessage(Base):
    """
    Modèle pour les messages du dialogue d'idéation socratique.

    Chaque message représente un échange dans la conversation
    entre l'utilisateur et l'IA pendant la phase d'idéation.
    """
    __tablename__ = "ideation_messages"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contenu du message
    role = Column(SQLEnum(MessageRole), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Métadonnées optionnelles (pour tracking et debugging)
    meta = Column(JSON, nullable=True, default={})
    # Exemple de meta:
    # {
    #   "model": "mistral:7b-instruct-q4_K_M",
    #   "temperature": 0.7,
    #   "tokens_used": 250,
    #   "response_time_ms": 1500
    # }

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relations
    project = relationship("Project", back_populates="ideation_messages")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<IdeationMessage(id={self.id}, role={self.role}, content='{preview}')>"
