# Améliorations Apportées - 31 Décembre 2025

## ✅ Corrections Appliquées

### 1. Affichage du nom du projet sur les tâches

**Problème** : Les tâches n'affichaient pas à quel projet elles appartenaient.

**Solution** :
- ✅ Backend modifié (`/backend/app/api/v1/tasks.py`) :
  - Liste des tâches inclut maintenant `project_name`
  - Endpoint GET tâche individuelle inclut `project_name`
  - Endpoint POST création tâche retourne `project_name`

- ✅ Frontend modifié :
  - Type `Task` mis à jour (`/frontend/src/types/task.types.ts`)
  - `TaskCard` affiche maintenant le nom du projet avec icône dossier

**Résultat** : Chaque carte de tâche affiche maintenant "📁 Nom du Projet" sous le titre.

---

### 2. Nettoyage des fichiers obsolètes

**Action** :
- ✅ Supprimé `/files/` contenant anciennes conversations (CONV4, etc.)
- ✅ Conservé uniquement les fichiers actuels et pertinents

---

## 🎯 Système de Veille Généralisé

### Architecture Actuelle

Le système utilise déjà un champ JSON flexible dans le modèle `Project` :

```python
features = {
  "code_gen": bool,      # Génération de code activée
  "veille": bool,        # Veille activée
  "git_auto": bool       # Git automatique activé
}
```

### Nouvelle Structure Proposée

Pour personnaliser la veille selon vos besoins (tech, subventions, appels d'offre), vous pouvez utiliser:

```python
features = {
  "code_gen": True,
  "veille": True,
  "veille_config": {
    "types": ["technology", "grants", "tenders", "general"],
    "keywords": [
      "React",
      "subventions culture",
      "appels d'offre graphisme",
      "intelligence artificielle"
    ],
    "sources": [
      "https://www.culture.gouv.fr/Aides-demarches",  # Subventions culture
      "https://www.boamp.fr",                         # Appels d'offre publics
      "https://dev.to",                               # Tech
      "RSS feeds..."
    ],
    "frequency": "weekly",
    "notify_email": True
  }
}
```

### Types de Veille Supportés

| Type | Description | Usage |
|------|-------------|-------|
| `technology` | Veille technologique (frameworks, outils, langages) | Projets de dev |
| `grants` | Subventions et aides (culture, innovation, recherche) | Projets artistiques, research |
| `tenders` | Appels d'offres (publics, privés) | Travail de graphiste freelance |
| `general` | Veille générique (actualité domaine spécifique) | Tous projets |

### Exemples Concrets

#### 1. Projet Artistique avec veille subventions

```json
{
  "name": "Installation Interactive",
  "type": "personal",
  "features": {
    "code_gen": false,
    "veille": true,
    "veille_config": {
      "types": ["grants"],
      "keywords": [
        "subventions art numérique",
        "résidence artistique",
        "aide création contemporaine",
        "DRAC Île-de-France"
      ],
      "sources": [
        "https://www.culture.gouv.fr/Aides-demarches",
        "https://www.afdas.com",
        "https://www.cnap.fr"
      ],
      "frequency": "weekly"
    }
  }
}
```

#### 2. Projet Graphiste avec appels d'offre

```json
{
  "name": "Activité Freelance Graphisme",
  "type": "professional",
  "features": {
    "code_gen": false,
    "veille": true,
    "veille_config": {
      "types": ["tenders"],
      "keywords": [
        "graphisme",
        "identité visuelle",
        "charte graphique",
        "design UX/UI"
      ],
      "sources": [
        "https://www.boamp.fr",
        "https://www.marches-publics.gouv.fr",
        "https://ted.europa.eu/fr/"
      ],
      "frequency": "daily"
    }
  }
}
```

#### 3. Projet Tech avec veille technologique

```json
{
  "name": "App React Native",
  "type": "personal",
  "features": {
    "code_gen": true,
    "veille": true,
    "veille_config": {
      "types": ["technology"],
      "keywords": [
        "React Native",
        "Expo",
        "TypeScript",
        "mobile development"
      ],
      "sources": [
        "https://dev.to",
        "https://news.ycombinator.com",
        "https://www.reddit.com/r/reactnative/"
      ],
      "frequency": "weekly"
    }
  }
}
```

---

## 🔮 Implémentation Future

### Phase 1 : Backend (Optionnel - déjà flexible)

Le champ `features` est déjà en JSON, donc **aucune migration nécessaire**.

Vous pouvez dès maintenant créer un projet avec une config personnalisée via l'API :

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Projet Artistique",
    "type": "personal",
    "features": {
      "code_gen": false,
      "veille": true,
      "veille_config": {
        "types": ["grants"],
        "keywords": ["subventions art", "résidence artistique"]
      }
    }
  }'
