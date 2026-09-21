# 🚀 Orchestrateur IA — journal d'atelier

Outil personnel de pilotage de projets créatifs (art numérique + tech) assisté par une IA **100 % locale** (Ollama). Il décompose les projets, génère code et documents, fait de la veille textuelle, visuelle et sur les appels à projets, et rédige chaque matin un briefing qui donne envie de s'y mettre.

État détaillé et roadmap : [`PROJECT_STATE.md`](PROJECT_STATE.md) · Architecture : [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) · Lancement pas à pas : [`launch.md`](launch.md)

---

## ✨ Fonctionnalités

**Pilotage** — idéation par dialogue (streaming), analyse IA en tâches avec dépendances, chemin critique + frise Gantt, score de maturité, chrono par tâche.

**Action** — génération de code (revue, édition inline, regénération avec instructions), génération de documents, veille par scope (actualités, tech, culturelle, financements, académique, visuelle) récurrente ou one-shot, alimentée par DuckDuckGo et des flux RSS curatés avec anti-doublon, rapport radar avec affinage, appels à projets avec extraction des deadlines, moodboard d'images libres trié par un modèle vision qui regarde et décrit chaque référence.

**Proactivité** — briefing du matin (top 3, prochaine action évidente par projet, échéances), détection de projets qui stagnent avec suggestions de relance, célébrations et séries.

**Socle** — espace documents par projet (texte, code, images) injecté dans les prompts, carnet de projet partagé par toutes les actions, plan de fichiers partagé entre les tâches de code, scheduler APScheduler, retry avec backoff, watchdog, registre de modèles Ollama avec repli automatique, design system éditorial, PWA installable, tests backend, sauvegardes Postgres quotidiennes.

---

## ⚡ Installation

