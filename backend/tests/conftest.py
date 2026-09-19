"""
Configuration et fixtures pour pytest.

La base de test est dérivée de DATABASE_URL (même hôte/identifiants, base
`orchestrator_test`), donc les tests tournent tels quels dans le conteneur
backend : `docker compose exec backend python -m pytest`.
Surchargeable via la variable d'environnement TEST_DATABASE_URL.
"""
import os
import re
from typing import AsyncGenerator

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


def _test_database_url() -> str:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    url = str(settings.DATABASE_URL)
    # Forcer le driver async (DATABASE_URL peut être en postgresql:// simple)
    url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+asyncpg://", url)
    base, _, _ = url.rpartition("/")
    return f"{base}/orchestrator_test"


TEST_DATABASE_URL = _test_database_url()


async def _ensure_test_database() -> None:
    """Crée la base de test si elle n'existe pas (via la base de maintenance)."""
    dsn = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    base, _, dbname = dsn.rpartition("/")
    conn = await asyncpg.connect(f"{base}/postgres")
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def test_engine():
    # Portée fonction : chaque test a sa boucle asyncio, un moteur partagé
    # entre boucles provoque « attached to a different loop » (asyncpg)
    await _ensure_test_database()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session de test : tables créées avant chaque test, supprimées après."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP de test branché sur la session de test."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    except ImportError:  # httpx < 0.27
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Utilisateur de test inscrit + jeton Bearer prêt à l'emploi."""
    await client.post("/api/v1/auth/register", json={
        "email": "tester@example.com", "password": "Test1234!", "full_name": "Tester",
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": "tester@example.com", "password": "Test1234!",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
