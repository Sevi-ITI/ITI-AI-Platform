# ITI AI Console (admin-ui)

Next.js 16.3 (App Router, TypeScript) console for the ITI AI Platform. Only its server code talks to
FastAPI; the browser never does, and the console holds no API keys (the person's session only).

## Run (from `admin-ui\`)

1. Copy `.env.example` to `.env.local` (git-ignored).
2. `npm install` (exact versions; `.npmrc` keeps them exact).
3. `npm run dev` → http://127.0.0.1:3000 (FastAPI must run on 127.0.0.1:8000).

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` / `npm start` | Dev server / production server on 127.0.0.1:3000 |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npm run gen:api` | Regenerates `src/lib/api/schema.d.ts` from FastAPI's `/openapi.json` (commit the result) |
