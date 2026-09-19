# Architecture technique — Orchestrateur IA

Mise à jour : 19 septembre 2026.

## 📁 Racine

```
orchestrateur-ia/
├── .env.example            # Variables d'environnement (copier en .env)
├── docker-compose.yml      # postgres, backend, frontend, open-webui, db-backup
├── launch.md               # Lancement pas à pas
├── PROJECT_STATE.md        # État fonctionnel, sécurité, roadmap
├── PROJECT_STRUCTURE.md    # Ce fichier
├── README.md               # Présentation, installation, commandes
├── run_tests.sh            # Tests backend dans le conteneur
├── setup-ollama.sh / start.sh
├── backups/                # Sauvegardes Postgres quotidiennes (ignoré par git)
├── archive/                # Anciens documents et tests
├── backend/
└── frontend/
```

## 🏗 Backend (FastAPI)

```
backend/
├── Dockerfile                 # stages development (avec outils de test) / production
├── requirements.txt           # dépendances runtime
├── requirements-dev.txt       # + pytest, pytest-asyncio, httpx, pytest-cov
├── pytest.ini                 # asyncio_mode=auto
├── alembic/versions/          # 14 migrations (dernière : add_veille_advanced_fields)
├── app/
│   ├── main.py                # FastAPI, CORS (settings), handlers d'erreurs, scheduler
│   ├── core/
│   │   ├── config.py          # Settings pydantic (DATABASE_URL, OLLAMA_*, CORS, clés API)
│   │   ├── database.py        # moteur async + sessions
│   │   ├── security.py        # bcrypt, JWT
│   │   ├── exceptions.py / logging.py
│   ├── api/v1/
│   │   ├── auth.py            # register, login (anti-brute-force), me
│   │   ├── projects.py        # CRUD, analyse IA, create-suggested-tasks, critical-path,
│   │   │                      # maturity-analysis, visual-references, idéation unifiée
│   │   ├── tasks.py           # CRUD, validate/reject/generate/complete/retry/stop, logs,
│   │   │                      # veille-results (+ update), veille-refine, veille-rescan,
│   │   │                      # veille-deadlines
│   │   ├── ideation.py        # dialogue socratique (SSE)
│   │   ├── orchestrator.py    # status, queue, stats, force generate
│   │   ├── reports.py         # briefings quotidiens
│   │   ├── settings.py        # préférences de modèles, liste des modèles Ollama
│   │   └── time.py            # chrono / entrées de temps
│   ├── models/                # User, UserSettings, Project, Task (+task_dependencies),
│   │                          # TaskLog, TimeEntry, DailyReport, IdeationMessage,
│   │                          # VeilleTopic, VeilleResult
│   ├── schemas/               # Pydantic (dont project_analysis, veille_result)
│   ├── prompts/ideation_prompts.py
│   └── services/
│       ├── model_registry.py        # resolve_model() + think_kwargs() — TOUT appel LLM passe par là
│       ├── llm_client.py            # génération code/texte (streaming, double passe thinking)
│       ├── unified_orchestrator.py  # dispatch par type de tâche, veille, financements,
│       │                            # veille visuelle, retry
│       ├── scheduler.py             # jobs APScheduler
│       ├── project_analyzer.py      # analyse IA → tâches, veilles, blocages
│       ├── daily_review_service.py  # briefing du matin, stagnation, deadlines
│       ├── critical_path.py         # CPM + dates projetées
│       ├── maturity.py              # score de maturité
│       ├── ideation_service.py / ollama_service.py
│       ├── web_search_service.py    # DuckDuckGo (ou Brave si clé)
│       └── modules/
│           ├── analyzer.py          # scoring de pertinence, résumés, extraction
│           ├── web_research.py      # fetch (anti-SSRF), RSS, Aides-Territoires,
│           │                        # Openverse / AIC / Met
│           ├── document_generator.py
│           └── prompt_generator.py
├── scripts/seed_demo_data.py
└── tests/                     # 39 tests : auth, projets, tâches, erreurs
    ├── conftest.py            # base orchestrator_test créée automatiquement
    └── test_*.py
```

### Flux d'une tâche
```
Frontend → POST /tasks (READY) → scheduler (2 min) ou « Générer maintenant »
        → UnifiedOrchestrator.handle_task → handler par type
        → résultat (generated_code / radar_report / VeilleResult)
        → MANUAL_REVIEW (code) ou COMPLETED → validation utilisateur
```

### Résolution des modèles
`model_registry.resolve_model(préféré)` : modèle préféré s'il est installé, sinon `OLLAMA_MODEL_CODE`, sinon premier modèle local (hors embeddings/cloud), avec avertissement. `think_kwargs(model)` ajoute `think=False` uniquement si le modèle expose la capacité « thinking » (API `/show`).

