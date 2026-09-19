# Améliorer la vitesse de génération de code

## Problème: Génération trop lente (3-4 minutes)

La génération de code est lente car Ollama utilise un modèle lourd localement sur votre machine.

## Solution actuelle appliquée ✅

J'ai changé le modèle de **devstral-small-2 (15 GB)** à **mistral:7b (4.3 GB)**.

**Résultat attendu**: Génération **2-3x plus rapide** (~1-2 minutes au lieu de 3-4 minutes)

**Trade-off**: Le code généré sera moins précis et moins complexe.

---

## Options disponibles

### Option 1: Mistral 7B (APPLIQUÉE)

**Fichier**: `backend/app/core/config.py` ligne 43
```python
OLLAMA_MODEL_CODE: str = "mistral:7b-instruct-q4_K_M"
```

✅ **Plus rapide** (~1-2 minutes)
⚠️ **Moins bon pour le code** (code plus simple, parfois des erreurs)

**Quand utiliser**:
- Pour des tâches simples
- Pour tester rapidement
- Quand la vitesse prime sur la qualité

---

### Option 2: Devstral Small 2 (AVANT)

**Fichier**: `backend/app/core/config.py` ligne 43
```python
OLLAMA_MODEL_CODE: str = "devstral-small-2"
```

⚠️ **Plus lent** (~3-4 minutes)
✅ **Meilleur pour le code** (code plus complexe et précis)

**Quand utiliser**:
- Pour des tâches complexes
- Pour du code de production
- Quand la qualité prime sur la vitesse

---

### Option 3: Télécharger un modèle optimisé pour le code

Vous pouvez télécharger **CodeLlama** ou **DeepSeek Coder** qui sont optimisés pour le code:

```bash
# CodeLlama 7B (rapide, bon pour le code)
ollama pull codellama:7b-instruct

# DeepSeek Coder 6.7B (très bon pour le code)
ollama pull deepseek-coder:6.7b-instruct
```

Puis dans `backend/app/core/config.py`:
```python
OLLAMA_MODEL_CODE: str = "codellama:7b-instruct"
# OU
OLLAMA_MODEL_CODE: str = "deepseek-coder:6.7b-instruct"
```

**Avantages**:
- ✅ Rapide (7B paramètres)
- ✅ Spécialisé pour le code
- ✅ Meilleur que Mistral général pour le code

---

### Option 4: Utiliser une API externe (OpenAI, Anthropic)

**Le plus rapide** mais **payant** et nécessite une connexion internet.

```python
# Dans config.py
USE_EXTERNAL_LLM: bool = True
OPENAI_API_KEY: str = "sk-..."
```

**Avantages**:
- ✅ Très rapide (quelques secondes)
- ✅ Meilleure qualité de code
- ✅ Ne consomme pas de ressources locales

**Inconvénients**:
- ❌ Coût par requête
- ❌ Nécessite internet
- ❌ Envoie le code à un tiers

---

## Comparaison des vitesses

| Modèle | Taille | Vitesse estimée | Qualité code |
|--------|--------|----------------|--------------|
| **Mistral 7B** (actuel) | 4.3 GB | ~1-2 min | ⭐⭐⭐ |
| Devstral Small 2 | 15 GB | ~3-4 min | ⭐⭐⭐⭐⭐ |
| CodeLlama 7B | ~4 GB | ~1-2 min | ⭐⭐⭐⭐ |
| DeepSeek Coder 6.7B | ~4 GB | ~1-2 min | ⭐⭐⭐⭐⭐ |
| OpenAI GPT-4 | N/A | ~5-10 sec | ⭐⭐⭐⭐⭐ |

---

## Comment changer de modèle

### 1. Télécharger le modèle (si nouveau)

```bash
ollama pull codellama:7b-instruct
```

### 2. Modifier la configuration

Éditez `backend/app/core/config.py` ligne 43:
```python
OLLAMA_MODEL_CODE: str = "codellama:7b-instruct"
```

### 3. Redémarrer le backend

```bash
docker-compose restart backend
```

### 4. Tester

Lancez une génération et vérifiez la vitesse et la qualité du code.

---

## Optimisations supplémentaires

### Réduire la longueur du prompt

Des prompts plus courts = génération plus rapide.

**Fichier**: `backend/app/services/llm_client.py`

Simplifiez le prompt système pour réduire le contexte.

### Activer le cache Ollama

Ollama met en cache les prompts similaires. Si vous générez plusieurs fois le même type de code, ça ira plus vite après la première fois.

### Utiliser GPU

Si vous avez un GPU NVIDIA, Ollama l'utilisera automatiquement. Vérifiez avec:
```bash
ollama ps
```

Si vous voyez `GPU: 0/X GB`, c'est que le GPU est utilisé.

---

## Recommandation finale

**Pour l'instant (changement appliqué)**:
- ✅ Utilisez **Mistral 7B** pour tester rapidement
- ⏱️ Temps: ~1-2 minutes
- 📝 Qualité: Suffisante pour des tâches simples

**Si vous voulez le meilleur compromis vitesse/qualité**:
```bash
ollama pull deepseek-coder:6.7b-instruct
```

Puis changez dans `backend/app/core/config.py`:
```python
OLLAMA_MODEL_CODE: str = "deepseek-coder:6.7b-instruct"
```

**Si vous voulez la meilleure qualité** (peu importe le temps):
- Revenez à **devstral-small-2**

---

## Vérifier le modèle actuel

```bash
docker-compose logs backend | grep "model"
```

Ou regardez les logs lors d'une génération:
```bash
docker-compose logs backend -f
```

Vous verrez: `Using model: mistral:7b-instruct-q4_K_M`
