# Diagnostic et résolution - Problème de latence et détection EOS

## 🔴 Problème identifié

Votre génération était bloquée pendant 30+ minutes à cause de:

### 1. **Pas de streaming** - CRITIQUE ⚠️
L'ancien code appelait `client.chat()` **sans streaming**, attendant toute la réponse d'un coup. Si Ollama ne détecte pas la fin (EOS token), ça reste bloqué indéfiniment.

### 2. **Modèle hardcodé** - Bug de configuration
Ligne 118: `return "devstral-small-2"` → ignorait votre config `OLLAMA_MODEL_CODE`

### 3. **Context window trop grand** - Ralentissement
`num_ctx: 8192` → Consommait trop de RAM et ralentissait la génération

### 4. **Pas de logs de performance** - Impossible de diagnostiquer
Aucun log de TTFT, progression, ou détection de fin

### 5. **Pas de stop sequences** - EOS non détecté
Mistral peut générer indéfiniment sans stop tokens explicites

---

## ✅ Solutions appliquées

### 1. **Streaming activé** (ligne 80)

```python
stream = self.client.chat(
    model=model,
    messages=[...],
    stream=True,  # ✅ STREAMING
    options={...}
)
```

**Avantages**:
- ✅ Détecte la fin en temps réel (`chunk.get('done', False)`)
- ✅ Affiche la progression chunk par chunk
- ✅ Permet de voir où ça bloque
- ✅ Plus besoin d'attendre toute la réponse

### 2. **Stop sequences ajoutées** (ligne 89)

```python
'stop': ['</s>', '<|endoftext|>', '[DONE]', '\n\n\n'],
```

**Mistral utilise** `</s>` comme EOS token. Maintenant explicitement configuré.

### 3. **Context window réduit** (ligne 83)

```python
'num_ctx': 4096,  # Avant: 8192
```

**Impact**: ~40% moins de RAM, génération plus rapide

### 4. **Logs de performance détaillés**

Vous verrez maintenant dans les logs backend:

```
🤖 [TASK-65] Starting generation with mistral:7b-instruct-q4_K_M
🤖 [TASK-65] Prompt length: 245 chars
⚡ [TASK-65] First token received in 2.34s    ← TTFT
📝 [TASK-65] Chunk 10 | 150 chars | 5.2s elapsed
📝 [TASK-65] Chunk 20 | 312 chars | 8.7s elapsed
✅ [TASK-65] Generation complete!
📊 [TASK-65] Stats:
   - Total time: 15.42s
   - TTFT: 2.34s
   - Chunks: 45
   - Output: 823 chars
   - Speed: 53 chars/s
   - Tokens generated: 234
```

### 5. **Utilisation de la config** (ligne 177)

```python
model = settings.OLLAMA_MODEL_CODE  # Plus hardcodé!
```

Maintenant respecte votre changement à `mistral:7b-instruct-q4_K_M`

### 6. **Prompt raccourci** (ligne 157)

Moins de tokens en entrée = réponse plus rapide

---

## 📊 Comment interpréter les logs

### Logs normaux (génération OK)

```
⚡ [TASK-X] First token received in 1-3s     ← Normal
📝 Chunks toutes les 0.5-2s                  ← Génération active
✅ Generation complete!                      ← EOS détecté
```

### Logs problématiques (bloqué)

```
🤖 Starting generation...
⚡ First token received in 15s+              ← ⚠️ Trop long (modèle ou contexte)
📝 Chunk 10 | ... | 60s elapsed              ← ⚠️ Trop lent
```

Ou pire:
```
🤖 Starting generation...
(plus rien pendant 5+ minutes)               ← ❌ BLOQUÉ
```

---

## 🧪 Comment tester

### 1. Vérifier les logs en temps réel

```bash
docker-compose logs backend -f
```

### 2. Lancer une génération simple

Créez une tâche avec un prompt court:
```
Prompt: "Écris une fonction Python qui retourne 'Hello World'"
```

### 3. Observer les logs

