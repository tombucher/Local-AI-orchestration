🚀 PROJET : ORCHESTRATEUR IA (v2)
📝 Descriptif du Projet
L'Orchestrateur IA est un outil de gestion de projet intelligent qui ne se contente pas de stocker des données, mais les analyse et les structure de manière autonome. Il utilise des modèles de langage (LLM via Ollama) pour décomposer des objectifs complexes en tâches logiques, identifie leurs dépendances, calcule le chemin critique (CPM) et évalue la viabilité du projet via un score de maturité.

🏗 État Technique Actuel (Janvier 2026)
Backend (FastAPI + SQLAlchemy 2.0)

Système de Dépendances : Table de liaison récursive (task_dependencies) permettant de lier les tâches entre elles.

Service CPM (CriticalPathService) : Implémentation de l'algorithme de calcul des dates au plus tôt/tard et détection des tâches critiques.

Service Maturité (MaturityService) : Algorithme de scoring (0-100) basé sur 4 piliers (Dépendances, Descriptions, Délais, Chemin Critique).

Intelligence Artificielle : Prompt Engineering optimisé pour l'extraction de dépendances en format JSON via Ollama.

Stabilité : Utilisation de lazy="selectin" pour les relations et .unique() pour la déduplication des résultats SQL.

Frontend (React + Vite + Tailwind)

Dashboard de base fonctionnel (CRUD Projets & Tâches).

Note : Le front doit maintenant intégrer les nouvelles données analytiques du backend.

🐛 État des Bugs (Janvier 2026)

### Bugs Résolus ✅
- ✅ Dashboard : Problème de calcul des tâches totales (affichait 28 au lieu de 5)
- ✅ Dashboard : Erreur 500 sur le chemin critique
- ✅ Génération de code : Erreur 500 (NameError: name 'row' is not defined)
- ✅ Édition des tâches : Perte du type de tâche lors de la sauvegarde
- ✅ Disparition des tâches : Filtrage incorrect des tâches CANCELLED

### Bugs Restants ⚠️
- ⚠️ Dashboard : Compteur de projets incorrect (remonte trop de projets)
- ⚠️ Dashboard : Redondance d'information entre DailyReportCard et la section projets/tâches
- ⚠️ Création de projet : Chat ne fonctionne pas dans l'idéation
- ⚠️ Page projet : Erreurs 500 au chargement (maturity-analysis, critical-path)
- ⚠️ Analyse de projet : Page blanche avec erreurs 404
- ⚠️ Édition de projet : Sauvegarde ne fonctionne pas
- ⚠️ Dashboard santé : Score de maturité à 0, erreurs sur les conseils
- ⚠️ Chemin critique : Erreur de chargement et documentation manquante
- ⚠️ Tâches : Filtres visuels peu intuitifs
- ⚠️ Génération de code : Ne fonctionne pas pour certains types de tâches
- ⚠️ Sélection du type de tâche : UI peu user-friendly
- ⚠️ Types de tâches spécifiques : Veille, génération de documents, recherche de financement/évènements non fonctionnels
- ⚠️ Paramètres : Sélection des modèles par type de tâche non implémentée

🗺 Roadmap de Développement
Étape 1 : Fondations et Intelligence Logique (TERMINÉ ✅)

✅ 1.1 Structure de données pour les dépendances.

✅ 1.2 Algorithme de calcul du chemin critique (CPM).

✅ 1.3 IA : Génération de tâches avec liens logiques automatiques.

✅ 1.4 Système de score de maturité du projet.

Étape 2 : Visualisation et Pilotage (EN COURS 🔄)

✅ 2.1 Dashboard de Santé : Visualisation du score de maturité (jauge) et des alertes de planification.

2.2 Vue Flux / Gantt : Affichage visuel des dépendances et mise en évidence du chemin critique (tâches en rouge/feu).

2.3 Interactivité : Modification drag-and-drop des dépendances sur le front.

Étape 3 : Collaboration et IA Avancée (À VENIR 📅)

3.1 Agent de Remédiation : L'IA propose des solutions quand le score de maturité baisse ou qu'une tâche critique est en retard.

3.2 Gestion des Ressources : Analyse de la charge de travail par utilisateur.

3.3 Export et Rapports : Génération de synthèses de projet pour les décideurs.

💡 Instructions pour le "Reset" de Conversation
Lors de l'ouverture d'une nouvelle session, toujours donner l'état technique actuel et la prochaine sous-étape de l'étape 2.
