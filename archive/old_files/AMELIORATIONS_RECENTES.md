# Améliorations récentes - 31 décembre 2025

## Problèmes résolus

### 1. Performance et stabilité du système ✅

**Problème**: Le système se bloquait et l'ordinateur chauffait beaucoup lors de la génération de code.

**Solutions appliquées**:
- Réduction du `ORCHESTRATOR_BATCH_SIZE` de 5 à 1 pour éviter la surcharge CPU
- Augmentation de l'intervalle d'auto-refresh de 5 à 10 secondes dans TaskDetail
- Correction d'une boucle infinie dans `useEffect` (retrait de `fetchTask` des dépendances)

**Fichiers modifiés**:
- `backend/app/core/config.py` (ligne 48)
- `frontend/src/pages/Tasks/TaskDetail.tsx` (lignes 35, 48, 59)

---

### 2. Génération de code non-bloquante ✅

**Problème**: Lorsqu'on cliquait sur "Générer maintenant", l'interface se figeait pendant 3-4 minutes.

**Solution**: Implémentation d'une génération asynchrone via `BackgroundTasks` de FastAPI:
- L'endpoint `/generate` retourne immédiatement avec le status `GENERATING`
- La génération se fait en arrière-plan
- Le frontend affiche instantanément le timer et la barre de progression
- Auto-refresh toutes les 10 secondes pour suivre l'avancement

**Fichiers modifiés**:
- `backend/app/api/v1/tasks.py` - Ajout de `BackgroundTasks` et fonction `_generate_code_background`
- `backend/app/core/database.py` - Export de `async_session_maker`
- `frontend/src/pages/Tasks/TaskDetail.tsx` - Simplification de `handleGenerate`

**Bénéfices**:
- Interface toujours réactive
- Feedback immédiat à l'utilisateur
- Possibilité de naviguer pendant la génération

---

### 3. Indicateur d'état du service ✅

**Problème**: Impossible de savoir ce que fait le système (tâches en cours, en attente, etc.)

**Solution**: Nouveau composant `ServiceStatus` dans le Dashboard:
- Affiche le nombre de tâches en génération (avec spinner animé)
- Affiche les tâches en attente de validation
- Affiche les tâches en file d'attente
- Affiche les tâches terminées
- Auto-refresh toutes les 30 secondes

**Fichiers créés**:
- `frontend/src/components/ServiceStatus.tsx`

**Fichiers modifiés**:
- `frontend/src/pages/Dashboard.tsx` - Intégration du composant
- `frontend/src/services/tasks.ts` - Ajout de `getServiceStats()`

**Endpoint backend**: `GET /api/v1/tasks/stats/service`

---

### 4. Suppression de tâches ✅

**Statut**: La suppression de tâches était déjà fonctionnelle, code vérifié et confirmé.

**Endpoint**: `DELETE /api/v1/tasks/{task_id}`
**Frontend**: Bouton "Supprimer" dans TaskDetail.tsx (ligne 205-221)

---

## Utilisation

### Démarrer le système

```bash
docker-compose up -d
```

### Vérifier l'état

```bash
docker-compose ps
```

Tous les containers doivent être `Up` et `healthy`:
- `orchestrator-backend` (port 8000)
- `orchestrator-frontend` (port 5173)
- `orchestrator-postgres` (port 5432)
- `open-webui` (port 3001)

### Générer du code pour une tâche

1. Créer une tâche en status `READY`
2. Aller sur la page de détail de la tâche
3. Cliquer sur "Générer maintenant"
4. L'interface affiche immédiatement un timer et une barre de progression
5. La page se rafraîchit automatiquement toutes les 10 secondes
6. Après 3-4 minutes, le code apparaît avec le status `MANUAL_REVIEW`

### Surveiller l'état du système

- Aller sur le Dashboard (`/dashboard`)
- La carte "État du service" affiche en temps réel:
  - 🟡 Tâches en génération (avec animation)
  - 🔵 Tâches en attente de validation
  - ⚫ Tâches en file d'attente
  - 🟢 Tâches terminées

---

## Configuration

### Paramètres de performance

Dans `backend/app/core/config.py`:

```python
ORCHESTRATOR_INTERVAL_MINUTES: int = 5  # Intervalle du scheduler (5 min)
ORCHESTRATOR_BATCH_SIZE: int = 1        # Nombre de tâches traitées en parallèle
```

**Recommandation**: Garder `BATCH_SIZE = 1` pour éviter la surcharge CPU avec Ollama.

### Modèles Ollama

```python
OLLAMA_HOST: str = "http://host.docker.internal:11434"
OLLAMA_MODEL_DEVSTRAL: str = "devstral-small-2"  # Pour génération de code
OLLAMA_MODEL_MISTRAL: str = "mistral:7b-instruct-q4_K_M"  # Pour prompts
```

---

## Logs et débogage

### Voir les logs backend
```bash
docker-compose logs backend --tail 50 -f
```

### Voir les logs en temps réel
```bash
docker-compose logs -f
```

### Vérifier qu'Ollama est accessible
```bash
curl http://localhost:11434/api/tags
```

### Vérifier les tâches en cours
```bash
docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator -c "SELECT id, title, status FROM tasks ORDER BY created_at DESC LIMIT 5;"
```

---

## Prochaines améliorations possibles

1. **Notifications**: Alerter l'utilisateur quand une génération est terminée
2. **Annulation**: Permettre d'annuler une génération en cours
3. **Retry automatique**: Relancer automatiquement les tâches en échec
4. **Historique**: Garder un historique des générations précédentes
5. **Métriques**: Temps moyen de génération, taux de succès, etc.

---

## Support

En cas de problème:
1. Vérifier que tous les containers sont `Up`
2. Consulter les logs backend
3. Vérifier qu'Ollama est accessible
4. S'assurer que les modèles sont téléchargés dans Ollama
