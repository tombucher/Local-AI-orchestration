"""
Configuration de la base de données avec SQLAlchemy 2.0
"""
import logging
from pathlib import Path
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


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


async def check_db_schema() -> None:
    """Compare le schéma en base à la dernière migration Alembic.

    Remplace l'ancien `create_all` au démarrage : celui-ci créait les tables des
    nouveaux modèles avant qu'Alembic ne passe, si bien que chaque migration
    échouait ensuite sur « table already exists » et que le schéma réel pouvait
    diverger des migrations sans que rien ne le signale.

    Ne crée plus rien : se contente de prévenir, et n'empêche jamais le démarrage
    (l'application peut être lancée avant la première migration).
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    try:
        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        head = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception as e:
        logger.debug(f"Impossible de lire les migrations Alembic : {e}")
        return

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar()
    except Exception:
        logger.warning(
            "⚠️ Base non initialisée (table alembic_version absente). "
            "Lance : docker compose exec backend alembic upgrade head"
        )
        return

    if current == head:
        logger.info(f"✅ Schéma à jour (migration {current})")
    else:
        logger.warning(
            f"⚠️ Schéma en retard : base sur '{current}', dernière migration '{head}'. "
            "Lance : docker compose exec backend alembic upgrade head"
        )
