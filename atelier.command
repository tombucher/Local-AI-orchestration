#!/bin/bash
# Ouvrir l'atelier en un geste : double-clic dans le Finder, ou ./atelier.command
#
# Lance Docker Desktop et Ollama s'ils dorment, démarre les services, applique
# les migrations et ouvre l'interface dans le navigateur. Sans argument tout
# est idempotent : relancer ne casse rien. `./atelier.command stop` arrête tout.
set -e
cd "$(dirname "$0")"

dire() { printf '\033[1m%s\033[0m\n' "$1"; }

if [ "${1:-}" = "stop" ]; then
    docker compose down
    dire "Atelier fermé. Docker Desktop reste ouvert (Cmd+Q pour le quitter)."
    exit 0
fi

if [ ! -f .env ]; then
    dire "Pas de fichier .env : copie .env.example en .env et renseigne POSTGRES_PASSWORD et SECRET_KEY."
    exit 1
fi

# 1. Docker Desktop : l'app démarre en arrière-plan, le démon met ~20 s à répondre
if ! docker info >/dev/null 2>&1; then
    dire "Démarrage de Docker Desktop…"
    open -a Docker
    for _ in $(seq 1 60); do
        docker info >/dev/null 2>&1 && break
        sleep 2
    done
    docker info >/dev/null 2>&1 || { dire "Docker ne répond pas. Ouvre Docker Desktop à la main puis relance."; exit 1; }
fi

# 2. Ollama natif : l'app macOS si elle est installée, sinon le service en ligne de commande
if ! curl -sf http://localhost:11434/api/version >/dev/null; then
    dire "Démarrage d'Ollama…"
    if [ -d "/Applications/Ollama.app" ]; then
        open -a Ollama
    elif command -v ollama >/dev/null; then
        (ollama serve >/dev/null 2>&1 &)
    else
        dire "Ollama n'est pas installé : https://ollama.com (puis ollama pull qwen3.8:27b-mlx)."
        exit 1
    fi
    for _ in $(seq 1 30); do
        curl -sf http://localhost:11434/api/version >/dev/null && break
        sleep 1
    done
fi
if [ "$(curl -sf http://localhost:11434/api/tags | grep -c '"name"')" = "0" ]; then
    dire "Aucun modèle Ollama installé : ollama pull qwen3.8:27b-mlx et ollama pull gemma4:12b-mlx"
fi

# 3. Les services (Open WebUI est optionnel : docker compose --profile chat up -d)
dire "Démarrage des services…"
docker compose up -d --quiet-pull 2>&1 | grep -v "is up-to-date" || true

for _ in $(seq 1 60); do
    curl -sf http://localhost:8000/health >/dev/null && break
    sleep 2
done
curl -sf http://localhost:8000/health >/dev/null || {
    dire "Le backend ne répond pas. Logs : docker compose logs backend"; exit 1; }

# 4. Migrations : sans effet si le schéma est déjà à jour
docker compose exec -T backend alembic upgrade head 2>&1 | grep -i "running upgrade" || true

dire "L'atelier est ouvert : http://localhost:5173"
open http://localhost:5173
