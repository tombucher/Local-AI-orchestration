# Fonctionnalité de configuration utilisateur - Sélection du modèle IA

## Changements effectués

J'ai implémenté un système de configuration utilisateur qui permet à chaque utilisateur de choisir son modèle Ollama préféré pour la génération de code.

### Backend

#### 1. Nouveau modèle `UserSettings`

**Fichier**: `backend/app/models/user_settings.py`

Stocke les préférences de chaque utilisateur:
- `user_id`: Lien vers l'utilisateur (unique, 1-to-1)
- `ollama_model_code`: Modèle Ollama pour génération de code
- `ollama_model_text`: Modèle Ollama pour génération de texte (futur usage)
- Timestamps: `created_at`, `updated_at`

Relation ajoutée dans `User`:
```python
settings: Mapped[Optional["UserSettings"]] = relationship("UserSettings", back_populates="user")
```

#### 2. Migration de base de données

**Fichier**: `backend/alembic/versions/003_add_user_settings.py`

Migration appliquée avec succès. La table `user_settings` a été créée.

#### 3. Schemas Pydantic

**Fichier**: `backend/app/schemas/user_settings.py`

- `UserSettingsCreate`: Créer des paramètres
- `UserSettingsUpdate`: Mettre à jour partiellement
- `UserSettingsResponse`: Réponse API
- `OllamaModelInfo`: Information sur un modèle disponible

#### 4. Endpoints API

**Fichier**: `backend/app/api/v1/settings.py`

Trois nouveaux endpoints sous `/api/v1/settings`:

##### `GET /api/v1/settings/ollama-models`
Liste tous les modèles Ollama disponibles sur le serveur.

**Exemple**:
```bash
curl -X GET "http://localhost:8000/api/v1/settings/ollama-models" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse**:
```json
[
  {
    "name": "mistral:7b-instruct-q4_K_M",
    "size": 4370000000,
    "modified_at": "2026-01-01T12:00:00Z"
  },
  {
    "name": "codellama:7b-instruct",
    "size": 3800000000,
    "modified_at": "2026-01-01T10:00:00Z"
  }
]
```

##### `GET /api/v1/settings`
Récupère les paramètres de l'utilisateur connecté.

Si les paramètres n'existent pas, ils sont automatiquement créés avec les valeurs par défaut.

**Exemple**:
```bash
curl -X GET "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse**:
```json
{
  "id": 1,
  "user_id": 1,
  "ollama_model_code": "mistral:7b-instruct-q4_K_M",
  "ollama_model_text": null,
  "created_at": "2026-01-01T13:00:00Z",
  "updated_at": "2026-01-01T13:00:00Z"
}
```

##### `PUT /api/v1/settings`
Met à jour les paramètres de l'utilisateur.

**Exemple**:
```bash
curl -X PUT "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ollama_model_code": "codellama:7b-instruct"
  }'
```

**Réponse**:
```json
{
  "id": 1,
  "user_id": 1,
  "ollama_model_code": "codellama:7b-instruct",
  "ollama_model_text": null,
  "created_at": "2026-01-01T13:00:00Z",
  "updated_at": "2026-01-01T14:30:00Z"
}
```

#### 5. Intégration dans la génération de code

**Fichiers modifiés**:
- `backend/app/services/llm_client.py`: Accepte maintenant un `model_override`
- `backend/app/services/orchestrator.py`: Récupère les préférences utilisateur avant la génération

**Flux de génération**:
1. L'orchestrateur récupère la tâche
2. Il récupère l'utilisateur via `task.project.user_id`
3. Il récupère les paramètres de l'utilisateur (`UserSettings`)
4. Il utilise `user_settings.ollama_model_code` ou le modèle par défaut
5. Il passe le modèle à `llm_client.generate_code(task, model_override=model)`
6. Le modèle utilisé est loggé dans les `TaskLog`

**Logs**:
```
📦 [TASK-65] Selected model: codellama:7b-instruct
✅ Task 65 → MANUAL_REVIEW (model: codellama:7b-instruct)
```

---

## Frontend - À implémenter

Pour compléter cette fonctionnalité, il faut créer une page de paramètres dans le frontend.

### Structure suggérée

