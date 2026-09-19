# Bug Fix - Commit manquant après génération

## 🐛 Problème identifié

Lorsque vous cliquez sur "Générer maintenant" dans le frontend, la génération se termine avec succès dans les logs backend, **mais** :

- Le frontend continue de "mouliner" indéfiniment
- La tâche reste bloquée en status `GENERATING` dans la base de données
- Le code généré n'est jamais sauvegardé

## 🔍 Cause racine

Dans `/backend/app/api/v1/tasks.py`, fonction `_generate_code_background()` (ligne 312-349) :

```python
async def _generate_code_background(task_id: int):
    async with async_session_maker() as db:
        try:
            # ... code ...

            # Lancer la génération
            await orchestrator.handle_task(task)

            # ❌ MANQUE: await db.commit()

        except Exception as e:
            # ...
```

La fonction `handle_task()` met à jour la tâche (status → MANUAL_REVIEW, code généré), mais sans `commit()`, les changements restent en mémoire et ne sont **jamais persistés** en base de données.

## ✅ Solution appliquée

**Fichier** : `/backend/app/api/v1/tasks.py` (ligne 341-342)

```python
# Lancer la génération
await orchestrator.handle_task(task)

# CRITIQUE: Commit pour sauvegarder le status MANUAL_REVIEW
await db.commit()
```

## 📊 Différence avec `process_queue()`

Le job automatique `process_queue()` **fonctionne correctement** car il fait un commit à la fin :

```python
# backend/app/services/orchestrator.py ligne 83
async def process_queue(...):
    for task in tasks:
        try:
            await self.handle_task(task)
            success_count += 1
        except Exception as e:
            await self.handle_failure(task, e)

    await self.db.commit()  # ✅ Commit présent
```

Mais quand on clique sur "Générer maintenant", ça appelle `_generate_code_background()` qui n'avait **pas** de commit.

## 🧪 Comment tester

1. **Créer une tâche** avec prompt "test"
2. **Cliquer sur "Générer maintenant"**
3. **Observer les logs** :
   ```bash
   docker-compose logs backend -f
   ```
4. **Vérifier la base de données** après ~30 secondes :
   ```bash
   docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator -c "SELECT id, status FROM tasks WHERE id = 66;"
   ```

**Avant le fix** :
- Logs backend : "✅ Generation complete!"
- Base de données : status = `GENERATING` (bloqué)
- Frontend : Spinner infini

**Après le fix** :
- Logs backend : "✅ Generation complete!"
- Base de données : status = `MANUAL_REVIEW`
- Frontend : Affiche le code généré

## 🔄 Actions effectuées

1. ✅ Ajouté `await db.commit()` après `orchestrator.handle_task(task)` (ligne 342)
2. ✅ Redémarré le backend : `docker-compose restart backend`
3. ✅ Corrigé la tâche 66 bloquée : `UPDATE tasks SET status = 'READY' WHERE id = 66`

## 📝 Résumé

**Symptôme** : Frontend "mouline" pendant 3+ minutes après une génération réussie

**Cause** : Commit manquant dans la tâche background

**Fix** : Ajout de `await db.commit()` après la génération

**Statut** : ✅ **Résolu** - Testé et prêt à valider
