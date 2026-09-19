# 🎨 Guide d'Utilisation des Nouvelles Fonctionnalités Frontend

Date : 2026-01-01
Statut : ✅ **PRÊT À UTILISER**

---

## 🎉 Nouvelles Fonctionnalités Disponibles

Votre orchestrateur IA peut maintenant gérer **8 types de tâches différentes**, bien au-delà de la simple génération de code !

---

## 📋 Types de Tâches Disponibles

### 💻 Génération de Code (CODE_GENERATION)
**Usage** : Génération automatique de code par l'IA

**Comment créer** :
1. Aller dans "Nouvelle tâche"
2. Sélectionner le type : "💻 Génération de Code"
3. Remplir le prompt LLM avec ce que vous voulez générer
4. Exemple : *"Crée une fonction Python pour valider des emails avec regex"*

**Ce qui se passe** :
- Le scheduler traite la tâche toutes les 5 minutes
- L'IA génère le code selon votre prompt
- Le code apparaît dans la tâche pour validation

---

### 📄 Rédaction de Document (DOCUMENT_WRITING)
**Usage** : L'IA rédige des documents (dossiers de financement, rapports, budgets...)

**Comment créer** :
1. Type : "📄 Rédaction de Document"
2. Dans "Instructions pour l'IA", décrivez le document
3. Exemple : *"Rédige un budget prévisionnel sur 12 mois pour un projet artistique de 50 000€"*

**Ce qui se passe** :
- L'IA analyse les besoins du projet
- Génère un document structuré en Markdown
- Fournit un document prêt à être adapté

**Types de documents** :
- Dossiers de financement
- Rapports d'activité
- Budgets prévisionnels
- Lettres de motivation
- Fiches de présentation

---

### 💰 Recherche de Financements (FUNDING_SEARCH)
**Usage** : Trouver des opportunités de financement (subventions, appels à projets...)

**Comment créer** :
1. Type : "💰 Recherche de Financements"
2. Mots-clés : `subvention, culture, numérique, association`
3. L'IA cherche automatiquement sur data.gouv.fr et autres sources

**Ce qui se passe** :
- Recherche sur data.gouv.fr (données publiques françaises)
- Analyse de pertinence par l'IA (score 0-100)
- Extraction des informations clés :
  - Montant du financement
  - Date limite de candidature
  - Critères d'éligibilité
  - Lien vers le dossier

**Exemple de résultat** :
```
Titre : Subvention DRAC - Projets numériques culturels
Score de pertinence : 92/100
Montant : 10 000 - 50 000 €
Date limite : 15/03/2026
Critères : Associations culturelles, projets innovants numériques
Lien : https://...
```

---

### 🔍 Veille Technologique (VEILLE_TECH)
**Usage** : Surveiller les nouvelles technologies, outils, frameworks

**Comment créer** :
1. Type : "🔍 Veille Technologique"
2. Mots-clés : `FastAPI, Python, async, WebSockets`
3. L'IA cherche sur GitHub, Hacker News

**Ce qui se passe** :
- Recherche sur GitHub (repos les plus pertinents)
- Recherche sur Hacker News (discussions techniques)
- Analyse de pertinence
- Résumé des découvertes

**Sources utilisées** :
- GitHub API (repos, stars, dernières updates)
- Hacker News (articles, discussions)
- RSS feeds techniques (optionnel)

---

### 🎨 Veille Culturelle (VEILLE_CULTURAL)
**Usage** : Découvrir des artistes, œuvres, tendances artistiques

**Comment créer** :
1. Type : "🎨 Veille Culturelle"
2. Mots-clés : `art numérique, installation interactive, bio-art`
3. L'IA cherche sur diverses sources culturelles

**Ce qui se passe** :
- Recherche d'artistes et œuvres
- Analyse de tendances
- Identification d'opportunités de collaboration

**Résultats possibles** :
- Artistes émergents
- Œuvres récentes
- Tendances artistiques
- Résidences d'artistes

---

### 📅 Recherche d'Événements (VEILLE_EVENTS)
**Usage** : Trouver des festivals, expositions, conférences

**Comment créer** :
1. Type : "📅 Recherche d'Événements"
2. Mots-clés : `festival, exposition, art numérique, Paris`
3. L'IA cherche des événements pertinents

