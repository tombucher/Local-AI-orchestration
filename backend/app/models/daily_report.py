"""
Modèle pour les rapports quotidiens.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship

from app.core.database import Base


class DailyReport(Base):
    """Rapport quotidien généré automatiquement chaque matin."""

    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)  # Date du rapport (sans heure)

    # Résumé généré par l'IA
    summary = Column(Text, nullable=False)

    # Statistiques globales
    total_projects = Column(Integer, default=0)
    active_projects = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_today = Column(Integer, default=0)
    blockers_count = Column(Integer, default=0)

    # Données structurées en JSON
    projects_analysis = Column(JSON)  # Liste des ProjectStatus
    top_priorities = Column(JSON)  # Liste des 3 actions prioritaires
    recommendations = Column(JSON)  # Liste des recommandations

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    user = relationship("User", back_populates="daily_reports")

    def __repr__(self):
        return f"<DailyReport(id={self.id}, user_id={self.user_id}, date={self.date})>"
