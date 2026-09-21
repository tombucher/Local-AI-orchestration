"""Schémas Pydantic pour l'espace documents d'un projet."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.project_document import DocumentKind


class DocumentTextCreate(BaseModel):
    """Dépôt d'une note ou d'un extrait de code collé directement."""

    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    kind: DocumentKind = DocumentKind.TEXT
    note: Optional[str] = Field(None, max_length=500)


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    note: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    content: Optional[str] = None


class DocumentResponse(BaseModel):
    """Le contenu n'est pas renvoyé dans la liste : un extrait suffit à l'affichage."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    kind: DocumentKind
    mime_type: str
    note: Optional[str] = None
    enabled: bool
    size_bytes: int
    created_at: datetime
    excerpt: Optional[str] = None   # premiers caractères, pour la liste
    has_image: bool = False


class DocumentDetail(DocumentResponse):
    """Réponse complète, avec le contenu textuel intégral."""

    content: Optional[str] = None