**Ce qui se passe** :
- Recherche d'événements à venir
- Extraction des dates et lieux
- Analyse de pertinence pour votre projet

**Informations extraites** :
- Nom de l'événement
- Date et lieu
- Description
- Lien d'inscription
- Date limite de soumission (si appel à participation)

---

### 📋 Tâche Administrative (ADMINISTRATIVE)
**Usage** : Tâches administratives génériques

**Comment créer** :
1. Type : "📋 Tâche Administrative"
2. Description claire de la tâche
3. L'IA peut vous assister selon le besoin

---

### 🔬 Recherche (RESEARCH)
**Usage** : Recherche générique d'informations

**Comment créer** :
1. Type : "🔬 Recherche"
2. Mots-clés ou description de la recherche
3. L'IA cherche et synthétise les informations

---

## 🎯 Comment Utiliser

### Étape 1 : Créer une Nouvelle Tâche

1. **Aller dans "Tâches"** → Cliquer sur "Nouvelle tâche"
2. **Remplir les informations** :
   - **Projet** : Sélectionnez le projet concerné
   - **Titre** : Titre clair de la tâche
   - **Description** : Description détaillée
   - **Type de tâche** : ⚠️ **NOUVEAU** Choisissez parmi les 8 types
   - **Priorité** : P1 (urgent), P2 (important), P3 (normal)

3. **Remplir les champs spécifiques** selon le type :

**Pour Génération de Code ou Rédaction** :
- Section "Instructions pour l'IA" apparaît
- Décrivez ce que vous voulez

**Pour Veille ou Recherche de Financements** :
- Section "Paramètres de recherche" apparaît
- Entrez les mots-clés séparés par des virgules

4. **Cliquer sur "Créer la tâche"**

---

### Étape 2 : Le Scheduler Traite la Tâche

- **Automatique** : Le scheduler tourne toutes les 5 minutes
- **Statut** : La tâche passe en `GENERATING`
- **Traitement** : L'IA travaille selon le type de tâche
- **Fin** : La tâche passe en `MANUAL_REVIEW`

---

### Étape 3 : Consulter les Résultats

1. **Ouvrir la tâche** en cliquant dessus
2. **Voir les résultats** :
   - Code généré (pour CODE_GENERATION)
   - Document rédigé (pour DOCUMENT_WRITING)
   - Opportunités trouvées (pour FUNDING_SEARCH)
   - Résultats de veille (pour VEILLE_*)

3. **Valider ou ajuster** selon vos besoins

---

## 🎨 Interface Visuelle

### Badges de Type de Tâche

Chaque type a maintenant un badge coloré dans les listes :

- 💻 **Code** : Bleu
- 📄 **Document** : Violet
- 💰 **Financement** : Vert
- 🔍 **Veille Tech** : Indigo
- 🎨 **Veille Culture** : Rose
- 📅 **Événements** : Orange
- 📋 **Admin** : Gris
- 🔬 **Recherche** : Turquoise

### Formulaire Adaptatif

Le formulaire change selon le type de tâche sélectionné :
- **Code/Document** : Affiche un champ "Prompt LLM"
- **Veille/Financement** : Affiche un champ "Mots-clés"
- **Autres** : Formulaire de base

---

## 📊 Exemples Concrets

### Exemple 1 : Recherche de Financements pour une Asso

```
Type : 💰 Recherche de Financements
Titre : Trouver des subventions pour notre projet
Mots-clés : subvention, association, culture, numérique, île-de-france
Priorité : P1

→ Résultats attendus :
- Liste de 5-10 opportunités de financement
- Scores de pertinence
- Dates limites
- Montants disponibles
```

---

### Exemple 2 : Veille Technologique sur FastAPI

```
Type : 🔍 Veille Technologique
Titre : Suivre l'évolution de FastAPI
Mots-clés : FastAPI, Python, async, performance
Priorité : P2

→ Résultats attendus :
- Nouvelles versions de FastAPI
- Repos GitHub intéressants
- Articles techniques récents
- Discussions Hacker News
```

---

### Exemple 3 : Trouver des Festivals d'Art Numérique

```
Type : 📅 Recherche d'Événements
Titre : Festivals art numérique 2026
Mots-clés : festival, art numérique, installation, France
Priorité : P2

→ Résultats attendus :
- Liste de festivals à venir
- Dates et lieux
- Dates limites de soumission
- Liens de contact
```

