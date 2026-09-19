# Guide de Déploiement - Orchestrateur IA

Ce guide couvre le déploiement local du système Orchestrateur IA sur macOS avec M3 Max.

---

## Prérequis

### Matériel Recommandé
- **CPU** : Apple Silicon (M1/M2/M3) ou équivalent x86_64
- **RAM** : 16GB minimum, 32GB+ recommandé
- **Stockage** : 20GB libres minimum

### Logiciels Requis

1. **Docker Desktop**
   ```bash
   # Installer via Homebrew
   brew install --cask docker

   # Ou télécharger depuis https://www.docker.com/products/docker-desktop

   # Vérifier l'installation
   docker --version
   docker-compose --version
   ```

2. **Ollama** (pour LLM locaux)
   ```bash
   # Installer Ollama
   brew install ollama

   # Démarrer le service
   brew services start ollama

   # Vérifier qu'il tourne
   ollama list
   ```

3. **Git**
   ```bash
   brew install git
   ```

---

## Installation Rapide

### 1. Cloner le Projet

```bash
# Cloner le repository
git clone <votre-repo-url>
cd orchestrateur-ia
```

### 2. Installer les Modèles Ollama

```bash
# Script automatique (recommandé)
chmod +x setup-ollama.sh
./setup-ollama.sh

# OU manuellement
ollama pull mistral:7b-instruct-q4_K_M      # ~4.1GB
ollama pull devstral-small-2                 # ~7.5GB

# Vérifier les modèles installés
ollama list
```

**Note** : Le téléchargement peut prendre 10-30 minutes selon votre connexion.

### 3. Configuration de l'Environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer si nécessaire (optionnel pour dev)
nano .env
```

**Variables importantes** :
```env
# Database (par défaut OK pour dev local)
DATABASE_URL=postgresql+asyncpg://orchestrator_user:<mot_de_passe>@postgres:5432/orchestrator

# Security (CHANGER EN PRODUCTION!)
SECRET_KEY=votre_cle_secrete_tres_longue_et_aleatoire

# Ollama (localhost pour macOS natif)
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL_CODE=devstral-small-2
OLLAMA_MODEL_PROMPT=mistral:7b-instruct-q4_K_M

# Orchestrator
ORCHESTRATOR_INTERVAL_MINUTES=5
ORCHESTRATOR_BATCH_SIZE=5
```

### 4. Démarrer les Services

```bash
# Rendre le script exécutable
chmod +x start.sh

# Lancer tous les services
./start.sh
```

**Le script va** :
1. Vérifier qu'Ollama tourne
2. Builder les images Docker (première fois : ~5-10 min)
3. Démarrer PostgreSQL
4. Appliquer les migrations DB
5. Démarrer le backend FastAPI
6. Démarrer le frontend React
7. Démarrer Open WebUI

**Logs en temps réel** :
```bash
# Tous les services
docker-compose logs -f

# Backend uniquement
docker-compose logs -f backend

# Frontend uniquement
docker-compose logs -f frontend
```

### 5. Vérifier que Tout Fonctionne

**Services à vérifier** :
```bash
docker-compose ps
```

Devrait afficher :
```
NAME                    STATUS
orchestrator-backend    Up (healthy)
orchestrator-postgres   Up (healthy)
orchestrator-frontend   Up
open-webui             Up (healthy)
```

**Endpoints** :
- Frontend : http://localhost:5173
- Backend API : http://localhost:8000
- Swagger UI : http://localhost:8000/docs
- Open WebUI : http://localhost:3001

**Health Check Backend** :
```bash
curl http://localhost:8000/health

# Devrait répondre : {"status":"healthy"}
```

**Connexion Ollama depuis le backend** :
```bash
# Depuis le backend container
docker exec orchestrator-backend curl http://host.docker.internal:11434/api/tags

