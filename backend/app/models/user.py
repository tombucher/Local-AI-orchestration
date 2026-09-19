"""
Modèle User pour SQLAlchemy
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    Modèle utilisateur
    
    Attributes:
        id: ID unique de l'utilisateur
        email: Email (unique, utilisé pour login)
        hashed_password: Mot de passe hashé avec bcrypt
        full_name: Nom complet de l'utilisateur
        is_active: Compte actif ou désactivé
        is_superuser: Utilisateur admin
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )
    
    is_superuser: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
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

    # Relations
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    time_entries: Mapped[List["TimeEntry"]] = relationship("TimeEntry", back_populates="user", cascade="all, delete-orphan")
    settings: Mapped[Optional["UserSettings"]] = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    daily_reports: Mapped[List["DailyReport"]] = relationship("DailyReport", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
