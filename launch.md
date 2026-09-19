# 🚀 Lancement — Orchestrateur IA

Instructions simples pour démarrer l'application en local (MacBook Pro M3 Max).

---

## 📋 Prérequis

1. **Docker Desktop** installé et lancé
2. **Ollama** installé nativement sur macOS (https://ollama.ai)
3. **Modèles Ollama** téléchargés (variantes `-mlx` pour Apple Silicon) :
   ```bash
   ollama pull qwen3.8:27b-mlx     # code, documents, analyse, idéation
   ollama pull gemma4:12b-mlx      # tâches courtes : veille, scoring, briefing
   ```
   Les modèles se choisissent ensuite dans **Paramètres** ; si l'un d'eux disparaît, l'application bascule automatiquement sur un modèle installé.
4. **Ollama en service** : `ollama serve` (ou lancer l'app macOS)

---

## ⚙️ Configuration initiale (première fois)

```bash
# 1. Copier le fichier d'exemple
cp .env.example .env

# 2. Générer une SECRET_KEY sécurisée
python3 -c "import secrets; print(secrets.token_hex(32))"

# 3. Éditer .env et renseigner :
#    - POSTGRES_PASSWORD=<ton_mot_de_passe>
#    - SECRET_KEY=<la_clé_générée>
#    - DATABASE_URL (même mot de passe que POSTGRES_PASSWORD)
#    - OLLAMA_MODEL_PROMPT=gemma4:12b-mlx (modèle rapide)
```

---

## ▶️ Démarrer l'application

```bash
docker compose up -d
```

Premier lancement : le build prend quelques minutes (images backend/frontend).

### Vérifier que tout tourne

```bash
docker compose ps
```

Tous les services doivent être `Up` (healthy pour postgres et backend). Le service `db-backup` écrit une sauvegarde quotidienne dans `./backups/`.

---

## 🌐 Accès aux interfaces

| Service | URL |
|---|---|
| 🎨 **Frontend** (interface principale) | http://localhost:5173 |
| 📚 **API Swagger** (docs interactives) | http://localhost:8000/docs |
| ⚙️ API Backend | http://localhost:8000 |
| 🌐 Open WebUI (chat Ollama) | http://localhost:3001 (localhost uniquement) |
| 🗄️ PostgreSQL | 127.0.0.1:5432 (localhost uniquement) |
| 🤖 Ollama (natif macOS) | http://localhost:11434 |

**Premier usage** : créer un compte via http://localhost:5173 (signup activé).

---

## 🛠️ Commandes utiles

```bash
# Voir les logs en continu
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f backend

# Arrêter l'application
docker compose down

# Rebuild après changement de code
docker compose up -d --build

# Reset complet de la base de données ⚠️
docker compose down -v && docker compose up -d

# Appliquer les migrations Alembic (si nouvelle migration)
docker compose exec backend alembic upgrade head
```

---

## 🔍 Troubleshooting

| Problème | Solution |
|---|---|
| Backend ne répond pas | `docker compose logs backend` — vérifier que la migration Alembic s'est bien exécutée |
| Erreurs Ollama / timeout | Vérifier `curl http://localhost:11434/api/tags` (Ollama doit tourner côté macOS) |
| Tâche bloquée en GENERATING | Le watchdog la remet en FAILED après 15 min, puis retry auto |
| « model not found » à la génération | Le modèle configuré a été supprimé : `ollama list` puis rechoisir dans Paramètres |
| Veille sans résultats / 403 DuckDuckGo | Rate-limit temporaire ; ajouter `BRAVE_SEARCH_API_KEY` dans `.env` |
| Port déjà utilisé | `lsof -i :5173` (ou 8000, 5432) puis tuer le process |

---

## 🧠 Rappels architecture

- Scheduler : traite la file d'attente toutes les **2 min** (veilles, recherches, admin en automatique ; code et documents à la demande)
- Retry exponentiel : 1 min → 5 min → 15 min en cas d'échec
- Rapports quotidiens : générés chaque jour à **8h00** pour les utilisateurs actifs
- Veilles récurrentes : check toutes les **15 min**
- Watchdog tâches zombies : toutes les **5 min**

---

## 📱 Accès depuis le téléphone

Voir la section « Depuis le téléphone (Tailscale) » du README : `tailscale serve --bg --https=443 http://localhost:5173`, puis ajouter l'URL `.ts.net` à l'écran d'accueil. Notifications du briefing : app ntfy + `NTFY_TOPIC` dans `.env`.
