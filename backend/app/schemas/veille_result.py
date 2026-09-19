"""
Pydantic schemas for Veille Results
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.veille_result import VeilleResultType, VeilleResultStatus


class VeilleResultResponse(BaseModel):
    """Schema pour réponse API d'un résultat de veille"""
    id: int
    topic_id: int

    # Classification
    result_type: VeilleResultType

    # Contenu principal
    title: str
    url: Optional[str] = None
    description: Optional[str] = None

    # Analyse IA
    ai_summary: Optional[str] = None
    relevance_score: float = Field(..., ge=0, le=100)
    key_points: Optional[list] = Field(default_factory=list)
    relevance_reason: Optional[str] = None

    # Échéance (appels à projets) et références visuelles
    deadline: Optional[datetime] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    license: Optional[str] = None

    # Métadonnées spécifiques au type
    metadata: Optional[dict] = Field(default_factory=dict, validation_alias="result_metadata")

    # Source et dates
    source: Optional[str] = None
    source_platform: Optional[str] = None
    published_at: Optional[datetime] = None
    found_at: datetime

    # Statut utilisateur
    status: VeilleResultStatus = VeilleResultStatus.NEW
    user_notes: Optional[str] = None
    user_rating: Optional[int] = None

    # Actions liées
    task_created: bool = False
    task_id: Optional[int] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class VeilleResultList(BaseModel):
    """Liste de résultats de veille pour une tâche"""
    items: list[VeilleResultResponse]
    total: int
    task_id: int


# --- Radar Report Schemas ---

class RadarPepite(BaseModel):
    """Une 'pépite' — résultat particulièrement pertinent"""
    name: str
    synthesis: str
    link: Optional[str] = None
    relevance_score: float = Field(..., ge=0, le=100)
    result_id: Optional[int] = None


class RadarStats(BaseModel):
    """Statistiques du scan de veille"""
    total_scanned: int
    total_relevant: int
    avg_score: float = Field(..., ge=0, le=100)
    top_sources: list[str] = Field(default_factory=list)
    scan_date: str


class RadarAffinage(BaseModel):
    """Suggestions d'affinage pour la prochaine occurrence"""
    current_keywords: list[str] = Field(default_factory=list)
    suggested_additions: list[str] = Field(default_factory=list)
    suggested_removals: list[str] = Field(default_factory=list)
    suggested_exclusions: list[str] = Field(default_factory=list)
    reasoning: str = ""


class RadarReport(BaseModel):
    """Rapport Radar complet d'une occurrence de veille"""
    pepites: list[RadarPepite] = Field(default_factory=list)
    stats: RadarStats
    affinage: RadarAffinage


class VeilleResultUpdate(BaseModel):
    """Mise à jour utilisateur d'un résultat de veille (épingler, écarter, noter)"""
    status: Optional[VeilleResultStatus] = None
    user_notes: Optional[str] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)


class VeilleRefineRequest(BaseModel):
    """Requête d'affinage de veille par l'utilisateur"""
    add_keywords: list[str] = Field(default_factory=list)
    remove_keywords: list[str] = Field(default_factory=list)
    add_excluded: list[str] = Field(default_factory=list)
    remove_excluded: list[str] = Field(default_factory=list)
    user_notes: Optional[str] = None