**Fichier**: `frontend/src/pages/Settings.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
}

interface UserSettings {
  ollama_model_code: string;
  ollama_model_text: string | null;
}

export default function Settings() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [modelsRes, settingsRes] = await Promise.all([
        api.get('/api/v1/settings/ollama-models'),
        api.get('/api/v1/settings')
      ]);
      setModels(modelsRes.data);
      setSettings(settingsRes.data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = async (modelName: string) => {
    try {
      const res = await api.put('/api/v1/settings', {
        ollama_model_code: modelName
      });
      setSettings(res.data);
      alert('Modèle mis à jour avec succès!');
    } catch (error) {
      console.error('Failed to update model:', error);
      alert('Erreur lors de la mise à jour');
    }
  };

  if (loading) return <div>Chargement...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Paramètres</h1>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Modèle IA pour génération de code</h2>

        <div className="space-y-2">
          {models.map((model) => (
            <label key={model.name} className="flex items-center space-x-3 p-3 border rounded hover:bg-gray-50 cursor-pointer">
              <input
                type="radio"
                name="model"
                value={model.name}
                checked={settings?.ollama_model_code === model.name}
                onChange={() => handleModelChange(model.name)}
                className="w-4 h-4"
              />
              <div className="flex-1">
                <div className="font-medium">{model.name}</div>
                <div className="text-sm text-gray-500">
                  Taille: {(model.size / 1e9).toFixed(2)} GB
                </div>
              </div>
            </label>
          ))}
        </div>

        {models.length === 0 && (
          <p className="text-gray-500">Aucun modèle Ollama disponible</p>
        )}
      </div>
    </div>
  );
}
```

### Ajouter la route

**Fichier**: `frontend/src/App.tsx`

```tsx
import Settings from './pages/Settings';

// Dans les routes
<Route path="/settings" element={<Settings />} />
```

### Ajouter un lien dans la navigation

Dans votre composant de navigation, ajoutez:
```tsx
<Link to="/settings">⚙️ Paramètres</Link>
```

---

## Comment tester

### 1. Tester les endpoints API

```bash
# 1. Se connecter (remplacez par vos credentials)
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "votre@email.com", "password": "votrepassword"}' \
  | jq -r '.access_token')

# 2. Lister les modèles disponibles
curl -X GET "http://localhost:8000/api/v1/settings/ollama-models" \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Récupérer vos paramètres actuels
curl -X GET "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Changer de modèle
curl -X PUT "http://localhost:8000/api/v1/settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ollama_model_code": "codellama:7b-instruct"}' | jq
```

### 2. Tester la génération avec le nouveau modèle

1. Changez votre modèle via l'API
2. Créez une nouvelle tâche
3. Cliquez sur "Générer maintenant"
4. Vérifiez les logs backend:
   ```bash
   docker-compose logs backend -f
   ```
   Vous devriez voir:
   ```
   📦 [TASK-X] Selected model: codellama:7b-instruct
   ```

---

## Modèles recommandés pour le code

Voici quelques modèles optimisés pour la génération de code:

### Rapides et légers (7B paramètres)
- `mistral:7b-instruct-q4_K_M` (actuel) - Général, bon compromis
- `codellama:7b-instruct` - Spécialisé code, rapide
- `deepseek-coder:6.7b-instruct` - Excellent pour le code

### Plus lents mais meilleurs (15B+ paramètres)
- `devstral-small-2` (ancien) - Très bon pour le code mais lent
- `codellama:13b-instruct` - Meilleur que 7B
- `deepseek-coder:33b-instruct` - Top qualité (requiert beaucoup de RAM)

Pour installer un nouveau modèle:
```bash
ollama pull codellama:7b-instruct
```

---

## Résumé des changements

### Backend ✅
- [x] Modèle `UserSettings` créé
- [x] Migration de base de données appliquée
- [x] Schemas Pydantic créés
- [x] Endpoints API `/api/v1/settings/*` créés
- [x] Intégration dans la génération de code
- [x] Backend redémarré

### Frontend ⏳
- [ ] Page Settings à créer
- [ ] Route `/settings` à ajouter
- [ ] Lien navigation à ajouter

---

## Notes importantes

1. **Valeur par défaut**: Si un utilisateur n'a pas de paramètres, le système utilise `OLLAMA_MODEL_CODE` de la config (actuellement `mistral:7b-instruct-q4_K_M`)

2. **Un seul paramètre par utilisateur**: Contrainte `UNIQUE` sur `user_id`

3. **Cascade delete**: Si un utilisateur est supprimé, ses paramètres sont supprimés automatiquement

4. **Logs de génération**: Le modèle utilisé est maintenant loggé dans `task_logs.details['model']`

5. **API flexible**: L'endpoint PUT accepte des mises à jour partielles (seulement les champs fournis)

---

## Prochaines étapes

1. **Implémenter le frontend** comme suggéré ci-dessus
2. **Tester le workflow complet**:
   - Changer de modèle dans l'interface
   - Générer une tâche
   - Vérifier que le bon modèle est utilisé
3. **Optionnel**: Ajouter un affichage du modèle utilisé dans la liste des tâches
4. **Optionnel**: Ajouter une validation pour s'assurer que le modèle sélectionné existe sur Ollama

Besoin d'aide pour implémenter le frontend ? Je peux le créer pour vous!
