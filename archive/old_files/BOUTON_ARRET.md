# Bouton d'arrêt de génération

## Fonctionnalité ajoutée

Un bouton rouge **"Arrêter la génération"** a été ajouté pour interrompre une génération de code en cours.

## Comment ça fonctionne

### Interface utilisateur

Lorsqu'une tâche est en cours de génération (status `GENERATING`), vous verrez maintenant:
- Un timer qui compte le temps écoulé
- Une barre de progression animée
- **Un bouton rouge "Arrêter la génération"**

### Comportement

Quand vous cliquez sur le bouton:
1. Une confirmation vous est demandée
2. Si vous confirmez, la génération est immédiatement arrêtée
3. La tâche revient en status `READY`
4. Vous pouvez relancer la génération plus tard si nécessaire

## Implémentation technique

### Backend - Nouvel endpoint

**Endpoint**: `POST /api/v1/tasks/{task_id}/stop`

**Fichier**: `backend/app/api/v1/tasks.py` (ligne 526-583)

```python
@router.post("/{task_id}/stop", response_model=TaskResponse)
async def stop_generation(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Arrêter une génération en cours
    Remet la tâche en status READY si elle est en GENERATING
    """
    # Vérification que la tâche est en GENERATING
    # Reset du status à READY
    # Nettoyage du code généré partiel
    # Création d'un log
```

**Validation**: Ne fonctionne que si la tâche est en status `GENERATING`.

### Frontend

**Service**: `frontend/src/services/tasks.ts` (ligne 89-92)
```typescript
stopGeneration: async (id: number): Promise<Task> => {
  const response = await api.post<Task>(`/api/v1/tasks/${id}/stop`);
  return response.data;
}
```

**Store**: `frontend/src/stores/tasksStore.ts` (ligne 207-221)
```typescript
stopGeneration: async (id) => {
  // Appel du service
  // Mise à jour de la tâche dans l'état
  // Gestion des erreurs
}
```

**Interface**: `frontend/src/pages/Tasks/TaskDetail.tsx`
- Handler: ligne 155-170
- Bouton: ligne 331-338

## Exemple d'utilisation

1. **Créer une tâche** avec un prompt LLM
2. **Lancer la génération** (bouton "Générer maintenant")
3. **Attendre quelques secondes** pour voir le timer démarrer
4. **Cliquer sur "Arrêter la génération"** (bouton rouge)
5. **Confirmer** l'arrêt
6. La tâche revient en status `READY`

## Raisons d'arrêter une génération

- La génération prend trop de temps
- Vous avez changé d'avis sur le prompt
- Le système devient trop lent
- Vous voulez modifier la tâche avant de la générer
- Test rapide de la fonctionnalité

## Ce qui se passe techniquement

### Côté backend
```
1. Vérification que task.status == GENERATING
2. task.status = READY
3. task.started_at = None
4. task.generated_code = None
5. Création d'un log STATUS_CHANGED
6. Commit en base de données
```

### Côté frontend
```
1. Appel de stopGeneration(task.id)
2. Confirmation utilisateur
3. Toast de succès
4. Mise à jour automatique de l'interface
5. Le bouton "Arrêter" disparaît
6. Le bouton "Générer maintenant" réapparaît
```

## Notes importantes

- ⚠️ Le code partiellement généré est supprimé
- ⚠️ Vous ne pouvez pas reprendre la génération là où elle s'est arrêtée
- ✅ Pas de perte de données (la tâche et le prompt sont conservés)
- ✅ Vous pouvez relancer la génération à tout moment
- ✅ Un log est créé pour tracer l'arrêt

## Limitations

- **Ne tue pas le processus Ollama**: Si Ollama est en train de générer, il continuera jusqu'à la fin, mais le résultat sera ignoré
- **Action irréversible**: Une fois arrêtée, vous devez relancer depuis le début

## Alternative

Si vous voulez simplement **annuler définitivement** une tâche (pas juste arrêter la génération), utilisez le bouton "Annuler" qui existe déjà. Cela mettra la tâche en status `CANCELLED`.

## Différence Cancel vs Stop

| Action | Endpoint | Status final | Peut relancer? |
|--------|----------|-------------|----------------|
| **Arrêter** | `/stop` | `READY` | ✅ Oui |
| **Annuler** | `/cancel` | `CANCELLED` | ❌ Non |

## Résultat visuel

Avant (pendant génération):
```
┌─────────────────────────────────────┐
│ 🔄 Ollama génère le code...         │
│ ████████████░░░░░░░░░  2:34         │
│ La génération prend 3-4 minutes...  │
│ [🛑 Arrêter la génération]          │ ← NOUVEAU
└─────────────────────────────────────┘
```

Après arrêt:
```
┌─────────────────────────────────────┐
│ Status: READY                        │
│ [▶️ Générer maintenant]              │
└─────────────────────────────────────┘
```

## Logs générés

Un log de type `STATUS_CHANGED` est créé avec les détails:
```json
{
  "old_status": "GENERATING",
  "new_status": "READY",
  "reason": "Generation stopped by user"
}
```

Vous pouvez voir ces logs dans la section "Historique" de la tâche.
