"""
SQLAlchemy model for Veille Topics (monitoring topics)
"""
from datetime import datetime, timedelta
import enum

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum as SQLEnum,
    ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class VeilleScope(str, enum.Enum):
    """Types de veille possibles"""
    TECH = "tech"                    # Veille technologique (GitHub, Stack Overflow, HN)
    FUNDING = "funding"              # Appels d'offres, subventions, financements
    CULTURAL = "cultural"            # Festivals, expositions, événements artistiques
    ACADEMIC = "academic"            # Publications scientifiques, recherche
    NEWS = "news"                    # Actualités généralistes
    COLLABORATION = "collaboration"  # Opportunités de partenariat
    VISUAL = "visual"                # Références visuelles / moodboard (images)


class VeilleTopic(Base):
    """
    Sujet de veille configuré par projet

    Permet de surveiller automatiquement différents types de contenus
    selon les besoins du projet (tech, financements, culture, etc.)
    """
    __tablename__ = "veille_topics"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Identification
    name = Column(String(255), nullable=False)  # "Financements culture numérique"
    scope = Column(SQLEnum(VeilleScope, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    description = Column(String(500), nullable=True)

    # Configuration de recherche
    keywords = Column(JSON, nullable=False, default=[])  # ["compostage", "art numérique"]
    excluded_keywords = Column(JSON, nullable=True, default=[])  # ["compost physique"]

    # Filtres géographiques/temporels
    location_filters = Column(JSON, nullable=True)  # {"country": "FR", "region": "IDF", "radius_km": 100}
    date_filters = Column(JSON, nullable=True)      # {"min_date": "2026-01-01", "max_date": "2026-12-31"}

    # Sources spécifiques (URLs, APIs, feeds RSS)
    sources = Column(JSON, nullable=True, default=[])  # ["artsy.net", "culture.gouv.fr"]

    # Configuration de scan
    scan_frequency = Column(String(50), nullable=False, default="weekly")  # daily, weekly, monthly
    min_relevance_score = Column(Integer, default=60)  # Seuil de pertinence 0-100

    # Scheduling
    last_scan = Column(DateTime(timezone=True), nullable=True)
    next_scan = Column(DateTime(timezone=True), nullable=True)

    # Statut
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Historique des affinages utilisateur
    refinement_history = Column(JSON, nullable=True, server_default='[]')

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    project = relationship("Project", back_populates="veille_topics")
    results = relationship("VeilleResult", back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<VeilleTopic(id={self.id}, name='{self.name}', scope={self.scope}, enabled={self.enabled})>"

    def calculate_next_scan(self) -> datetime:
        """Calcule la prochaine date de scan selon la fréquence"""
        now = datetime.utcnow()

        if self.scan_frequency == "daily":
            return now + timedelta(days=1)
        elif self.scan_frequency == "weekly":
            return now + timedelta(weeks=1)
        elif self.scan_frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(weeks=1)  # Default: weekly
