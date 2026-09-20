"""
Bibliothèque de flux RSS de l'utilisateur.

Un catalogue de flux codé en dur ne peut pas couvrir des projets arbitraires :
c'est l'utilisateur qui ajoute les sources qu'il découvre au fil de ses recherches.
Chaque flux est vérifié à l'ajout (le flux existe-t-il, a-t-il des entrées ?) et
ses étiquettes sont déduites de son contenu, pour que la veille puisse choisir
les bonnes sources selon le sujet.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RssFeed(Base):
    """Flux RSS/Atom enregistré par un utilisateur."""

    __tablename__ = "rss_feeds"
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_rss_feeds_user_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    # Titre annoncé par le flux ; l'utilisateur peut le remplacer
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Étiquettes déduites du contenu (et éditables) : servent au choix des sources
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Dernière vérification : évite de garder un flux mort sans le savoir
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_entry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def is_healthy(self) -> bool:
        return self.last_status == "ok" and self.last_entry_count > 0

    def __repr__(self) -> str:
        return f"<RssFeed(id={self.id}, url='{self.url[:40]}', status={self.last_status})>"
