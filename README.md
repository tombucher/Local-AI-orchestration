# 🚀 Orchestrateur IA — journal d'atelier

Outil personnel de pilotage de projets créatifs (art numérique + tech) assisté par une IA **100 % locale** (Ollama). Il décompose les projets, génère code et documents, fait de la veille textuelle, visuelle et sur les appels à projets, et rédige chaque matin un briefing qui donne envie de s'y mettre.

État détaillé et roadmap : [`PROJECT_STATE.md`](PROJECT_STATE.md) · Architecture : [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) · Lancement pas à pas : [`launch.md`](launch.md)

---

## ✨ Fonctionnalités

**Pilotage** — idéation par dialogue (streaming), analyse IA en tâches avec dépendances, chemin critique + frise Gantt, score de maturité, chrono par tâche.

**Action** — génération de code (revue, édition inline, regénération avec instructions), génération de documents, veille par scope (actualités, tech, culturelle, financements, académique, visuelle) récurrente ou one-shot, rapport radar avec affinage, appels à projets avec extraction des deadlines, moodboard d'images libres.

**Proactivité** — briefing du matin (top 3, prochaine action évidente par projet, échéances), détection de projets qui stagnent avec suggestions de relance, célébrations et séries.

**Socle** — scheduler APScheduler, retry avec backoff, watchdog, registre de modèles Ollama avec repli automatique, design system éditorial, PWA installable, tests backend, sauvegardes Postgres quotidiennes.

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
docker compose exec backend alembic upgrade head
```

| Service | URL |
|---|---|
| Interface | http://localhost:5173 |
| API Swagger | http://localhost:8000/docs |
| Open WebUI (chat Ollama) | http://localhost:3001 (localhost uniquement) |
| PostgreSQL | 127.0.0.1:5432 (localhost uniquement) |

Créer un compte via l'interface, puis choisir tes modèles dans **Paramètres**.

---

## 🧭 Premiers pas

1. **Nouveau projet** → décris ton idée dans le dialogue d'idéation, puis finalise.
2. **Analyser avec l'IA** → coche les tâches proposées, elles sont créées avec leurs dépendances et leurs veilles.
3. Sur une tâche **code** ou **document** : « Générer maintenant », puis valide, édite ou regénère avec des instructions.
4. Crée une **veille** (type + fréquence, dont « une seule fois ») ; les veilles **visuelles** alimentent le **Moodboard** du projet.
5. Chaque matin, le **briefing** sur le dashboard te dit par quoi commencer.

---

## 🛠 Commandes utiles

```bash
docker compose ps                         # état des services
docker compose logs -f backend            # logs backend
./run_tests.sh                            # 39 tests backend
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
| `BRAVE_SEARCH_API_KEY` | Optionnel — remplace DuckDuckGo (plus fiable) |
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

**Backend** : FastAPI 0.141 · SQLAlchemy 2.0 async · PostgreSQL 15 · Alembic · Pydantic 2 · APScheduler · ollama-python · aiohttp/BeautifulSoup/feedparser.

**Frontend** : React 18 · TypeScript 5 · Vite 5 · react-router 7 · Zustand · TailwindCSS 3 · react-hook-form + zod · react-markdown · Fraunces / Archivo / JetBrains Mono (Fontsource).

---

## 🆘 Dépannage

| Symptôme | Piste |
|---|---|
| Génération qui échoue « model not found » | Le modèle configuré a été supprimé d'Ollama : rechoisis-en un dans Paramètres (`ollama list`) |
| Veille sans résultats, 403 DuckDuckGo | Rate-limit temporaire ; ajoute `BRAVE_SEARCH_API_KEY` |
| Tâche bloquée en GENERATING | Le watchdog la passe en FAILED après 15 min, puis retry |
| Erreur « attached to a different loop » dans les tests | Relancer `./run_tests.sh` (moteur de test par fonction) |
| Backend injoignable | `docker compose logs backend`, puis `docker compose restart backend` |
