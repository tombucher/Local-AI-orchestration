# Test de la fonctionnalité Settings

## ✅ Implémentation terminée

### Backend
- ✅ Modèle `UserSettings` créé
- ✅ Migration de base de données appliquée
- ✅ API endpoints créés (`/api/v1/settings/*`)
- ✅ Intégration dans la génération de code
- ✅ Backend redémarré

### Frontend
- ✅ Types TypeScript créés (`types/settings.ts`)
- ✅ Service API créé (`services/settingsApi.ts`)
- ✅ Page Settings créée (`pages/Settings.tsx`)
- ✅ Route ajoutée dans App.tsx
- ✅ Lien ajouté dans Sidebar
- ✅ Frontend redémarré

---

## 🧪 Comment tester

### 1. Accéder à la page Settings

1. Ouvrez votre navigateur: http://localhost:5173
2. Connectez-vous avec vos identifiants
3. Cliquez sur **"Paramètres"** dans la sidebar (icône ⚙️)

### 2. Fonctionnalités disponibles

La page Settings vous permet de:
- ✅ Voir tous les modèles Ollama installés sur votre machine
- ✅ Voir le modèle actuellement sélectionné (badge "Actif")
- ✅ Changer de modèle en cliquant sur un autre modèle
- ✅ Voir la taille et la date de modification de chaque modèle

### 3. Test du workflow complet

1. **Changez de modèle**:
   - Allez dans Paramètres
   - Sélectionnez un modèle différent (ex: `codellama:7b-instruct` si installé)
   - Vérifiez que le message "Paramètres mis à jour avec succès !" apparaît

2. **Créez une tâche**:
   - Allez dans Projets
   - Sélectionnez un projet
   - Créez une nouvelle tâche avec un prompt simple
   - Cliquez sur "Générer maintenant"

3. **Vérifiez le modèle utilisé**:
   ```bash
   docker-compose logs backend -f
   ```

   Vous devriez voir:
   ```
   📦 [TASK-X] Selected model: codellama:7b-instruct
   ```

---

## 🎨 Aperçu de l'interface

La page Settings affiche:
- **Header** avec icône Settings et titre
- **Section principale** avec:
  - Liste des modèles sous forme de cartes radio
  - Badge "Actif" sur le modèle sélectionné
  - Informations: nom, taille, date de modification
  - Messages de succès/erreur
  - Spinner de chargement
- **Section info** avec conseils pour choisir un modèle

---

## 📊 Modèles disponibles

Pour voir quels modèles sont installés:
```bash
ollama list
```

Pour installer un nouveau modèle (exemples):
```bash
# Modèles rapides et légers (recommandés)
ollama pull codellama:7b-instruct
ollama pull deepseek-coder:6.7b-instruct

# Modèles plus lourds mais meilleurs
ollama pull codellama:13b-instruct
ollama pull deepseek-coder:33b-instruct
```

---

## 🔍 Test des endpoints API (optionnel)

Si vous voulez tester les endpoints directement:

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "VOTRE_PASSWORD"}' \
  | jq -r '.access_token')

# 2. Lister les modèles
curl -s -X GET "http://localhost:8000/api/v1/settings/ollama-models" \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Voir vos paramètres
curl -s -X GET "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Changer de modèle
curl -s -X PUT "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ollama_model_code": "codellama:7b-instruct"}' | jq
```

---

## ✨ Améliorations futures possibles

- [ ] Afficher le modèle utilisé dans la liste des tâches
- [ ] Permettre de choisir différents modèles par projet
- [ ] Ajouter un bouton "Tester le modèle" pour vérifier qu'il fonctionne
- [ ] Afficher des statistiques de performance par modèle
- [ ] Ajouter une validation pour s'assurer que le modèle existe
- [ ] Permettre de configurer `ollama_model_text` pour usage futur

---

## 🐛 Debugging

### Si la page Settings ne charge pas les modèles

1. Vérifiez qu'Ollama tourne:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Vérifiez que le backend peut accéder à Ollama:
   ```bash
   docker-compose logs backend | grep "Ollama"
   ```

3. Vérifiez les logs du frontend:
   ```bash
   docker-compose logs frontend -f
   ```

### Si le changement de modèle ne fonctionne pas

1. Vérifiez les logs backend:
   ```bash
   docker-compose logs backend -f
   ```

2. Vérifiez la console du navigateur (F12) pour les erreurs JavaScript

3. Vérifiez que l'utilisateur a bien des paramètres:
   ```bash
   docker exec orchestrator-postgres psql -U orchestrator_user -d orchestrator \
     -c "SELECT * FROM user_settings;"
   ```

---

## 🎉 Résumé

Vous avez maintenant une interface graphique complète pour:
1. **Voir** tous vos modèles Ollama installés
2. **Sélectionner** le modèle à utiliser pour la génération de code
3. **Valider** que le bon modèle est utilisé lors de la génération

Le système utilisera automatiquement votre modèle préféré pour toutes les futures générations de code!

Bon test! 🚀
