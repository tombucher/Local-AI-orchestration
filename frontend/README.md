# Frontend — Orchestrateur IA

React 18 + TypeScript + Vite, design system « journal d'atelier ». Servi en dev par le conteneur `frontend` (http://localhost:5173).

## Commandes

```bash
npm install            # sur l'hôte (pour tsc / build) — le conteneur a son propre node_modules
npx tsc --noEmit       # 0 erreur attendue
npm run build          # build de production (dist/)
docker compose exec frontend npm install   # après un changement de package.json
```

## Design system

- Tokens Tailwind (`tailwind.config.js`) : `paper` / `paper-warm` / `paper-card` (fonds), `ink` / `ink-soft` / `ink-faint` / `ink-line` (texte, filets), `accent` vermillon (actions), `highlight` jaune, statuts `success` / `warning` / `danger` / `info` désaturés.
- Fontes (Fontsource, hors ligne) : **Fraunces** pour les titres (`font-display`, appliquée automatiquement aux h1-h3), **Archivo** pour l'interface, **JetBrains Mono** pour code et chiffres.
- Classes maison (`src/index.css`) : `.kicker` (petites capitales), `.standfirst` (exergue), `.rule` / `.rule-strong` (filets), `.figures` (chiffres tabulaires), `animate-fade-up`, `animate-pop`.
- Règles : angles droits (`rounded-none`), **aucune couleur Tailwind brute** (`blue-600`…), primitives dans `src/components/ui/` (Button, Card, Input, Select, ConfirmDialog, FieldError, Loader).

## Architecture

- `pages/` gardent l'état et les appels API ; `components/` sont visuels (ex. `TaskDetail` = `TaskHeader` + `TaskStatusPanel` + `TaskReviewActions` + `TaskResultPanel`).
- `services/api.ts` : axios avec JWT automatique et **toast d'erreur global** ; passer `{ silentError: true }` pour le polling et les 404 attendus.
- `hooks/usePolling.ts` : polling qui s'arrête sur statut terminal et se met en pause quand l'onglet est caché.
- `stores/` : Zustand (auth, projects, tasks, timer).
- PWA : `public/manifest.webmanifest` + icônes SVG, métas dans `index.html`.

Arborescence complète dans `../PROJECT_STRUCTURE.md`.
