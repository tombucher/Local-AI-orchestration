"""
SQLAlchemy model for Veille Results (monitoring results)
"""
from datetime import datetime
import enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum as SQLEnum,
    ForeignKey, JSON, Float, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class VeilleResultType(str, enum.Enum):
    """Types de résultats de veille"""
    FUNDING_OPPORTUNITY = "funding_opportunity"     # Opportunité de financement
    TECH_ARTICLE = "tech_article"                  # Article technique
    TECH_TOOL = "tech_tool"                        # Outil/bibliothèque
    EVENT = "event"                                # Festival, exposition, conférence
    COLLABORATION = "collaboration"                # Opportunité de collaboration
    ACADEMIC_PAPER = "academic_paper"              # Publication scientifique
    NEWS_ARTICLE = "news_article"                  # Article d'actualité
    ARTIST_WORK = "artist_work"                    # Œuvre/travail d'artiste
    CALL_FOR_PROPOSALS = "call_for_proposals"      # Appel à projets/résidence
    VISUAL_REFERENCE = "visual_reference"          # Référence visuelle (image, moodboard)


class VeilleResultStatus(str, enum.Enum):
    """Statut d'un résultat de veille côté utilisateur"""
    NEW = "new"              # Nouveau, non lu
    READ = "read"            # Lu
    SAVED = "saved"          # Sauvegardé/favoris
    ACTIONABLE = "actionable"  # À traiter (ex: dossier à remplir)
    DISMISSED = "dismissed"  # Écarté


class VeilleResult(Base):
    """
    Résultat d'une veille automatique

    Stocke les opportunités/contenus trouvés par les agents de veille,
    avec analyse IA de pertinence et extraction d'informations clés
    """
    __tablename__ = "veille_results"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("veille_topics.id", ondelete="CASCADE"), nullable=False, index=True)

    # Classification
    result_type = Column(SQLEnum(VeilleResultType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)

    # Contenu principal
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)

    # Analyse IA
    ai_summary = Column(Text, nullable=True)              # Résumé généré par LLM
    relevance_score = Column(Float, nullable=False)       # 0-100 (calculé par LLM)
    key_points = Column(JSON, nullable=True, default=[])  # Points clés extraits
    relevance_reason = Column(Text, nullable=True)        # Pourquoi c'est pertinent

    # Échéance extraite (appels à projets) — triable
    deadline = Column(DateTime(timezone=True), nullable=True, index=True)

    # Références visuelles (moodboard)
    image_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    license = Column(String(100), nullable=True)

    # Métadonnées spécifiques au type
    result_metadata = Column("metadata", JSON, nullable=True, default={})
    # Exemples:
    # - FUNDING: {"amount": 50000, "deadline": "2026-06-01", "eligibility": [...], "documents_required": [...]}
    # - EVENT: {"date": "2026-05-15", "location": "Paris", "type": "festival", "submission_deadline": "2026-03-01"}
    # - TECH: {"github_stars": 1500, "last_commit": "2026-01-01", "language": "Python"}
    # - ARTIST_WORK: {"artist_name": "John Doe", "medium": "installation", "themes": ["data", "ecology"]}

    # Source et dates
    source = Column(String(255), nullable=True)
    source_platform = Column(String(100), nullable=True)  # "data.gouv.fr", "GitHub", etc.
    published_at = Column(DateTime(timezone=True), nullable=True)
    found_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Statut utilisateur
    status = Column(SQLEnum(VeilleResultStatus, values_callable=lambda x: [e.value for e in x]), default=VeilleResultStatus.NEW, nullable=False, index=True)
    user_notes = Column(Text, nullable=True)
    user_rating = Column(Integer, nullable=True)  # 1-5 pour feedback utilisateur

    # Actions liées
    task_created = Column(Boolean, default=False)  # True si une tâche a été créée depuis ce résultat
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    topic = relationship("VeilleTopic", back_populates="results")
    task = relationship("Task")

    def __repr__(self) -> str:
        return f"<VeilleResult(id={self.id}, type={self.result_type}, title='{self.title[:50]}...', score={self.relevance_score})>"
