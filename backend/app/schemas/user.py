"""
Schemas Pydantic pour User et Auth
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Schema de base pour User"""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """
    Schema pour créer un nouvel utilisateur
    
    Attributes:
        email: Email de l'utilisateur
        password: Mot de passe en clair (sera hashé)
        full_name: Nom complet optionnel
    """
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """
    Schema pour login
    
    Attributes:
        email: Email de l'utilisateur
        password: Mot de passe en clair
    """
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """
    Schema de réponse pour User (sans mot de passe)
    
    Attributes:
        id: ID de l'utilisateur
        email: Email
        full_name: Nom complet
        is_active: Compte actif
        is_superuser: Utilisateur admin
        created_at: Date de création
        updated_at: Date de dernière modification
    """
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Auth Schemas
# ============================================================================

class Token(BaseModel):
    """
    Schema pour la réponse de login
    
    Attributes:
        access_token: Token JWT
        token_type: Type de token (bearer)
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema pour les données du token
    
    Attributes:
        user_id: ID de l'utilisateur
    """
    user_id: Optional[int] = None