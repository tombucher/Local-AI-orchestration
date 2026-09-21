"""
Documents attachés à un projet : notes, code, spécifications, images de référence.

Le carnet de projet (`project_memory`) ne sait que ce que la base contient déjà.
Ces documents sont le moyen de lui donner ce qu'elle ne peut pas deviner : une
charte, un cahier des charges, un extrait de code existant, une image de référence.

Les images sont conservées telles quelles : les modèles installés (qwen3.8, gemma4)
annoncent la capacité `vision`, elles peuvent donc être envoyées au modèle.
Les PDF sont volontairement hors périmètre — l'extraction coûte trop cher en local.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, LargeBinary, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentKind(str, enum.Enum):
    """Nature du document, qui détermine comment il est donné au modèle."""

    TEXT = "text"      # note, spécification, markdown — injecté tel quel
    CODE = "code"      # extrait de code — injecté dans un bloc, langage déduit
    IMAGE = "image"    # référence visuelle — envoyée aux modèles dotés de vision


class ProjectDocument(Base):
    """Document de référence rattaché à un projet."""

    __tablename__ = "project_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[DocumentKind] = mapped_column(
        SQLEnum(DocumentKind, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=DocumentKind.TEXT, index=True,
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="text/plain")

    # Texte et code : le contenu lisible. Images : None.
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Images uniquement : les octets bruts, encodés en base64 au moment de l'envoi.
    binary: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Ce que l'utilisateur veut que le modèle en retienne ; sert aussi de résumé
    # dans le carnet de projet quand le document est trop gros pour être injecté.
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Désactiver un document sans le supprimer (essai, version périmée…)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project = relationship("Project")

    @property
    def is_image(self) -> bool:
        return self.kind == DocumentKind.IMAGE

    def __repr__(self) -> str:
        return f"<ProjectDocument(id={self.id}, kind={self.kind.value}, name='{self.name[:30]}')>"