### Prérequis
- Docker Desktop
- [Ollama](https://ollama.ai) natif macOS avec au moins un modèle local, par exemple :
  ```bash
  ollama pull qwen3.8:27b-mlx    # code, documents, analyse
  ollama pull gemma4:12b-mlx     # tâches courtes (veille, briefing)
  ```

### Configuration
```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY
# Éditer .env : POSTGRES_PASSWORD, SECRET_KEY, DATABASE_URL (même mot de passe)
```

### Démarrer
```bash
docker compose up -d
docker compose exec backend alembic upgrade head   # obligatoire : le démarrage ne crée plus les tables
```

Au démarrage, le backend compare le schéma à la dernière migration et prévient dans les logs
s'il est en retard (`⚠️ Schéma en retard`). Il ne crée plus aucune table de lui-même : Alembic
est seul maître du schéma.

| Service | URL |
|---|---|
| Interface | http://localhost:5173 |
| API Swagger | http://localhost:8000/docs |
| Open WebUI (chat Ollama) | http://localhost:3001 (localhost uniquement) |
| SearXNG (métamoteur de veille) | http://localhost:8888 (localhost uniquement) |
| PostgreSQL | 127.0.0.1:5432 (localhost uniquement) |

Créer un compte via l'interface, puis choisir tes modèles dans **Paramètres**.

---

## 🧭 Premiers pas

1. **Nouveau projet** → décris ton idée dans le dialogue d'idéation, puis finalise.
2. **Analyser avec l'IA** → coche les tâches proposées, elles sont créées avec leurs dépendances et leurs veilles.
3. Sur une tâche **code** ou **document** : « Générer maintenant », puis valide, édite ou regénère avec des instructions.
4. Crée une **veille** : la **portée** décide de tout — « Visuelle » alimente le Moodboard en images, les autres portées ramènent des articles. Le titre de la tâche n'y change rien.
5. Dans **Paramètres → Mes flux de veille**, ajoute les flux RSS que tu croises : ils alimentent la veille en priorité.
6. Chaque matin, le **briefing** sur le dashboard te dit par quoi commencer.

---

## 🛠 Commandes utiles

```bash
docker compose ps                         # état des services
docker compose logs -f backend            # logs backend
./run_tests.sh                            # 182 tests backend
docker compose up -d --build backend      # rebuild après changement de dépendances
docker compose exec backend alembic upgrade head
ls backups/                               # sauvegardes Postgres quotidiennes (14 jours)
```

Restaurer une sauvegarde :
```bash
gunzip -c backups/orchestrator-YYYYMMDD-HHMM.sql.gz | docker compose exec -T postgres psql -U orchestrator_user orchestrator
```

---

## ⚙️ Variables d'environnement (`.env`)

| Variable | Rôle |
|---|---|
| `POSTGRES_PASSWORD`, `DATABASE_URL` | Base de données (le mot de passe doit être identique dans les deux) |
| `SECRET_KEY` | Signature des JWT (64 hex) |
| `BACKEND_CORS_ORIGINS` | Origines autorisées (liste JSON) |
| `OLLAMA_MODEL_PROMPT` | Modèle rapide pour veille / scoring / briefing (`gemma4:12b-mlx`) |
| `AIDES_TERRITOIRES_API_KEY` | Optionnel — aides publiques FR avec deadlines structurées |
| `SEARXNG_URL`, `SEARXNG_SECRET` | Métamoteur local, **backend de recherche prioritaire** (ni clé ni quota). `SEARXNG_SECRET` : 64 hex |
| `BRAVE_SEARCH_API_KEY` | Repli optionnel — l'offre gratuite de Brave n'existe plus |
| `PEXELS_API_KEY` | Optionnel — photographies sous licence permissive pour le moodboard ([clé gratuite](https://www.pexels.com/api/)) |
| `ARENA_ACCESS_TOKEN` | Optionnel — moodboard enrichi des collections Are.na ([jeton gratuit](https://dev.are.na/oauth/applications)) ; images = références, **pas** libres de droits |
| `NTFY_TOPIC` (+ `NTFY_URL`, `NTFY_TOKEN`) | Optionnel — envoie le briefing de 8h sur le téléphone via l'app ntfy |
| `APP_PUBLIC_URL` | Optionnel — URL publique (Tailscale) utilisée dans les notifications |

Les modèles pour le code, l'idéation et l'analyse se choisissent par utilisateur dans **Paramètres**. Si un modèle configuré n'est plus installé, le registre bascule automatiquement sur un modèle disponible (avertissement dans les logs).

---

## 📱 Depuis le téléphone (Tailscale)

Le frontend appelle l'API en chemin relatif (`/api`) via le proxy Vite : une seule origine, donc l'app marche depuis n'importe quel hôte. Pour y accéder hors du Mac, en HTTPS et sans rien exposer sur Internet :

1. Installer Tailscale sur le Mac et le téléphone (même compte), activer MagicDNS et HTTPS dans la console.
2. Sur le Mac : `tailscale serve --bg --https=443 http://localhost:5173`
3. Ouvrir `https://<mac>.<tailnet>.ts.net` sur le téléphone → « Ajouter à l'écran d'accueil » (PWA).
4. Mettre cette URL dans `APP_PUBLIC_URL` pour que les notifications ntfy ouvrent l'app.

## 🤖 Orchestration

```
CREATED → READY → GENERATING → MANUAL_REVIEW → COMPLETED
                      ↓
                    FAILED → READY (retry 1 → 5 → 15 min, 3 essais)
```

| Job | Fréquence |
|---|---|
| Traitement de la file (veilles, recherche, admin en automatique ; code et documents à la demande) | 2 min |
| Occurrences de veille dues | 15 min |
| Watchdog des générations bloquées | 5 min |
| Briefing quotidien | 8h00 |

---

## 🔒 Sécurité

Isolation par utilisateur sur tous les endpoints, JWT 7 jours, bcrypt, Postgres et Open WebUI non exposés sur le réseau, anti-brute-force sur le login, garde-fou SSRF sur les récupérations de pages, dépendances auditées (`pip-audit`, `npm audit`). Détails dans `PROJECT_STATE.md`.

---

## 🧱 Stack

**Recherche** : SearXNG auto-hébergé (métamoteur) · flux RSS étiquetés · Openverse / Wikimedia / Are.na pour les images.

**Backend** : FastAPI 0.141 · SQLAlchemy 2.0 async · PostgreSQL 15 · Alembic · Pydantic 2 · APScheduler · ollama-python · aiohttp/BeautifulSoup/feedparser.

**Frontend** : React 18 · TypeScript 5 · Vite 5 · react-router 7 · Zustand · TailwindCSS 3 · react-hook-form + zod · react-markdown · Fraunces / Archivo / JetBrains Mono (Fontsource).

---

## 🆘 Dépannage

| Symptôme | Piste |
|---|---|
| Génération qui échoue « model not found » | Le modèle configuré a été supprimé d'Ollama : rechoisis-en un dans Paramètres (`ollama list`) |
| Veille sans résultats, 403 DuckDuckGo | Rate-limit temporaire ; ajoute `BRAVE_SEARCH_API_KEY` |
| Veille sans résultats | `docker compose ps searxng` ; si l'API renvoie 403, vérifier que `json` figure dans `search.formats` de `searxng/settings.yml` puis `docker compose restart searxng` |
| Veille textuelle pauvre | Ajoute tes flux dans **Paramètres → Mes flux de veille** ; ils sont vérifiés et étiquetés, et passent avant le catalogue par défaut |
| Moodboard vide ou très peu d'images | Normal si les sources couvrent mal le sujet : renseigne des mots-clés courts et concrets sur le topic (ils servent directement de requêtes) |
| Tâche bloquée en GENERATING | Le watchdog la passe en FAILED après 15 min, puis retry. Attention : toute modification sous `backend/app/` redémarre le serveur et tue les tâches en cours |
| Moodboard vide | Il se remplit **tout seul** depuis une veille de portée **visuelle** ; une veille d'actualités ne ramène que des liens et n'y contribue pas. Sinon, bouton « Ajouter une image » pour déposer une URL ou un fichier |
| Erreur « attached to a different loop » dans les tests | Relancer `./run_tests.sh` (moteur de test par fonction) |
| Backend injoignable | `docker compose logs backend`, puis `docker compose restart backend` |
