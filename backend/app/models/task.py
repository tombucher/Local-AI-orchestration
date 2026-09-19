"""
SQLAlchemy model for Tasks
"""
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum as SQLEnum,
    ForeignKey, JSON, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TaskType(str, enum.Enum):
    """Types de tâches selon le domaine"""
    CODE_GENERATION = "code_generation"      # Génération de code
    DOCUMENT_WRITING = "document_writing"    # Rédaction de documents
    FUNDING_SEARCH = "funding_search"        # Recherche de financements
    VEILLE = "veille"                        # Veille récurrente (type unifié)
    VEILLE_TECH = "veille_tech"             # DEPRECATED — gardé pour compat DB
    VEILLE_CULTURAL = "veille_cultural"      # DEPRECATED — gardé pour compat DB
    VEILLE_EVENTS = "veille_events"          # DEPRECATED — gardé pour compat DB
    ADMINISTRATIVE = "administrative"        # Tâches administratives
    RESEARCH = "research"                    # Recherche générique


class TaskPriority(str, enum.Enum):
    """Niveaux de priorité des tâches"""
    P1 = "P1"  # Urgent/Critique
    P2 = "P2"  # Important
    P3 = "P3"  # Normal


class TaskStatus(str, enum.Enum):
    """
    Machine à états des tâches
    
    Workflow:
    CREATED → READY → GENERATING → MANUAL_REVIEW → COMPLETED
                                  ↓
                                FAILED → READY (retry)
                                  ↓
                              CANCELLED
    """
    CREATED = "created"              # Créée, prompt manuel
    READY = "ready"                  # Prête pour génération
    GENERATING = "generating"        # Génération code en cours
    MANUAL_REVIEW = "manual_review"  # Code généré, attente validation
    COMPLETED = "completed"          # Validée et terminée
    FAILED = "failed"                # Échec génération
    CANCELLED = "cancelled"          # Annulée par user


# Table d'association pour les dépendances entre tâches
task_dependencies = Table(
    "task_dependencies",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("depends_on_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True,
)

class Task(Base):
    """
    Modèle pour les tâches

    Gère le workflow complet de génération de code avec validation humaine
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Type de tâche (détermine quel agent la traite)
    task_type = Column(SQLEnum(TaskType, values_callable=lambda x: [e.value for e in x]), default=TaskType.CODE_GENERATION, nullable=False, index=True)

    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.P2, nullable=False, index=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.CREATED, nullable=False, index=True)
    
    # Contenu généré
    llm_prompt = Column(Text, nullable=True)           # Prompt pour génération
    generated_code = Column(Text, nullable=True)       # Code généré par LLM
    validation_notes = Column(Text, nullable=True)     # Notes lors validation
    
    # Métriques
    estimated_duration = Column(Integer, nullable=True)  # Estimation en secondes
    actual_duration = Column(Integer, nullable=True)     # Durée réelle en secondes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)      # Début génération
    completed_at = Column(DateTime(timezone=True), nullable=True)    # Fin complète
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)  # Échéance (Gantt, nudges)
    
    # Retry
    retry_count = Column(Integer, nullable=False, server_default='0', default=0)
    last_failed_at = Column(DateTime(timezone=True), nullable=True)

    # Métadonnées flexibles
    task_metadata = Column("metadata", JSON, nullable=True, server_default='{}')  # Données additionnelles

    # Veille — rapport Radar structuré et lien vers le topic récurrent
    radar_report = Column(JSON, nullable=True)  # Rapport Radar JSON (pépites, stats, affinage)
    veille_topic_id = Column(Integer, ForeignKey("veille_topics.id", ondelete="SET NULL"), nullable=True)

    # Relations
    project = relationship("Project", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="task")
    veille_topic = relationship("VeilleTopic", foreign_keys=[veille_topic_id])

    # Relations de dépendances
    dependencies = relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin="Task.id == task_dependencies.c.task_id",
        secondaryjoin="Task.id == task_dependencies.c.depends_on_id",
        backref="dependent_tasks",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', priority={self.priority}, status={self.status})>"
