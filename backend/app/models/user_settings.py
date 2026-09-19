"""
Modèle UserSettings pour stocker les préférences utilisateur
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, func, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserSettings(Base):
    """
    Paramètres utilisateur pour la configuration de l'application

    Attributes:
        id: ID unique
        user_id: ID de l'utilisateur (FK)
        ollama_model_code: Modèle Ollama pour génération de code
        ollama_model_text: Modèle Ollama pour génération de texte (futur)
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # Un seul settings par user
        nullable=False,
        index=True
    )

    # Modèles Ollama spécifiques par type de tâche
    ollama_model_code: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="mistral:7b-instruct-q4_K_M"
    )

    ollama_model_ideation: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="devstral-small-2:latest"
    )

    ollama_model_analysis: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="mistral:7b-instruct-q4_K_M"
    )

    ollama_model_task_generation: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="mistral:7b-instruct-q4_K_M"
    )

    # Modèle Ollama pour génération de texte (pour futur usage)
    ollama_model_text: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relation
    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id}, model={self.ollama_model_code})>"
