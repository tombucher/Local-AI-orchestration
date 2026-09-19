#!/bin/bash
set -e

echo "🚀 Démarrage Orchestrateur IA..."

# Vérifier Ollama
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "❌ Ollama non actif. Lance: ./setup-ollama.sh"
    exit 1
fi

# Vérifier .env
if [ ! -f .env ]; then
    echo "⚠️  Fichier .env manquant (optionnel)"
    echo "   cp .env.example .env"
    echo ""
    echo "✅ Mais on continue (pas d'API Claude nécessaire)"
    echo ""
fi

# Démarrer Docker
docker-compose up -d

echo ""
echo "✅ Démarré !"
echo ""
echo "📍 Interfaces:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8000"
echo "   Open WebUI: http://localhost:3001"
echo ""
echo "📊 Commandes:"
echo "   Logs:   docker-compose logs -f"
echo "   Stop:   docker-compose down"