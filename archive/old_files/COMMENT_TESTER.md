# Comment tester la fonctionnalité Settings

## 🚀 Test rapide (2 minutes)

### 1. Ouvrir l'application

Dans votre navigateur: **http://localhost:5173**

### 2. Se connecter

Utilisez vos identifiants habituels.

### 3. Aller dans Paramètres

Dans la sidebar à gauche, cliquez sur **"Paramètres"** (icône ⚙️)

### 4. Voir les modèles disponibles

Vous devriez voir une liste de tous vos modèles Ollama installés avec:
- Le nom du modèle
- La taille en GB
- La date de modification
- Un badge "Actif" sur le modèle actuellement sélectionné

### 5. Changer de modèle

Cliquez sur un autre modèle pour le sélectionner.

Un message vert "Paramètres mis à jour avec succès !" devrait apparaître.

### 6. Vérifier que ça marche

**Option A - Via l'interface**:
1. Allez dans un projet
2. Créez une nouvelle tâche
3. Cliquez sur "Générer maintenant"

**Option B - Via les logs**:
```bash
docker-compose logs backend -f
```

Cherchez cette ligne:
```
📦 [TASK-X] Selected model: VOTRE_MODELE
```

---

## 🎯 C'est tout!

Si vous voyez le nom du modèle que vous avez sélectionné dans les logs, ça fonctionne parfaitement!

---

## 📦 Installer un nouveau modèle (optionnel)

Si vous voulez tester avec d'autres modèles:

```bash
# Modèles rapides pour le code
ollama pull codellama:7b-instruct
ollama pull deepseek-coder:6.7b-instruct

# Modèle général rapide
ollama pull mistral:7b-instruct
```

Après l'installation, rafraîchissez la page Settings pour voir le nouveau modèle!

---

## ❓ Problème?

### La page Settings est vide
→ Vérifiez qu'Ollama tourne: `ollama list`

### Le modèle ne change pas
→ Vérifiez les logs backend: `docker-compose logs backend -f`

### Erreur "Failed to load settings"
→ Vérifiez que le backend est accessible: `curl http://localhost:8000/`
