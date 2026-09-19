# Backend - Orchestrateur IA

API REST FastAPI avec authentification JWT pour le projet Orchestrateur IA.

## 🚀 Quick Start

### Prérequis
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation (Développement avec Docker)

1. **Copier les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env et personnaliser les valeurs
```

2. **Démarrer les services**
```bash
# Depuis la racine du projet
docker compose up -d
```

3. **Vérifier que tout fonctionne**
```bash
# API health check
curl http://localhost:8000/health

# Documentation Swagger
open http://localhost:8000/docs
```

### Installation (Développement local)

1. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configurer la base de données**
```bash
# Créer la base de données
createdb orchestrator

# Variables d'environnement
cp .env.example .env
# Éditer DATABASE_URL pour pointer vers localhost
```

4. **Lancer le serveur**
```bash
uvicorn app.main:app --reload
```

## 🗄️ Migrations Alembic

### Créer une nouvelle migration
```bash
# Auto-générer depuis les modèles
alembic revision --autogenerate -m "Description du changement"

# Ou créer une migration vide
alembic revision -m "Description"
```

### Appliquer les migrations
```bash
# Appliquer toutes les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1
```

### Historique des migrations
```bash
alembic history
alembic current
```

## 🧪 Tests

Les tests tournent dans le conteneur (base `orchestrator_test` créée automatiquement) :

```bash
../run_tests.sh                                              # depuis la racine
docker compose exec backend python -m pytest -q             # équivalent
docker compose exec backend python -m pytest tests/test_auth.py::test_register_user
docker compose exec backend python -m pytest --cov=app --cov-report=term
```

Détails dans `tests/README.md`. Outils de test dans `requirements-dev.txt` (stage `development` de l'image).

## 📚 Documentation API

Une fois le serveur lancé :

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc
- **OpenAPI JSON** : http://localhost:8000/api/v1/openapi.json

## 🏗️ Structure du Projet

Voir `../PROJECT_STRUCTURE.md` (arborescence complète et à jour). Points d'entrée :
- `app/main.py` — application FastAPI, CORS, handlers d'erreurs, scheduler
- `app/api/v1/` — endpoints (auth, projects, tasks, ideation, orchestrator, reports, settings, time)
- `app/services/model_registry.py` — résolution des modèles Ollama (obligatoire pour tout appel LLM)
- `app/services/unified_orchestrator.py` — traitement des tâches par type

## 🔐 Authentification

### Créer un compte
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### Accéder aux endpoints protégés
```bash
# Utiliser le token reçu lors du login
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 🔧 Configuration

Les variables d'environnement sont définies dans `.env` (copier depuis `.env.example`).

### Variables principales

| Variable | Description | Défaut |
|----------|-------------|--------|
| `ENV` | Environnement (development/production) | development |
| `DEBUG` | Mode debug | False |
| `SECRET_KEY` | Clé secrète pour JWT | **À CHANGER !** |
| `DATABASE_URL` | URL de la base de données | postgresql://... |
| `OLLAMA_HOST` | URL du serveur Ollama | http://host.docker.internal:11434 |
| `LOG_LEVEL` | Niveau de log | INFO |
| `OLLAMA_MODEL_PROMPT` | Modèle rapide (veille, scoring, briefing) | gemma4:12b-mlx |
| `AIDES_TERRITOIRES_API_KEY` | Aides publiques FR (optionnel) | vide |
| `BRAVE_SEARCH_API_KEY` | Recherche web Brave (optionnel) | vide |

## 🐛 Debugging

### Logs de l'application
```bash
# Docker
docker compose logs -f backend

# Local
# Les logs apparaissent dans le terminal
```

### Shell dans le container
```bash
docker exec -it orchestrator-backend bash
```

### Accéder à la base de données
```bash
# Depuis le host
psql -U orchestrator_user -d orchestrator -h localhost

# Depuis le container
docker exec -it orchestrator-postgres psql -U orchestrator_user -d orchestrator
```

## 📝 Conventions de Code

- **Type hints** : Obligatoires pour toutes les fonctions
- **Docstrings** : Google style pour les fonctions publiques
- **Async/await** : Utiliser l'async partout (SQLAlchemy 2.0)
- **Pydantic** : Pour toutes les validations et sérialisations
- **Tests** : Chaque endpoint doit avoir des tests

## 🧠 Modèles LLM

Ne jamais coder un nom de modèle en dur : `from app.services.model_registry import resolve_model, think_kwargs`. `resolve_model()` renvoie le modèle préféré s'il est installé, sinon un repli disponible ; `think_kwargs()` désactive le mode thinking quand le modèle le supporte.

## 📄 License

Projet privé - Tous droits réservés
