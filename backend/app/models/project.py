import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum as SQLEnum,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class ProjectType(str, enum.Enum):
    """Types de projets possibles"""
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    RESEARCH = "research"

class ProjectStatus(str, enum.Enum):
    """Statuts possibles d'un projet"""
    IDEATION = "IDEATION"      
    PLANNING = "PLANNING"       
    ACTIVE = "ACTIVE"           
    ARCHIVED = "ARCHIVED"
    PAUSED = "PAUSED"

class Project(Base):
    """
    Modèle pour les projets
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(SQLEnum(ProjectType), nullable=False, index=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.IDEATION, nullable=False, index=True)
    
    features = Column(JSON, nullable=False, default={})
    financial_config = Column(JSON, nullable=True)

    ideation_transcript = Column(JSON, nullable=True, default=None)
    ideation_context = Column(JSON, nullable=True, default=None)
    ideation_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Score de maturité du projet (0-100)
    maturity_score = Column(Integer, default=0, nullable=False)

    # Projet tenu dans un dossier du Mac : fiche .md (chemin relatif au dossier
    # de projets de l'utilisateur) et empreinte de la dernière version importée
    source_path = Column(String(1000), nullable=True, index=True)
    source_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="project", cascade="all, delete-orphan")
    veille_topics = relationship("VeilleTopic", back_populates="project", cascade="all, delete-orphan")
    ideation_messages = relationship("IdeationMessage", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', type={self.type}, status={self.status})>"
