"""
Configuration de la base de données avec SQLAlchemy 2.0
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# Convertir postgresql:// en postgresql+asyncpg://
SQLALCHEMY_DATABASE_URL = str(settings.DATABASE_URL).replace(
    "postgresql://", "postgresql+asyncpg://"
)


# Créer le moteur async avec connection pooling
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    # echo découplé de DEBUG : l'écho SQL noie les logs applicatifs
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias pour compatibilité avec le code existant
async_session_maker = AsyncSessionLocal


# Base déclarative pour les modèles
class Base(DeclarativeBase):
    """Base class pour tous les modèles SQLAlchemy"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency pour obtenir une session de base de données
    
    Yields:
        AsyncSession: Session de base de données
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialise la base de données (crée les tables)
    
    Note:
        En production, utiliser Alembic pour les migrations
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