# Devrait lister les modèles
```

### 6. Créer des Données de Démonstration

```bash
# Créer user demo + projets + tâches
docker exec orchestrator-backend python scripts/seed_demo_data.py
```

**Login démo** :
- Email : `demo@example.com`
- Password : `demo123`

---

## Architecture Déployée

```
┌─────────────────────────────────────────────────────────┐
│                    macOS Host (M3 Max)                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Ollama (natif macOS)                             │  │
│  │ localhost:11434                                  │  │
│  │ - Mistral 7B Instruct                            │  │
│  │ - Devstral Small 2                               │  │
│  └──────────────────────────────────────────────────┘  │
│                          ▲                               │
│                          │ host.docker.internal          │
├──────────────────────────┼───────────────────────────────┤
│                          │                               │
│  ┌──────────────────────┼───────────────────────────┐  │
│  │ Docker Network (orchestrator_network)            │  │
│  │                      │                            │  │
│  │  ┌───────────────────┼────────────────────────┐  │  │
│  │  │ Backend (FastAPI)  │                        │  │  │
│  │  │ localhost:8000     │                        │  │  │
│  │  │ ├─ API REST        │                        │  │  │
│  │  │ ├─ Orchestrator ───┘                        │  │  │
│  │  │ └─ Scheduler (5min)                         │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │            │                                       │  │
│  │            │                                       │  │
│  │  ┌─────────┼────────────────────────────────────┐ │  │
│  │  │ PostgreSQL 15                                │ │  │
│  │  │ localhost:5432                               │ │  │
│  │  │ Database: orchestrator                       │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Frontend (React + Vite)                          │  │
│  │ localhost:5173                                   │  │
│  │ - Hot Module Replacement                         │  │
│  │ - TailwindCSS                                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Open WebUI                                       │  │
│  │ localhost:3001                                   │  │
│  │ - Interface ChatGPT-like pour Ollama            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Commandes Utiles

### Gestion des Services

```bash
# Démarrer
./start.sh

# Arrêter
docker-compose down

# Arrêter et supprimer les volumes (⚠️ perte de données!)
docker-compose down -v

# Redémarrer un service
docker-compose restart backend
docker-compose restart frontend

# Rebuild après modifications
docker-compose up -d --build backend

# Rebuild complet (no cache)
docker-compose build --no-cache
docker-compose up -d
```

### Logs et Debug

```bash
# Voir les logs en temps réel
docker-compose logs -f backend
docker-compose logs -f frontend

# Dernières 100 lignes
docker-compose logs --tail=100 backend

# Logs depuis un timestamp
docker-compose logs --since "2025-01-01T00:00:00" backend
```

### Base de Données

```bash
# Accéder au shell PostgreSQL
docker exec -it orchestrator-postgres psql -U orchestrator_user -d orchestrator

# Lister les tables
\dt

# Quitter
\q

# Backup de la DB
docker exec orchestrator-postgres pg_dump -U orchestrator_user orchestrator > backup.sql

# Restore
docker exec -i orchestrator-postgres psql -U orchestrator_user orchestrator < backup.sql
```

### Migrations Alembic

```bash
# Créer une nouvelle migration
docker exec orchestrator-backend alembic revision --autogenerate -m "Description"

# Appliquer les migrations
docker exec orchestrator-backend alembic upgrade head

# Revenir en arrière (1 migration)
docker exec orchestrator-backend alembic downgrade -1

# Voir l'historique
docker exec orchestrator-backend alembic history

# Voir la version actuelle
docker exec orchestrator-backend alembic current
```

### Tests

```bash
# Lancer tous les tests
docker exec orchestrator-backend pytest

# Tests avec couverture
docker exec orchestrator-backend pytest --cov=app --cov-report=html

# Tests d'intégration uniquement
docker exec orchestrator-backend pytest tests/integration/

# Test spécifique
docker exec orchestrator-backend pytest tests/integration/test_full_workflow.py -v

# Tests frontend
docker exec orchestrator-frontend npm test
```

---

## Dépannage

### Ollama ne répond pas

```bash
# Vérifier le statut
brew services list | grep ollama

# Redémarrer
brew services restart ollama

# Tester depuis le host
curl http://localhost:11434/api/tags

# Tester depuis le backend container
docker exec orchestrator-backend curl http://host.docker.internal:11434/api/tags
```

### Port déjà utilisé

```bash
# Port 5173 (frontend)
lsof -ti:5173 | xargs kill -9

# Port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Port 5432 (postgres)
lsof -ti:5432 | xargs kill -9
```

### Backend ne démarre pas

```bash
# Voir les logs
docker-compose logs backend

# Erreur bcrypt commune : rebuild
docker-compose build --no-cache backend
docker-compose up -d backend

# Vérifier la connexion DB
docker exec orchestrator-backend python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Frontend ne se connecte pas au backend

```bash
# 1. Vérifier que le backend tourne
curl http://localhost:8000/health

