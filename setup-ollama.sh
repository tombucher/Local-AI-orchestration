#!/bin/bash
set -e

echo "🤖 Installation Ollama..."

# Installer Ollama
if ! command -v ollama &> /dev/null; then
    brew install ollama
fi

# Démarrer service
brew services start ollama
sleep 5

# Télécharger Mistral 7B
echo "📥 Téléchargement Mistral 7B (~4 GB)..."
ollama pull mistral:7b-instruct-q4_K_M

# Test
echo "🧪 Test..."
ollama run mistral:7b-instruct-q4_K_M "Réponds juste 'OK'" | head -n 1

echo "✅ Ollama prêt sur http://localhost:11434"