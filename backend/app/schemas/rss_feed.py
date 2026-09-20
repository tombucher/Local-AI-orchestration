"""Schémas Pydantic pour la bibliothèque de flux RSS."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RssFeedCreate(BaseModel):
    """Ajout d'un flux. Les étiquettes sont déduites si elles ne sont pas fournies."""

    url: str = Field(..., min_length=8, max_length=1000)
    title: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None

    @field_validator("url")
    @classmethod
    def normalise_url(cls, v: str) -> str:
        v = v.strip()
        if not v.lower().startswith(("http://", "https://")):
            v = "https://" + v
        return v


class RssFeedUpdate(BaseModel):
    """Modification d'un flux existant (tous les champs sont optionnels)."""

    title: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


class RssFeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    tags: List[str] = []
    enabled: bool
    last_checked: Optional[datetime] = None
    last_status: Optional[str] = None
    last_entry_count: int = 0
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def none_to_list(cls, v):
        return v or []


class FeedCheckResult(BaseModel):
    """Résultat d'une vérification de flux, avant ou après enregistrement."""

    ok: bool
    status: str
    title: str = ""
    tags: List[str] = []
    entry_count: int = 0
    sample: List[str] = []
