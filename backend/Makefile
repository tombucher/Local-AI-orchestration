# ════════════════════════════════════════════════════════════
# Makefile - Backend Orchestrateur IA
# ════════════════════════════════════════════════════════════

.PHONY: help install run test clean migrate upgrade downgrade shell db-shell

help:  ## Afficher cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────────────────
# Installation
# ──────────────────────────────────────────────────────────

install:  ## Installer les dépendances
	pip install -r requirements.txt

install-dev:  ## Installer les dépendances + dev tools
	pip install -r requirements.txt
	pip install black ruff mypy

# ──────────────────────────────────────────────────────────
# Développement
# ──────────────────────────────────────────────────────────

run:  ## Lancer le serveur en mode dev
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-prod:  ## Lancer le serveur en mode production
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# ──────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────

test:  ## Lancer tous les tests
	pytest

test-v:  ## Lancer les tests en mode verbose
	pytest -v

test-cov:  ## Lancer les tests avec coverage
	pytest --cov=app --cov-report=html --cov-report=term

test-watch:  ## Lancer les tests en mode watch
	pytest-watch

# ──────────────────────────────────────────────────────────
# Database & Migrations
# ──────────────────────────────────────────────────────────

migrate:  ## Créer une nouvelle migration (usage: make migrate MESSAGE="description")
	alembic revision --autogenerate -m "$(MESSAGE)"

upgrade:  ## Appliquer toutes les migrations
	alembic upgrade head

downgrade:  ## Revenir à la migration précédente
	alembic downgrade -1

history:  ## Afficher l'historique des migrations
	alembic history

current:  ## Afficher la migration actuelle
	alembic current

db-shell:  ## Ouvrir un shell PostgreSQL
	psql -U orchestrator_user -d orchestrator -h localhost

# ──────────────────────────────────────────────────────────
# Code Quality
# ──────────────────────────────────────────────────────────

format:  ## Formater le code avec black
	black app/ tests/

lint:  ## Linter le code avec ruff
	ruff check app/ tests/

type-check:  ## Vérifier les types avec mypy
	mypy app/

quality:  ## Lancer tous les checks qualité
	make format
	make lint
	make type-check

# ──────────────────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────────────────

docker-build:  ## Build l'image Docker
	docker build -t orchestrator-backend .

docker-run:  ## Lancer le container Docker
	docker run -p 8000:8000 --env-file .env orchestrator-backend

shell:  ## Ouvrir un shell dans le container backend
	docker exec -it orchestrator-backend bash

# ──────────────────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────────────────

clean:  ## Nettoyer les fichiers temporaires
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -f .coverage

seed:  ## Créer des données de démonstration (Phase 2+)
	python scripts/seed_demo_data.py

# ──────────────────────────────────────────────────────────
# Documentation
# ──────────────────────────────────────────────────────────

docs:  ## Ouvrir la documentation API
	@echo "Opening API documentation..."
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs
