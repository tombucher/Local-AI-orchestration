# Orchestrateur IA — journal d'atelier

Outil personnel de pilotage de projets créatifs (art numérique + tech), assisté par une IA **100 % locale** (Ollama). Rien ne sort de la machine.

Tu tiens tes projets dans des **fiches `.md`** sur ton Mac ; l'outil les lit, en fait des tâches, génère code et documents, fait de la veille (articles, images, appels à projets), et chaque matin te dit **par quoi commencer** et **ce qui t'attend**.

État détaillé et historique : [`PROJECT_STATE.md`](PROJECT_STATE.md) · Architecture : [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)

---

## Au quotidien

**Ouvrir l'atelier** : double-clic sur `atelier.command` (ou `./atelier.command` dans un terminal). Il lance Docker Desktop et Ollama s'ils dorment, démarre les services, applique les migrations et ouvre http://localhost:5173. `./atelier.command stop` arrête tout.

**Le journal** (page d'accueil) :
1. **Le briefing du matin** — deux phrases, le top 3 du jour, la prochaine action évidente des cinq projets prioritaires. Préparé à 8h, ou à la première ouverture de la journée.
2. **Ce qui t'attend** — tout ce qui ne bougera pas sans toi : les résultats **à valider**, les tâches **en échec** (bouton *Relancer*), ce qui est **en cours**, et les tâches **à lancer**, par projet dans ton ordre de priorité (bouton *Lancer*). L'outil ne lance jamais une génération de code ou de document tout seul : c'est toi qui donnes le feu vert, ici ou dans le projet.
3. **Projets en cours** et **échéances** d'appels à projets.

**Les projets** : une ligne par projet (rang, état, ce qui attend, avancement, prochaine échéance), dépliable. Glisse les lignes pour fixer ta priorité ; mets un projet **en pause** (avec date de reprise) ou **en sommeil** pour le sortir du briefing sans rien perdre.

**Les fiches `.md`** : dans *Paramètres → Dossier de projets*, choisis un dossier du Mac. Chaque sous-dossier de premier niveau est un **espace** (Recherche, Mairie, Composer…), chaque dossier en dessous un **projet**, avec sa fiche :

```markdown
# Data-compost
Texte libre : l'intention, les contraintes, les idées.

## [ ] Écrire la note d'intention
type : document · échéance : 2026-11-14 · priorité : P1
- [ ] Trois mots-clés
- [ ] Un paragraphe par partie

## [x] Contacter le fablab
```

La fiche est relue toutes les 30 s ; les fichiers générés sont rangés dans le dossier du projet, et une tâche terminée coche sa case. Le bouton *Écrire la fiche* fait l'inverse : il crée dossier et fiche à partir d'un projet de l'outil.

**Pas de tâches ?** Dans un projet, *Discuter avec l'IA* : elle connaît la fiche, pose des questions, puis propose des tâches que tu choisis.

**Le résultat pose des questions ?** Sous chaque tâche terminée, un bloc **Ta réponse** : ce que tu y écris est lu par les tâches qui dépendent de celle-ci, par le carnet du projet (donc par toutes ses veilles), et par la tâche elle-même si tu la relances. Ta réponse est aussi écrite dans la fiche `.md`, sous la tâche (`Réponse : …`), et tu peux l'y écrire directement. Le bouton *Reporter dans le projet* va plus loin : la **description du projet est réécrite** pour intégrer ta réponse (ce qui y était « à préciser » l'est, le reste ne bouge pas), les mots-clés des veilles évoluent et la prochaine occurrence est avancée, et la fiche `.md` reçoit le tout. Les panneaux *Description du projet* et *Veilles du projet* montrent l'état réel ; la version précédente de la description est gardée.

**Les veilles** : une veille récurrente est un *sujet* (mots-clés, portée, fréquence). À chaque échéance, l'outil crée une **nouvelle tâche** « Veille — … · date » ; les occurrences passées restent, avec leurs résultats, mais n'encombrent pas la fiche `.md` (une seule ligne `type: veille` y suffit). *Affiner* sur une occurrence, ou *Ta réponse* sur n'importe quelle tâche du projet, change les suivantes.

---

## Installation

### Prérequis
- Docker Desktop
- [Ollama](https://ollama.com) natif macOS, avec deux modèles (variantes `-mlx` pour Apple Silicon) :
  ```bash
  ollama pull qwen3.8:27b-mlx    # code, documents, analyse, discussion
  ollama pull gemma4:12b-mlx     # tâches courtes : veille, scoring, briefing
  ```

### Première fois
```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # → SECRET_KEY, puis une seconde pour SEARXNG_SECRET
# Éditer .env : POSTGRES_PASSWORD, SECRET_KEY, SEARXNG_SECRET
./atelier.command
```

Le premier démarrage construit les images (quelques minutes). Puis créer un compte dans l'interface et vérifier les modèles dans **Paramètres**.

| Service | URL |
|---|---|
| Interface | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| SearXNG (métamoteur de veille) | http://localhost:8888, localhost uniquement |
| PostgreSQL | 127.0.0.1:5432, localhost uniquement |
| Open WebUI (chat Ollama, optionnel) | http://localhost:3001 — `docker compose --profile chat up -d` |

---

## Commandes utiles

```bash
./atelier.command                          # ouvrir l'atelier (idempotent)
./atelier.command stop                     # tout arrêter
docker compose logs -f backend             # logs du backend
./run_tests.sh                             # tests backend (~300)
docker compose up -d --build backend       # rebuild après changement de dépendances
docker compose exec backend alembic upgrade head
ls backups/                                # sauvegardes Postgres quotidiennes (14 jours)
```

Restaurer une sauvegarde :
```bash
gunzip -c backups/orchestrator-YYYYMMDD-HHMM.sql.gz | docker compose exec -T postgres psql -U orchestrator_user orchestrator
```

| Problème | Piste |
|---|---|
| Rien ne se génère | Le journal l'affiche : « Ollama ne répond pas ». Lancer l'app Ollama. |
| « plus installé » dans Paramètres | Le modèle a été supprimé : `ollama list`, puis rechoisir ; en attendant l'outil se replie sur un modèle installé. |
| Backend muet | `docker compose logs backend` ; vérifier que la migration est passée (`⚠️ Schéma en retard` dans les logs). |
| Tâche figée « en cours » | Le watchdog la passe en échec après 2 h sans signe de vie ; *Relancer* depuis le journal. |

---

## Variables d'environnement (`.env`)

| Variable | Rôle |
|---|---|
| `POSTGRES_PASSWORD` | Base de données (DATABASE_URL est recalculée par docker-compose) |
| `SECRET_KEY` | Signature des JWT (64 hex) |
| `SEARXNG_SECRET` | Clé de l'instance SearXNG (64 hex), backend de recherche prioritaire |
| `OLLAMA_MODEL_PROMPT` | Modèle rapide pour veille, scoring et briefing (`gemma4:12b-mlx`) |
| `PROJECTS_HOST_DIR` | Dossier du Mac partagé avec le backend (défaut : `~/Documents`) ; le dossier de projets se choisit dedans, dans Paramètres |
| `TIMEZONE`, `BRIEFING_HOUR` | Heure du briefing (défaut : `Europe/Paris`, 8h) |
| `AIDES_TERRITOIRES_API_KEY` | Optionnel — aides publiques FR avec deadlines structurées |
| `PEXELS_API_KEY` | Optionnel — photographies sous licence permissive pour le moodboard |
| `ARENA_ACCESS_TOKEN` | Optionnel — collections Are.na dans le moodboard (références, **pas** libres de droits) |
| `NTFY_TOPIC` (+ `NTFY_URL`, `NTFY_TOKEN`) | Optionnel — briefing de 8h sur le téléphone via l'app ntfy |
| `APP_PUBLIC_URL` | Optionnel — URL publique (Tailscale) utilisée dans les notifications |

Les modèles pour le code, les textes, la discussion et l'analyse se choisissent par compte dans **Paramètres**. Les modèles cloud d'Ollama sont refusés : tout reste local.

---

## Depuis le téléphone (Tailscale)

L'app appelle l'API en chemin relatif, donc marche depuis n'importe quel hôte, et la navigation tient sur un petit écran (menu ☰).

1. Installer Tailscale sur le Mac et le téléphone (même compte), activer MagicDNS et HTTPS.
2. Sur le Mac : `tailscale serve --bg --https=443 http://localhost:5173`
3. Ouvrir `https://<mac>.<tailnet>.ts.net` sur le téléphone → « Ajouter à l'écran d'accueil » (PWA).
4. Mettre cette URL dans `APP_PUBLIC_URL` pour que les notifications ntfy ouvrent l'app.

---

## Orchestration

```
CREATED ──(Lancer)──▶ GENERATING ──▶ MANUAL_REVIEW ──(Valider)──▶ COMPLETED
   │                      │
   └─(Mettre en file)─▶ READY        FAILED ──(Relancer)──▶ READY (3 essais : 1, 5, 15 min)
```

| Job | Fréquence |
|---|---|
| File d'attente : veilles, recherches, administratif en automatique ; code et documents sur ton feu vert | 2 min |
| Occurrences de veille dues (projets actifs seulement) | 15 min |
| Watchdog des générations sans signe de vie | 5 min |
| Relecture du dossier de projets (fiches `.md`) | 30 s |
| Briefing | 8h, heure de Paris ; rattrapé à l'ouverture |

Un projet en pause ou en sommeil ne lance rien et sort du briefing ; l'archivage annule ses tâches restantes.

---

## Sécurité

Isolation par compte sur tous les endpoints, JWT 7 jours, bcrypt, Postgres et SearXNG liés à localhost, anti-brute-force sur le login, garde-fou SSRF sur les récupérations de pages, modèles cloud verrouillés, dépendances auditées (`pip-audit`, `npm audit`).

---

## Stack

**Backend** : FastAPI · SQLAlchemy 2 async · PostgreSQL 15 · Alembic · APScheduler · ollama-python · aiohttp / BeautifulSoup / feedparser.

**Frontend** : React 18 · TypeScript · Vite · react-router 7 · Zustand · TailwindCSS 3 · Fraunces / Archivo / JetBrains Mono.

**Recherche** : SearXNG auto-hébergé · flux RSS personnels · Openverse / Wikimedia / AIC / Met / Internet Archive / Are.na pour les images.
