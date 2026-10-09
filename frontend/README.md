# CS-IRCFS District Planning Dashboard (React)

React 18 + TypeScript (strict) + Vite + Tailwind, with TanStack Query, React Router, Zod, Recharts and react-leaflet. FastAPI serves the build at `/app/`. Pages are migrated from the classic dashboard (`../dashboard/`) one at a time; the sidebar links to classic pages until their React version exists.

## Commands

```bash
npm ci              # install exactly what package-lock.json records
npm run dev         # http://localhost:5173/app/ — needs the API on http://127.0.0.1:8000
npm run typecheck   # TypeScript, app and Vite config
npm run lint        # ESLint
npm test            # Vitest + Testing Library
npm run build       # production build in dist/
```

In development Vite forwards `/api`, the sign-in page and the classic assets to the API (`CS_IRCFS_API` overrides the address), so the session cookie works as in production. With local development sign-in turned off (`ENVIRONMENT=development`, `REQUIRE_API_KEY=false`) the app opens as a local administrator.

## Layout

```text
src/
  app/           providers (session), routing, layouts (shell)
  components/    ui (cards, badges, metric card), feedback (data states), navigation, charts, maps
  features/      one folder per workspace; overview/ is the executive dashboard
  services/api/  fetch client and Zod schemas mirroring the backend responses
  i18n/          en.ts (source of keys) and rw.ts (Kinyarwanda, needs field review)
  lib/           formatting, design-token colours
  styles/        tokens.css (the palette) and index.css
```

Rules: every figure comes from the API and is validated by a schema; missing data is shown as missing, never as zero; colours come from tokens; text comes from `i18n`. See [docs/design-system.md](../docs/design-system.md).