---

### Exemple 4 : Rédiger un Dossier de Financement

```
Type : 📄 Rédaction de Document
Titre : Dossier DRAC pour projet XYZ
Instructions : Rédige un dossier de demande de subvention DRAC pour un projet d'installation interactive mêlant art et technologie. Budget : 30 000€, durée : 6 mois.
Priorité : P1

→ Résultat attendu :
- Document structuré avec :
  - Présentation du projet
  - Objectifs et enjeux
  - Budget détaillé
  - Plan de réalisation
  - Impact attendu
```

---

## ⚙️ Configuration Technique

### Backend
✅ **Tous les modules sont opérationnels** :
- WebResearchModule (GitHub, HN, data.gouv.fr, RSS)
- AnalyzerModule (scoring IA)
- PromptGeneratorModule
- DocumentGeneratorModule
- UnifiedOrchestrator (dispatching)

### Frontend
✅ **Interface mise à jour** :
- Sélecteur de type de tâche
- Champs conditionnels
- Badges visuels
- Types TypeScript

### Scheduler
✅ **Traitement automatique** :
- Toutes les 5 minutes
- Dispatching selon task_type
- Gestion des erreurs

---

## 🚀 Prochaines Améliorations Possibles

### 1. Page de Résultats de Veille
Créer une page dédiée pour consulter tous les résultats de veille :
- `/veille/results`
- Filtres par type, score, date
- Actions : sauvegarder, créer tâche, rejeter

### 2. Configuration des Topics de Veille
Interface pour gérer les topics de veille automatique :
- `/veille/topics`
- Créer des veilles récurrentes
- Fréquence : quotidienne, hebdomadaire, mensuelle

### 3. Intégration Notifications
Notifier quand :
- Une opportunité de financement pertinente est trouvée
- Un événement avec date limite approche
- Une tâche de veille a trouvé des résultats

### 4. Export des Résultats
Exporter les résultats :
- PDF pour les documents générés
- CSV pour les opportunités de financement
- Markdown pour les rapports de veille

### 5. Dashboard Analytics
Vue d'ensemble :
- Nombre d'opportunités trouvées par mois
- Score moyen de pertinence
- Types de tâches les plus utilisés
- Taux de validation des résultats

---

## 🐛 Dépannage

### Le formulaire ne s'affiche pas correctement
→ Rafraîchir la page (Ctrl+Shift+R ou Cmd+Shift+R)
→ Vider le cache du navigateur

### Les champs conditionnels ne changent pas
→ Vérifier que vous avez bien sélectionné un type de tâche
→ Recharger la page

### La tâche reste en statut READY
→ Attendre 5 minutes (durée du scheduler)
→ Vérifier les logs backend : `docker-compose logs backend --tail=50`

### Erreur lors de la création de tâche
→ Vérifier que tous les champs obligatoires sont remplis
→ Vérifier que le backend est démarré : `curl http://localhost:8000/health`

---

## 📚 Documentation Technique

Pour plus de détails techniques, consultez :
- `ARCHITECTURE_MODULAIRE.md` - Architecture des modules backend
- `EXEMPLES_MODULES.md` - 6 exemples d'utilisation détaillés
- `INTEGRATION_COMPLETE.md` - Guide d'intégration complète
- `CORRECTIFS_SCHEMAS.md` - Correctifs appliqués aux schemas

---

## ✅ Checklist de Vérification

Avant d'utiliser les nouvelles fonctionnalités :

- [ ] Backend démarré : `docker-compose ps backend` → "Up"
- [ ] Frontend démarré : `http://localhost:5173` accessible
- [ ] Connecté avec un compte utilisateur
- [ ] Au moins un projet créé
- [ ] Page formulaire affiche le sélecteur de type

---

## 🎊 Conclusion

Votre orchestrateur IA est maintenant un **véritable assistant multi-domaines** qui peut :
- ✅ Générer du code
- ✅ Rédiger des documents
- ✅ Trouver des financements
- ✅ Faire de la veille technologique
- ✅ Découvrir des événements culturels
- ✅ Et bien plus !

**Testez dès maintenant** en créant votre première tâche d'un nouveau type ! 🚀
