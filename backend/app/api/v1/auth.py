"""
Endpoints d'authentification
"""
import time
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_active_user, get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Créer un nouveau compte utilisateur
    
    Args:
        user_in: Données de création de l'utilisateur
        db: Session de base de données
        
    Returns:
        User créé
        
    Raises:
        HTTPException: Si l'email existe déjà
    """
    # Vérifier si l'email existe déjà
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Créer le nouvel utilisateur
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
        is_superuser=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


# Anti-brute-force : tentatives échouées par IP (mémoire process, suffisant en mono-instance)
_LOGIN_MAX_FAILURES = 10
_LOGIN_WINDOW_SECONDS = 15 * 60
_login_failures: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )


def _check_login_allowed(ip: str) -> None:
    now = time.time()
    recent = [t for t in _login_failures.get(ip, []) if now - t < _LOGIN_WINDOW_SECONDS]
    _login_failures[ip] = recent
    if len(recent) >= _LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives de connexion. Réessaie dans quelques minutes.",
        )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login avec email et mot de passe
    
    Args:
        credentials: Email et mot de passe
        db: Session de base de données
        
    Returns:
        Token JWT
        
    Raises:
        HTTPException: Si les credentials sont invalides
    """
    ip = _client_ip(request)
    _check_login_allowed(ip)

    # Récupérer l'utilisateur
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Vérifier l'utilisateur et le mot de passe
    if not user or not verify_password(credentials.password, user.hashed_password):
        _login_failures.setdefault(ip, []).append(time.time())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Créer le token
    access_token = create_access_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Récupérer les informations de l'utilisateur actuel
    
    Args:
        current_user: Utilisateur authentifié
        
    Returns:
        Informations de l'utilisateur
    """
    return current_user
