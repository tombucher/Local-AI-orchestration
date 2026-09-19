# 🚀 Quick Start - Backend Orchestrateur IA

Guide de démarrage rapide pour tester le backend localement.

## ✅ Prérequis

- Docker Desktop actif
- PostgreSQL accessible sur `localhost:5432`
- Python 3.11+ (pour tests locaux)

## 📋 Étapes

### 1. Configuration Environnement

```bash
# Copier les variables d'environnement
cp .env.example .env   # à la racine du projet

# Éditer .env et vérifier :
# - DATABASE_URL=postgresql+asyncpg://orchestrator_user:<mot_de_passe>@postgres:5432/orchestrator
# - SECRET_KEY (générer avec: openssl rand -hex 32)
```

### 2. Lancer avec Docker Compose

```bash
# Depuis la racine du projet
docker compose up -d backend

# Vérifier les logs
docker compose logs -f backend
```

### 3. Tester l'API

**Health Check**
```bash
curl http://localhost:8000/health
```

Réponse attendue :
```json
{
  "status": "ok",
  "app": "Orchestrateur IA",
  "version": "0.1.0",
  "environment": "development"
}
```

**Documentation Swagger**
```
http://localhost:8000/docs
```

### 4. Créer un Compte et Tester l'Auth

**Créer un compte**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

**Login**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

Copier le `access_token` de la réponse.

**Accéder à /me**
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer VOTRE_ACCESS_TOKEN"
```

## 🧪 Lancer les Tests

**Option 1 : Depuis le container**
```bash
docker exec -it orchestrator-backend pytest
```

**Option 2 : En local**
```bash
# Créer une DB de test
createdb orchestrator_test

# Installer les dépendances
pip install -r requirements.txt

# Lancer les tests
pytest
```

## 🐛 Troubleshooting

### Le backend ne démarre pas

```bash
# Vérifier PostgreSQL
docker compose ps postgres

# Voir les logs
docker compose logs backend

# Rebuild le container
docker compose up -d --build backend
```

### Erreur de connexion DB

```bash
# Vérifier que PostgreSQL est accessible
psql -U orchestrator_user -d orchestrator -h localhost

# Si échec, vérifier le mot de passe dans .env
```

### Les tests échouent

```bash
# La base orchestrator_test est créée automatiquement par tests/conftest.py.
# Vérifier que le conteneur backend tourne et relancer :
docker compose ps
../run_tests.sh
```

## 📚 Pour aller plus loin

État fonctionnel et roadmap : `../PROJECT_STATE.md` · Architecture : `../PROJECT_STRUCTURE.md` · Tests : `tests/README.md`.

## 💡 Commandes Utiles

```bash
# Voir tous les containers
docker compose ps

# Logs en temps réel
docker compose logs -f backend

# Shell dans le container
docker exec -it orchestrator-backend bash

# Reset complet (⚠️ supprime les données)
docker compose down -v
docker compose up -d
```

## ✅ Validation

Votre backend est prêt si :

- ✅ Health check répond `200 OK`
- ✅ `/docs` affiche la documentation Swagger
- ✅ Vous pouvez créer un compte
- ✅ Vous pouvez vous connecter et recevoir un token
- ✅ Vous pouvez accéder à `/me` avec le token
- ✅ Les tests passent (`../run_tests.sh`)
