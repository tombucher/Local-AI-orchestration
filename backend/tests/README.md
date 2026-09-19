# Tests — backend

39 tests d'API (auth, projets, tâches, gestion d'erreurs). Ils tournent **dans le conteneur backend** contre une base dédiée `orchestrator_test`, créée automatiquement.

## Lancer

```bash
./run_tests.sh                 # tous les tests
./run_tests.sh coverage        # avec couverture
docker compose exec backend python -m pytest -q                       # équivalent
docker compose exec backend python -m pytest tests/test_projects.py -q
docker compose exec backend python -m pytest -k "isolated" -q
```

## Fonctionnement (`conftest.py`)

- `TEST_DATABASE_URL` est dérivée de `DATABASE_URL` (même hôte et identifiants, base `orchestrator_test`, driver `asyncpg` forcé). Surchargeable par variable d'environnement.
- La base est créée si elle n'existe pas ; les tables sont recréées **avant chaque test** et supprimées après.
- Le moteur SQLAlchemy est en portée *fonction* : chaque test a sa propre boucle asyncio (sinon asyncpg lève « attached to a different loop »).
- Fixtures : `client` (httpx `ASGITransport` branché sur l'app, `get_db` surchargé) et `auth_headers` (utilisateur `tester@example.com` inscrit + jeton Bearer).

## Structure

```
tests/
├── conftest.py               # base de test, client, auth_headers
├── test_auth.py              # inscription, connexion, /me
├── test_projects.py          # CRUD, stats, archivage, isolation par utilisateur, 422
├── test_tasks.py             # CRUD, validation, annulation, logs
└── test_error_handling.py    # format d'erreur unifié {"error","message","details"}
```

Les anciens tests d'intégration (qui attaquaient la vraie base et l'ancien `TaskOrchestrator`) sont dans `archive/old_tests/`.

## Écrire un test

```python
async def test_example(client, auth_headers):
    r = await client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Projet", "type": "personal",
        "features": {"code_gen": True, "veille": False, "git_auto": False},
    })
    assert r.status_code == 201
```

Pas de `@pytest.mark.asyncio` nécessaire (`asyncio_mode = auto`). Les erreurs API ont la forme `{"error": "...", "message": "...", "details": {...}}` — pas de clé `detail`.

## Outils

Dépendances dans `requirements-dev.txt`, installées dans le stage `development` de l'image. Après modification : `docker compose build backend`.
