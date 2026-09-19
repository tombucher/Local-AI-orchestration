# Instructions de débogage

## Changements appliqués

J'ai ajouté des logs détaillés dans tous les handlers pour identifier les erreurs:

### Fonctions modifiées dans `/frontend/src/pages/Tasks/TaskDetail.tsx`

1. **handleAdjust** (ligne 110-126)
   - Ajoute `console.error()` en cas d'erreur
   - Affiche le message d'erreur détaillé dans le toast
   - Rafraîchit la tâche après succès

2. **handleReject** (ligne 128-144)
   - **FIX**: Utilise maintenant `rejectTask` au lieu de `cancelTask`
   - Ajoute `console.error()` en cas d'erreur
   - Affiche le message d'erreur détaillé dans le toast
   - Rafraîchit la tâche après succès

3. **handleStopGeneration** (ligne 165-181)
   - Ajoute `console.error()` en cas d'erreur
   - Affiche le message d'erreur détaillé dans le toast
   - Utilise `finally` pour toujours désactiver le loading

4. **Bouton Supprimer** (ligne 222-239)
   - Ajoute `console.error()` en cas d'erreur
   - Affiche le message d'erreur détaillé dans le toast

## Comment tester

### 1. Ouvrir la console du navigateur

1. Ouvrez l'application dans votre navigateur: http://localhost:5173
2. Appuyez sur **F12** ou **Ctrl+Shift+I** (Windows/Linux) ou **Cmd+Option+I** (Mac)
3. Allez dans l'onglet **Console**

### 2. Tester la suppression

1. Allez sur une tâche (n'importe laquelle)
2. Cliquez sur le bouton rouge **"Supprimer"**
3. Confirmez la suppression
4. **Regardez la console** pour voir s'il y a une erreur
5. Si ça ne fonctionne pas, vous verrez maintenant:
   ```
   Erreur suppression: <détails de l'erreur>
   ```

### 3. Tester la demande d'ajustement

1. Allez sur une tâche en status **MANUAL_REVIEW** (qui a du code généré)
2. Cliquez sur le bouton orange **"Demander ajustement"**
3. Remplissez les notes dans la modal
4. Cliquez sur **"Demander ajustement"**
5. **Regardez la console** pour voir s'il y a une erreur
6. Si ça ne fonctionne pas, vous verrez:
   ```
   Erreur handleAdjust: <détails de l'erreur>
   ```

### 4. Tester le rejet

1. Allez sur une tâche en status **MANUAL_REVIEW**
2. Cliquez sur le bouton rouge **"Rejeter"**
3. Remplissez les notes dans la modal
4. Cliquez sur **"Rejeter"**
5. **Regardez la console** pour voir s'il y a une erreur
6. Si ça ne fonctionne pas, vous verrez:
   ```
   Erreur handleReject: <détails de l'erreur>
   ```

### 5. Tester l'arrêt de génération

1. Créez une nouvelle tâche avec un prompt LLM
2. Cliquez sur **"Générer maintenant"**
3. Attendez que le timer démarre (quelques secondes)
4. Cliquez sur le bouton rouge **"Arrêter la génération"**
5. Confirmez
6. **Regardez la console** pour voir s'il y a une erreur
7. Si ça ne fonctionne pas, vous verrez:
   ```
   Erreur handleStopGeneration: <détails de l'erreur>
   ```

## Erreurs possibles et solutions

### Erreur 401 - Unauthorized

**Symptôme**: `Error 401: Could not validate credentials`

**Cause**: La session a expiré ou le token est invalide

**Solution**:
1. Déconnectez-vous
2. Reconnectez-vous
3. Réessayez

### Erreur 404 - Not Found

**Symptôme**: `Error 404: Task not found`

**Cause**:
- La tâche a déjà été supprimée
- L'ID de la tâche est incorrect
- Problème de permissions (la tâche appartient à un autre utilisateur)

**Solution**:
1. Rafraîchissez la page (F5)
2. Retournez à la liste des tâches
3. Vérifiez que vous êtes connecté avec le bon compte

### Erreur 400 - Bad Request

**Symptôme**: `Error 400: Can only stop tasks in GENERATING status`

**Cause**: Vous essayez d'arrêter une tâche qui n'est pas en train de générer

**Solution**:
- Normal, vous ne pouvez arrêter que les tâches en cours de génération

### Erreur réseau

**Symptôme**: `Network Error` ou `Failed to fetch`

**Cause**:
- Le backend n'est pas accessible
- Problème de CORS
- Le conteneur Docker est arrêté

**Solution**:
```bash
# Vérifier que tous les conteneurs tournent
docker-compose ps

# Redémarrer si nécessaire
docker-compose restart backend frontend
```

### Erreur 500 - Internal Server Error

**Symptôme**: `Error 500: Internal Server Error`

**Cause**: Erreur côté serveur (backend)

**Solution**:
1. Vérifier les logs backend:
```bash
docker-compose logs backend --tail 50
```

2. Chercher les lignes avec `ERROR` ou `Exception`

3. Si vous voyez une erreur de base de données, vérifier PostgreSQL:
```bash
docker-compose logs postgres --tail 20
```

## Logs backend utiles

### Voir tous les appels API en temps réel

```bash
docker-compose logs backend -f | grep "HTTP"
```

### Voir les erreurs uniquement

```bash
docker-compose logs backend -f | grep "ERROR"
```

### Voir les requêtes DELETE

```bash
docker-compose logs backend -f | grep "DELETE"
```

### Voir les requêtes POST (ajustement, rejet, arrêt)

```bash
docker-compose logs backend -f | grep "POST"
```

## Vérifications PostgreSQL

### Vérifier qu'une tâche existe avant de la supprimer

```bash
docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator -c "SELECT id, title, status FROM tasks WHERE id = 63;"
```

### Vérifier les logs d'une tâche

```bash
docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator -c "SELECT * FROM task_logs WHERE task_id = 63 ORDER BY timestamp DESC LIMIT 5;"
```

### Lister toutes les tâches

```bash
docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator -c "SELECT id, title, status FROM tasks ORDER BY id DESC LIMIT 10;"
```

## Que faire si rien ne fonctionne

1. **Redémarrez complètement le système**:
```bash
docker-compose down
docker-compose up -d
```

2. **Attendez 10 secondes** que tout démarre

3. **Vérifiez que tout est UP**:
```bash
docker-compose ps
```

4. **Videz le cache du navigateur**:
   - Chrome: Ctrl+Shift+Del → Cocher "Images et fichiers en cache" → Effacer
   - Firefox: Ctrl+Shift+Del → Cocher "Cache" → Effacer
   - Safari: Cmd+Option+E

5. **Rechargez la page en forçant**: Ctrl+F5 (ou Cmd+Shift+R sur Mac)

6. **Testez à nouveau** et **regardez la console**

## Contacter le support

Si après tout ça, ça ne fonctionne toujours pas, envoyez-moi:

1. Le message d'erreur **exact** de la console du navigateur
2. Le message d'erreur **exact** des logs backend
3. Les étapes **exactes** pour reproduire le problème

Je pourrai alors identifier et corriger le bug précis.
