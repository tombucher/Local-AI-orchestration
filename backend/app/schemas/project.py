"""
Pydantic schemas for Projects
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from app.models.project import ProjectType, ProjectStatus
from app.models.task import TaskType, TaskPriority


class ProjectFeatures(BaseModel):
    """Configuration des features activées pour un projet"""
    code_gen: bool = True
    veille: bool = False
    git_auto: bool = False


class FinancialConfig(BaseModel):
    """Configuration financière pour projets professionnels"""
    hourly_rate: Optional[float] = Field(None, gt=0, description="Taux horaire en EUR")
    budget: Optional[float] = Field(None, gt=0, description="Budget total en EUR")
    currency: str = Field("EUR", description="Devise")

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed = ["EUR", "USD", "CHF", "GBP"]
        if v not in allowed:
            raise ValueError(f"Currency must be one of {allowed}")
        return v


class ProjectBase(BaseModel):
    """Champs communs Project"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: ProjectType
    features: ProjectFeatures = Field(default_factory=ProjectFeatures)


class ProjectCreate(ProjectBase):
    """Schema pour création d'un projet"""
    financial_config: Optional[FinancialConfig] = None

    @field_validator('financial_config')
    @classmethod
    def validate_financial_config(cls, v: Optional[FinancialConfig], info) -> Optional[FinancialConfig]:
        """Valide que les projets PRO ont une config financière"""
        if info.data.get('type') == ProjectType.PROFESSIONAL and v is None:
            raise ValueError("Professional projects require financial_config")
        if info.data.get('type') != ProjectType.PROFESSIONAL and v is not None:
            raise ValueError("Only professional projects can have financial_config")
        return v


class ProjectUpdate(BaseModel):
    """Schema pour mise à jour d'un projet (tous champs optionnels)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[ProjectType] = None
    status: Optional[ProjectStatus] = None
    features: Optional[ProjectFeatures] = None
    financial_config: Optional[FinancialConfig] = None


class ProjectResponse(ProjectBase):
    """Schema pour réponse API avec toutes les infos"""
    id: int
    user_id: int
    status: ProjectStatus
    financial_config: Optional[FinancialConfig] = None
    created_at: datetime
    updated_at: datetime
    # Absent du schéma, le score n'atteignait jamais l'écran : la jauge affichait
    # 0/100 alors que la base contenait 90.
    maturity_score: int = 0
    # Fiche .md d'origine (projet tenu dans un dossier du Mac), sinon None
    source_path: Optional[str] = None
    # Statistiques optionnelles (pour la liste de projets)
    tasks_total: Optional[int] = None
    tasks_completed: Optional[int] = None

    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    """Statistiques d'un projet"""
    total_tasks: int
    tasks_by_status: dict[str, int]
    # Tâches ayant réellement produit un contenu : compter les statuts ne dit rien
    # de ce qui existe vraiment.
    tasks_with_output: int = 0
    tasks_by_priority: dict[str, int]
    total_time_seconds: Optional[int] = None
    estimated_cost: Optional[float] = None  # Pour projets PRO


class ProjectList(BaseModel):
    """Liste paginée de projets"""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Schemas pour le workflow "Finaliser la Vision" avec validation utilisateur
# ============================================================================

class TaskPreview(BaseModel):
    """Aperçu d'une tâche générée par l'IA (avant persistance)"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    task_type: TaskType
    priority: TaskPriority
    estimated_duration: Optional[int] = Field(None, description="Durée estimée en secondes")
    llm_prompt: Optional[str] = Field(None, description="Prompt pour génération de code")
    subtasks: List[str] = Field(default_factory=list, description="Liste de sous-tâches")


class ProjectFinalizationPreview(BaseModel):
    """Aperçu de la finalisation d'un projet (retourné par /preview-finalization)"""
    suggested_name: str = Field(..., description="Nom suggéré extrait du dialogue")
    suggested_description: str = Field(..., description="Description suggérée")
    project_type: str = Field(..., description="Type de projet (PERSONAL, PROFESSIONAL, RESEARCH)")
    tasks: List[TaskPreview] = Field(default_factory=list, description="Tâches suggérées")
    veille_keywords: List[str] = Field(default_factory=list, description="Mots-clés pour la veille")


class PreviewFinalizationRequest(BaseModel):
    """Requête pour générer un aperçu de finalisation"""
    project_id: int = Field(..., gt=0, description="ID du projet en phase IDEATION")


class TaskValidationInput(BaseModel):
    """Tâche validée/modifiée par l'utilisateur"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str
    task_type: TaskType
    priority: TaskPriority
    estimated_duration: Optional[int] = Field(None, description="Durée estimée en secondes")
    llm_prompt: Optional[str] = Field(None, description="Prompt pour génération de code")
    approved: bool = Field(..., description="True = créer la tâche, False = rejeter")


class FinalizeValidationRequest(BaseModel):
    """Requête de finalisation avec validation utilisateur"""
    project_id: int = Field(..., gt=0)
    project_name: str = Field(..., min_length=1, max_length=255)
    project_description: str
    tasks: List[TaskValidationInput] = Field(default_factory=list)
    enable_veille: bool = Field(False, description="Activer la veille automatique")
    veille_keywords: List[str] = Field(default_factory=list, description="Mots-clés pour VeilleTopic")