```

### Phase 2 : Interface Frontend (À développer)

Créer un composant `VeilleConfig` dans le formulaire de projet :

```tsx
<div className="space-y-4">
  <h3>Configuration de la Veille</h3>

  {/* Types de veille */}
  <div>
    <label>Types de veille</label>
    <div className="space-y-2">
      <Checkbox label="Veille technologique" value="technology" />
      <Checkbox label="Subventions & Aides" value="grants" />
      <Checkbox label="Appels d'offres" value="tenders" />
      <Checkbox label="Veille générale" value="general" />
    </div>
  </div>

  {/* Mots-clés */}
  <div>
    <label>Mots-clés</label>
    <TagInput
      placeholder="React, subventions culture, appels d'offre..."
      tags={keywords}
      onChange={setKeywords}
    />
  </div>

  {/* Sources */}
  <div>
    <label>Sources (optionnel)</label>
    <textarea
      placeholder="URLs de sites web, flux RSS..."
      value={sources}
      onChange={e => setSources(e.target.value)}
    />
  </div>

  {/* Fréquence */}
  <div>
    <label>Fréquence</label>
    <select value={frequency} onChange={e => setFrequency(e.target.value)}>
      <option value="daily">Quotidienne</option>
      <option value="weekly">Hebdomadaire</option>
      <option value="monthly">Mensuelle</option>
    </select>
  </div>
</div>
```

### Phase 3 : Service de Veille (À développer)

Créer un service `veille_service.py` qui :

1. **Analyse la config de chaque projet**
2. **Scrape les sources** selon le type de veille
3. **Filtre par mots-clés**
4. **Notifie l'utilisateur** (email, tâche créée automatiquement, etc.)

```python
# backend/app/services/veille_service.py

class VeilleService:
    async def process_project_veille(self, project: Project):
        config = project.features.get("veille_config", {})
        types = config.get("types", [])
        keywords = config.get("keywords", [])

        results = []

        for veille_type in types:
            if veille_type == "grants":
                results += await self.scrape_grants(keywords)
            elif veille_type == "tenders":
                results += await self.scrape_tenders(keywords)
            elif veille_type == "technology":
                results += await self.scrape_tech(keywords)
            elif veille_type == "general":
                results += await self.scrape_general(keywords, config.get("sources"))

        return results

    async def scrape_grants(self, keywords):
        # Scraper subventions (culture.gouv.fr, etc.)
        pass

    async def scrape_tenders(self, keywords):
        # Scraper appels d'offre (BOAMP, etc.)
        pass
```

---

## 📊 État Actuel du Projet

### ✅ Fonctionnalités Opérationnelles

- Backend FastAPI complet
- Frontend React avec gestion projets/tâches
- Orchestrateur IA avec Ollama
- Génération de code automatique
- Validation de code (split view)
- Time tracking (projets PRO)
- Tests d'intégration
- Données de démo
- **NOUVEAU** : Affichage nom projet sur tâches

### 🎯 Prochaines Étapes Suggérées

1. **Interface de configuration veille** (frontend)
   - Formulaire dans création/édition projet
   - Choix types de veille
   - Gestion mots-clés

2. **Service de veille backend**
   - Scraping sources configurées
   - Filtrage par keywords
   - Création automatique de tâches ou notifications

3. **Scheduler veille**
   - Exécution périodique selon fréquence
   - Intégration dans l'orchestrateur existant

---

## 🚀 Comment Utiliser Maintenant

### Afficher les tâches avec leur projet

1. Accédez à http://localhost:5173
2. Login avec `demo@example.com` / `demo123`
3. Allez dans **Tâches**
4. **Chaque tâche affiche maintenant son projet** avec une icône 📁

### Configurer la veille (via API pour le moment)

```bash
# Créer un projet avec veille personnalisée
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mon Projet Artistique",
    "type": "personal",
    "features": {
      "veille": true,
      "veille_config": {
        "types": ["grants"],
        "keywords": ["subventions art contemporain", "résidence artistique"]
      }
    }
  }'
```

---

**Dernière mise à jour** : 31 Décembre 2025
**Version** : Post-Conv9 + Améliorations
