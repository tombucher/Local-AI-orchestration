# 🚀 Orchestrateur IA — état du projet

**Dernière mise à jour : 21 septembre 2026**

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
- **Génération de code** (revue manuelle, édition inline, regénération avec instructions) et **de documents**. Les tâches de code d'un même projet partagent un **plan de fichiers** (une tâche = un fichier) et voient le code déjà produit : le HTML référence le bon `styles.css`, le CSS réutilise les vraies classes.
- **Veille** par scope (actualités, tech, culturelle, financements, académique, **visuelle**), alimentée par **SearXNG auto-hébergé** (métamoteur local : Google + Brave + DuckDuckGo agrégés, sans clé ni quota) **et par tes propres flux RSS** (Paramètres → « Mes flux de veille ») : chaque flux ajouté est vérifié et ses thèmes déduits de son contenu, pour que la veille choisisse les sources adaptées au *sujet* (typographie → tes flux design ; climat → tes flux écologie). Un petit catalogue intégré complète quand la bibliothèque est vide. Anti-doublon persistant par sujet — chaque scan ne ramène que du neuf. Si le filtre lexical est trop étroit, la récolte est complétée par les dernières entrées et c'est l'analyse LLM qui tranche — récurrente (quotidienne/hebdo/mensuelle) ou **one-shot** ; rapport radar avec pépites, affinage par mots-clés qui apprend des résultats écartés, relance immédiate.
- **Appels à projets** : requêtes dédiées, extraction LLM des deadlines depuis les pages, tuile « Échéances à venir », Aides-Territoires en option (clé gratuite).
- **Moodboard** : Openverse, Wikimedia Commons, Art Institute of Chicago, Met Museum, flux RSS design et **Are.na** (collections curatées, `ARENA_ACCESS_TOKEN`) **Internet Archive** (sans clé ; meilleur rendement mesuré : 62 % d'images pertinentes, médiane 90) et, si la clé gratuite est renseignée, **Pexels** — seule source dont les images sont réutilisables sans vérifier les droits au cas par cas — épinglables par projet. **Chaque vignette est regardée par un modèle vision** (gemma4, ~0,7 s) qui la note et la décrit : indispensable, puisque les sources nomment leurs images `IMG_8531.JPG` et qu'une image titrée « Brutalist Design » était un tracteur. La description remplace les titres illisibles. Une image que le modèle n'a pas pu regarder est **rétrogradée** sous le seuil : son score lexical atteint 95 dès qu'un mot de la requête traîne dans son titre, et une vignette injoignable se retrouvait en tête. Filtrées par pertinence : un moodboard vide plutôt qu'au hasard.
  ⚠️ Les images Are.na sont des **références** rassemblées par des utilisateurs, pas des visuels libres de droits.

### Proactivité
- **Briefing du matin** (8h) en français, ton d'atelier : top 3 du jour, **prochaine action évidente** par projet, échéances de financement intégrées.
- **Détection de stagnation** (7 jours sans activité) → suggestions de relance créables en un clic.

### Mémoire
- **Espace documents par projet** (`project_documents`, panneau dans la page projet) : notes, extraits de code et **images** déposés par l'utilisateur. Injectés dans les prompts selon la tâche, avec budget (12 000 car., 6 000 par document) ; au-delà les documents sont seulement cités. Les images ne partent qu'aux modèles annonçant `vision` (qwen3.8 et gemma4 l'annoncent), 3 au maximum. PDF hors périmètre : extraction trop coûteuse en local.
- **Carnet de projet** (`services/project_memory.py`) assemblé à la demande depuis la base (description, idéation, chantiers en cours, résultats gardés/écartés) et injecté dans toutes les générations de requêtes : veille, veille visuelle, financements. Jamais stocké, donc jamais périmé ; il apprend de ce que tu gardes et de ce que tu jettes.
- Volumétrie mesurée : le projet le plus fourni tient en ~1 800 tokens pour une fenêtre de 16k–32k — pas de recherche vectorielle nécessaire à ce stade.

### Sources de veille
- **Bibliothèque de flux personnelle** (`rss_feeds`, API `/settings/feeds`, UI dans Paramètres) : on ajoute une URL, elle est **vérifiée immédiatement** (un flux mort est refusé avec son motif) et ses **thèmes sont déduits** du titre, des catégories déclarées et des mots récurrents des entrées. À correspondance égale, tes flux passent devant le catalogue intégré.
- Bouton « re-vérifier » par flux : les sources meurent sans prévenir (deux des flux écolo de départ renvoyaient 404 depuis des mois).
- Garde-fou anti-SSRF à l'ajout : uniquement du http(s) public.

### Suivi d'exécution
- **Avancement en direct** (`services/task_progress.py`, champ `progress` de `GET /tasks/{id}`) : étape courante et compteur *n/N* pendant l'analyse. Registre en mémoire — la phase d'analyse tourne dans un savepoint, y écrire depuis une autre session bloquerait sur le verrou de la ligne `tasks`. S'efface après un redémarrage, ce qui signale une tâche morte au lieu de figer un faux avancement.

### Recherche web
- **SearXNG** (`docker compose up -d searxng`, `SEARXNG_URL`) est le backend prioritaire : métamoteur local, ni clé ni quota, lié à `127.0.0.1:8888`. Config dans `searxng/settings.yml` — **`json` doit figurer dans `search.formats`**, sinon l'API répond 403 (le backend le dit explicitement dans les logs).
- Ordre des backends : SearXNG → Brave (si clé) → DuckDuckGo. Repli automatique si SearXNG ne rend rien.
- Contexte : DuckDuckGo répondait 202 sur 100 % des requêtes (veille textuelle à zéro résultat) et l'offre gratuite de Brave n'existe plus. Après bascule : 42 résultats bruts, 11 pertinents sur une veille tech qui en rendait 0.

### Socle
- Scheduler (queue toutes les 2 min, veilles toutes les 15 min, watchdog 5 min, rapports 8h), retry avec backoff.
- **Registre de modèles** : si un modèle Ollama configuré n'existe plus, repli automatique sur un modèle installé ; thinking désactivé par détection de capacités.
- Design system « journal d'atelier » (papier/encre/vermillon, Fraunces + Archivo), PWA installable.
- **152 tests** backend (`./run_tests.sh`), sauvegardes Postgres quotidiennes (`./backups/`), rotation des logs.

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
- « Créer X tâches » en 500 : lecture de `task.dependencies` après commit (lazy-load synchrone interdit en async) → insertion directe dans `task_dependencies`.
- Tâches de code cloisonnées : le HTML ignorait le CSS et le JS produits par les autres tâches → plan de fichiers partagé (`services/project_workspace.py`).
- Code généré encadré de balises ``` : nettoyé avant écriture (`services/code_cleanup.py`).
- Veille visuelle aberrante : le projet n'était jamais lu (requête littérale « veille visuelle »), les requêtes étaient trop longues pour des APIs à mots-clés (« glitch » → 20 images, « glitch art brutalist aesthetic » → 0), et aucun filtrage ne s'appliquait → `services/project_memory.py` + notation par couverture de requête.
- Flux RSS CreativeApplications mort (« RSS Feed Inactive ») → remplacé par Hyperallergic et Dezeen ; Openverse plafonné à 20 (401 au-delà) ; concurrence réseau bridée (DNS du conteneur saturé).
- Are.na : `/v2/search/blocks` renvoie 403 pour tout le monde → on passe par `/v2/search/channels` puis le contenu des collections, ce qui vaut mieux (curation humaine).
- **Streaming Ollama bloquant** : le client *synchrone* était itéré dans une coroutine, gelant toute l'API pendant chaque génération (mesuré : zéro tick de la boucle d'événements en 7,4 s ; health check en échec). Passage à `AsyncClient` + `async for` ; `document_generator` déporté en thread.
- Page projet qui remontait en haut à chaque modification du Gantt : `fetchProjectStats` passait `loading` à `true` et le loader plein écran démontait la page. Il ne s'affiche plus qu'au premier chargement.
- Tâches affichées « en vrac » : le tri topologique du chemin critique n'était pas utilisé. Rang numéroté, badge « À faire maintenant » et marqueur « Bloquée » avec ses dépendances.
- `create_all` au démarrage créait les tables des nouveaux modèles avant Alembic : chaque migration échouait ensuite sur « table already exists » et le schéma pouvait diverger en silence. Le démarrage **vérifie** désormais la révision et prévient si elle est en retard, sans rien créer.
- Rechargement uvicorn déclenché par tout fichier sous `backend/` (y compris les tests) : il tuait les tâches de fond en cours. Surveillance restreinte à `app/`.
- Moodboard qui débordait de toute la page : `<main className="flex-1">` sans `min-w-0` ne peut pas rétrécir sous la largeur intrinsèque de son contenu, et une légende `truncate` (nowrap) imposait 4 972 px dans une fenêtre de 1 440. Corrigé sur les six pages concernées.
- Vignettes chargées en `loading="lazy"` masquées en `display:none` : une image masquée n'entre jamais dans le viewport, donc n'est jamais chargée. Squelette superposé plutôt que masquage.
- Flux d'actualité obsolètes corrigés : Yale E360 → `/feed.xml`, The Ecologist → `/rss` (les anciennes URL renvoyaient 404) ; Prosthetic Knowledge écarté (blog retiré).
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

Sources écartées volontairement : **Unsplash** (API réservée aux usages « non-automated », appel obligatoire à `links.download_location` à chaque sélection, attribution par lien profil UTM — incompatible avec une veille programmée), **Cosmos.so** (section 8(F) de ses conditions : accès automatisé interdit, endpoint privé nécessitant un jeton perso) et **Pinterest** (pas de recherche publique dans l'API officielle, interdiction de stocker les données, et depuis le 18/08/2026 interdiction expresse d'alimenter des modèles d'IA). Ne pas y revenir via des wrappers tiers, qui font le même scraping.

Ce qui dépend de toi : créer la clé gratuite Pexels si tu veux cette source ; installer Tailscale (+ `tailscale serve`), installer l'app ntfy et choisir un topic. Idées ensuite : Web Push natif (une fois en HTTPS), Gantt avec déplacement des échéances, export PDF du briefing.

## 💡 Reprise de session
Lire ce fichier, puis `PROJECT_STRUCTURE.md` pour l'architecture. Lancer : `docker compose up -d`, vérifier `curl localhost:8000/health`, tests : `./run_tests.sh`.