## 🖥 Frontend (React + Vite)

```
frontend/
├── index.html                 # manifeste PWA, theme-color, métas iOS
├── public/                    # manifest.webmanifest, icon.svg, icon-maskable.svg
├── tailwind.config.js         # tokens paper / ink / accent / highlight, fontes
└── src/
    ├── App.tsx                # routes (react-router 7)
    ├── index.css              # fontes Fontsource, .kicker, .standfirst, .rule, .figures
    ├── components/
    │   ├── ui/                # Button, Card, Input, Select, ConfirmDialog, FieldError, Loader
    │   ├── Layout/            # Navbar (chrono), Sidebar (sommaire)
    │   ├── tasks/             # TaskHeader, TaskStatusPanel, TaskReviewActions,
    │   │                      # TaskResultPanel, taskTypeUtils, StatusBadge, PriorityBadge,
    │   │                      # TaskTypeBadge, CodeViewer, RadarViewer, VeilleResultsViewer,
    │   │                      # ValidationModal, TaskCard
    │   ├── projects/          # ProjectHeader, ProjectInfoPanels, ProjectHealthDashboard,
    │   │                      # ProjectTasksBoard, GanttChart, MaturityScore,
    │   │                      # MaturityIndicators, AIAnalysisButton
    │   ├── IdeationChat.tsx / UnifiedProjectChat.tsx / FinalizationValidationModal.tsx
    │   ├── DailyReportCard.tsx, ProjectCard.tsx, ServiceStatus.tsx, TimerWidget.tsx,
    │   │   Badge.tsx, EmptyState.tsx, ProgressBar.tsx, StatsCard.tsx
    │   └── auth/ProtectedRoute.tsx
    ├── pages/
    │   ├── Dashboard.tsx      # « une de journal » : briefing, actions évidentes, échéances
    │   ├── Login.tsx / Register.tsx / Settings.tsx
    │   ├── Projects/          # ProjectsList, ProjectDetail, ProjectForm, ProjectAnalysis,
    │   │                      # ProjectMoodboard
    │   └── Tasks/             # TasksList, TaskDetail, TaskForm
    ├── hooks/usePolling.ts    # polling avec pause onglet caché
    ├── services/              # api.ts (axios + intercepteur d'erreurs, silentError),
    │                          # projects, tasks, ideation, timer, settingsApi, unifiedProject
    ├── stores/                # Zustand : auth, projects, tasks, timer
    ├── types/
    └── utils/                 # constants, celebrate
```

### Conventions frontend
- Aucune couleur Tailwind brute : uniquement les tokens (`bg-paper`, `text-ink`, `bg-accent`, `bg-success/10`…).
- Les pages gardent l'état et les appels API ; les composants sont visuels.
- Erreurs API toastées par l'intercepteur ; `{ silentError: true }` pour le polling et les 404 attendus.
- Pas de `window.confirm` : `ConfirmDialog`.

## 📦 Dépendances principales

| Backend | Version | | Frontend | Version |
|---|---|---|---|---|
| FastAPI | 0.141 | | React | 18 |
| Starlette | 1.6 | | TypeScript | 5 |
| SQLAlchemy | 2.0 (async) | | Vite | 5 |
| Pydantic | 2.13 | | react-router-dom | 7 |
| Alembic | 1.12 | | Zustand | 4 |
| APScheduler | 3.10 | | TailwindCSS | 3 |
| ollama (client) | 0.6 | | react-hook-form + zod | 7 / 3 |
| aiohttp / bs4 / feedparser | 3.9 / 4.15 / 6.0 | | react-markdown | 10 |
| passlib / python-jose | bcrypt / HS256 | | lucide-react | 0.29x |

## ⚙️ Environnement

Voir `.env.example`. Les modèles par usage (code, idéation, analyse, génération de tâches) sont stockés par utilisateur dans `user_settings` et choisis dans Paramètres.

## 📊 Données

```
User 1—N Project 1—N Task N—N Task (task_dependencies)
                  │        └— TaskLog, TimeEntry
                  └— VeilleTopic 1—N VeilleResult (deadline, image_url…)
User 1—1 UserSettings ; User 1—N DailyReport ; Project 1—N IdeationMessage
```

## 🔒 Sécurité (réel, pas théorique)
- JWT HS256, 7 jours, stocké en `localStorage` côté client (pas de cookie httpOnly).
- Isolation par `user_id` sur tous les endpoints ; 401 sans jeton.
- CORS depuis `settings.BACKEND_CORS_ORIGINS` ; Postgres/Open WebUI sur `127.0.0.1`.
- Anti-brute-force login en mémoire ; anti-SSRF dans `web_research.fetch_url`.
- Pas de protection CSRF (API Bearer, pas de cookies).