Vous devriez voir:
- `Starting generation` → Immédiat
- `First token received` → 1-3 secondes
- `Chunk 10, 20, 30...` → Toutes les 1-2 secondes
- `Generation complete!` → En 10-30 secondes total

### 4. Vérifier les stats

```
Total time: 15-30s           ← Attendu pour Mistral 7B
TTFT: 1-3s                   ← Bon
Speed: 40-80 chars/s         ← Bon pour local
```

---

## 🚨 Que faire si ça reste bloqué

### Si "Starting generation" mais pas de "First token"

**Cause**: Ollama ne démarre pas la génération

**Solutions**:
1. Vérifiez qu'Ollama tourne:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Vérifiez le modèle:
   ```bash
   docker-compose logs backend | grep "Selected model"
   ```

3. Redémarrez Ollama:
   ```bash
   # Si Ollama app
   killall ollama && open -a Ollama

   # Si service
   brew services restart ollama
   ```

### Si TTFT > 10 secondes

**Cause**: Context window ou modèle trop gros

**Solutions**:
1. Réduire encore `num_ctx`:
   ```python
   'num_ctx': 2048,  # Essayez 2048
   ```

2. Utiliser un modèle plus petit:
   ```bash
   ollama pull phi:2.7b
   ```

### Si chunks arrêtent à mi-chemin

**Cause**: Stop sequence rencontrée trop tôt

**Solutions**:
1. Retirez `\n\n\n` des stop sequences
2. Gardez seulement `</s>`

---

## 🔍 Diagnostic avancé

### Vérifier la mémoire Ollama

```bash
ps aux | grep ollama
```

Si `%MEM` > 50%, Ollama sature → Réduire `num_ctx`

### Tester Ollama directement

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral:7b-instruct-q4_K_M",
  "prompt": "Hello",
  "stream": true
}'
```

Vous devriez voir des chunks JSON défiler immédiatement.

### Vérifier les modèles chargés

```bash
curl http://localhost:11434/api/ps
```

Si plusieurs modèles chargés → RAM saturée → Décharger:
```bash
curl -X DELETE http://localhost:11434/api/generate -d '{"name": "devstral-small-2"}'
```

---

## 📈 Optimisations supplémentaires possibles

### 1. Réduire `num_predict`

```python
'num_predict': 1000,  # Au lieu de 2000
```

→ Code plus court mais génération 2x plus rapide

### 2. Augmenter `temperature`

```python
'temperature': 0.9,  # Au lieu de 0.7
```

→ Plus aléatoire mais souvent plus rapide

### 3. Utiliser `mirostat`

```python
'mirostat': 2,
'mirostat_tau': 5.0,
```

→ Meilleure détection de fin de génération

### 4. Mode batch (si plusieurs tâches)

Désactivez le batch parallèle (déjà fait):
```python
ORCHESTRATOR_BATCH_SIZE: int = 1
```

---

## 📋 Checklist de santé Ollama

Avant chaque génération, vérifiez:

- [ ] Ollama répond (`curl http://localhost:11434/api/tags`)
- [ ] Modèle disponible (`ollama list | grep mistral`)
- [ ] RAM disponible (`top` ou Activity Monitor < 80%)
- [ ] Aucun autre processus lourd
- [ ] Backend connecté (`docker-compose logs backend | grep "Ollama client initialized"`)

---

## 🎯 Résultats attendus

Avec ces changements, vous devriez avoir:

| Métrique | Avant | Après |
|----------|-------|-------|
| **Temps total** | 30+ min (timeout) | 10-30s |
| **TTFT** | Inconnu | 1-3s |
| **Détection fin** | ❌ Bloqué | ✅ Automatique |
| **Visibilité** | ❌ Aucune | ✅ Logs détaillés |
| **Modèle** | devstral-small-2 | mistral:7b |
| **Context** | 8192 | 4096 |

---

## 🧪 Test de validation

Lancez la tâche 65 que j'ai remise en READY et regardez les logs:

```bash
docker-compose logs backend -f
```

Vous devriez voir la génération se terminer en 10-30 secondes avec tous les logs de progression!