# 2. Vérifier les CORS dans backend logs
docker-compose logs backend | grep CORS

# 3. Vérifier les variables d'env du frontend
docker exec orchestrator-frontend printenv | grep VITE_
```

### Migrations échouent

```bash
# Vérifier l'état actuel
docker exec orchestrator-backend alembic current

# Réinitialiser complètement (⚠️ perte de données!)
docker-compose down -v
docker-compose up -d postgres
sleep 5
docker-compose up -d backend
docker exec orchestrator-backend alembic upgrade head
```

### Orchestrator ne génère pas de code

```bash
# 1. Vérifier les logs
docker-compose logs backend | grep -i orchestrator

# 2. Vérifier qu'il y a des tâches READY
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/orchestrator/queue

# 3. Forcer la génération manuelle
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/tasks/TASK_ID/generate

# 4. Vérifier la connexion Ollama
docker exec orchestrator-backend python -c "from app.services.llm_client import OllamaClient; import asyncio; client = OllamaClient(); print(asyncio.run(client.health_check()))"
```

---

## Optimisations Performance

### Ressources Docker

Ajuster dans Docker Desktop > Settings > Resources :

- **CPUs** : 4-6 cores (laisser 2 pour le système)
- **Memory** : 8-12GB (laisser 8GB pour macOS + Ollama)
- **Swap** : 2GB
- **Disk** : 20GB minimum

### Ollama Performance

```bash
# Vérifier l'utilisation mémoire
top -pid $(pgrep ollama)

# Si lent, réduire les modèles concurrents
# Éditer .env :
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

### PostgreSQL Tuning

Éditer `docker-compose.yml` :
```yaml
services:
  postgres:
    environment:
      - POSTGRES_SHARED_BUFFERS=256MB
      - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
      - POSTGRES_WORK_MEM=16MB
```

---

## Monitoring

### Métriques Système

```bash
# CPU/RAM des containers
docker stats

# Logs avec timestamps
docker-compose logs -f -t backend
```

### Endpoints de Monitoring

- **Backend Health** : http://localhost:8000/health
- **Orchestrator Status** : http://localhost:8000/api/v1/orchestrator/status
- **Queue Status** : http://localhost:8000/api/v1/orchestrator/queue

---

## Backup et Restore

### Backup Complet

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup DB
docker exec orchestrator-postgres pg_dump -U orchestrator_user orchestrator > $BACKUP_DIR/db.sql

# Backup .env
cp .env $BACKUP_DIR/.env

echo "Backup créé dans $BACKUP_DIR"
```

### Restore

```bash
# 1. Arrêter les services
docker-compose down

# 2. Supprimer les volumes
docker volume rm orchestrator-ia_postgres_data

# 3. Redémarrer
docker-compose up -d postgres
sleep 10

# 4. Restore DB
cat backups/20250101_120000/db.sql | docker exec -i orchestrator-postgres psql -U orchestrator_user orchestrator

# 5. Redémarrer tous les services
docker-compose up -d
```

---

## Production Checklist

**Avant de passer en production** :

- [ ] Changer `SECRET_KEY` dans `.env` (minimum 32 caractères aléatoires)
- [ ] Utiliser un mot de passe DB fort
- [ ] Activer HTTPS avec certificats SSL
- [ ] Configurer CORS pour le domaine de production uniquement
- [ ] Désactiver le mode debug (`DEBUG=False`)
- [ ] Configurer un reverse proxy (Nginx/Caddy)
- [ ] Mettre en place des backups automatiques
- [ ] Configurer la rotation des logs
- [ ] Activer le monitoring (Prometheus/Grafana)
- [ ] Tester le disaster recovery
- [ ] Documenter le runbook d'incidents

---

## Support

**Logs centralisés** :
```bash
# Sauvegarder tous les logs
docker-compose logs > debug_$(date +%Y%m%d_%H%M%S).log
```

**Informations système** :
```bash
# Versions
docker --version
docker-compose --version
ollama --version
python --version

# État des services
docker-compose ps
brew services list
```

---

**Déploiement réussi !** 🎉

Pour commencer à utiliser l'application :
1. Accédez à http://localhost:5173
2. Créez un compte ou utilisez `demo@example.com` / `demo123`
3. Créez votre premier projet
4. Lancez votre première génération de code !
