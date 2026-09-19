# 🚀 Orchestrateur IA — état du projet

**Dernière mise à jour : 19 septembre 2026**

## 📝 Ce que fait l'outil

Journal d'atelier assisté par IA locale (Ollama) pour un créateur art numérique + tech. Il **pilote** les projets (décomposition en tâches, dépendances, chemin critique, score de maturité), **passe à l'action** (génération de code et de documents, veille textuelle, visuelle et appels à projets) et **donne envie de faire** (briefing du matin, prochaine action évidente, relance des projets qui dorment, célébrations).

Tout tourne en local : FastAPI + PostgreSQL dans Docker, React/Vite, Ollama natif sur macOS.

## ✅ Ce qui fonctionne (vérifié de bout en bout)

### Pilotage
- Création de projet par **dialogue d'idéation** (streaming SSE) puis finalisation.
- **Analyse IA** : décomposition en 10-15 tâches avec sous-tâches, priorités, dépendances et veilles suggérées ; création en un clic.
- **Chemin critique** (CPM) avec dates projetées et **frise Gantt SVG interactive** (étirer une estimation, créer une dépendance en glissant) ; score de maturité et conseils.
- Chrono par tâche (widget dans la barre), séries de jours productifs.

### Action
- **Génération de code** (revue manuelle, édition inline, regénération avec instructions) et **de documents**.
- **Veille** par scope (actualités, tech, culturelle, financements, académique, **visuelle**) — récurrente (quotidienne/hebdo/mensuelle) ou **one-shot** ; rapport radar avec pépites, affinage par mots-clés qui apprend des résultats écartés, relance immédiate.
- **Appels à projets** : requêtes dédiées, extraction LLM des deadlines depuis les pages, tuile « Échéances à venir », Aides-Territoires en option (clé gratuite).
- **Moodboard** : images libres (Openverse, Art Institute of Chicago, Met Museum, Wikimedia Commons, flux RSS design) épinglables par projet.

### Proactivité
- **Briefing du matin** (8h) en français, ton d'atelier : top 3 du jour, **prochaine action évidente** par projet, échéances de financement intégrées.
- **Détection de stagnation** (7 jours sans activité) → suggestions de relance créables en un clic.

### Socle
- Scheduler (queue toutes les 2 min, veilles toutes les 15 min, watchdog 5 min, rapports 8h), retry avec backoff.
- **Registre de modèles** : si un modèle Ollama configuré n'existe plus, repli automatique sur un modèle installé ; thinking désactivé par détection de capacités.
- Design system « journal d'atelier » (papier/encre/vermillon, Fraunces + Archivo), PWA installable.
- **39 tests** backend (`./run_tests.sh`), sauvegardes Postgres quotidiennes (`./backups/`), rotation des logs.

## 🔒 Sécurité (audit du 19/09/2026)
- Isolation par utilisateur sur tous les endpoints ; 401 sans jeton, 404 sur les données d'autrui.
- Postgres et Open WebUI liés à `127.0.0.1` ; anti-brute-force sur le login (10 échecs / 15 min) ; garde-fou SSRF sur les récupérations de pages.
- Dépendances à jour (fastapi 0.141 / starlette 1.6, react-router 7, 0 vulnérabilité npm).
- À faire par toi : renforcer `POSTGRES_PASSWORD` ; ajouter une clé Brave Search pour fiabiliser la recherche web.

## 🤖 Modèles Ollama
| Usage | Modèle | Réglage |
|---|---|---|
| Code, documents, analyse, idéation | `qwen3.8:27b-mlx` | Paramètres (par utilisateur) |
| Requêtes de veille, scoring, briefing | `gemma4:12b-mlx` | `OLLAMA_MODEL_PROMPT` dans `.env` |

Les modèles changent souvent : ne jamais coder un nom en dur, passer par `backend/app/services/model_registry.py`. Préférer les variantes `-mlx` (Apple Silicon).

## 🐛 Bugs notables corrigés en 2026
- Génération LLM qui coupait au premier token (stop token vide) ; boucles de thinking sur qwen3.6+ (`think=False` natif).
- Analyse de projet vide (accolades doublées dans un prompt non-f-string ; appel Ollama synchrone qui gelait l'API ; modèle supprimé → 404 silencieux).
- Création des tâches suggérées qui relançait toute l'analyse ; veilles suggérées jamais planifiées ; veilles récurrentes dupliquées toutes les 15 min.
- Recherche de financements qui renvoyait des datasets data.gouv au lieu d'appels à projets.
- `GET /tasks/{id}/logs` en 500 ; CORS hardcodé ; ~30 erreurs TypeScript qui cassaient `npm run build`.

Rapport de validation historique (janvier 2026) : `archive/VALIDATION_QA.md`.

## 🗺 Pistes suivantes

Côté code, tout est en place (19/09/2026) :
- **Recherche web** : Brave utilisé automatiquement dès que `BRAVE_SEARCH_API_KEY` est renseignée.
- **Accès distant** : API en chemin relatif + proxy Vite (`allowedHosts`), prêt pour Tailscale (voir README, « Depuis le téléphone »).
- **Gantt interactif** : poignée pour étirer l'estimation, glisser une barre sur une autre pour créer une dépendance.
- **Notifications** : briefing de 8h envoyé via ntfy si `NTFY_TOPIC` est configuré (`POST /reports/daily/generate?notify=true` pour tester).
- **Veille visuelle** : Wikimedia Commons et flux RSS design (Colossal, designboom, CreativeApplications, ou `topic.sources`) en plus d'Openverse / AIC / Met.

Ce qui dépend de toi : créer la clé Brave, installer Tailscale (+ `tailscale serve`), installer l'app ntfy et choisir un topic. Idées ensuite : Web Push natif (une fois en HTTPS), Gantt avec déplacement des échéances, export PDF du briefing.

## 💡 Reprise de session
Lire ce fichier, puis `PROJECT_STRUCTURE.md` pour l'architecture. Lancer : `docker compose up -d`, vérifier `curl localhost:8000/health`, tests : `./run_tests.sh`.
