# Atlas UI (React + TypeScript)

Minimal chat front end for the Atlas orchestrator. One `<Chat />` component:
maintains a per-tab session id (so the server keeps multi-turn memory), POSTs
questions to `/ask`, renders answers, and surfaces any generated PDF/PPTX
deliverables as download links.

## Run

Start the orchestrator API in one terminal:

```bash
python -m orchestrator.serve      # serves /ask + /healthz on :8080
```

Then the UI (Vite proxies /ask to :8080):

```bash
cd ui
npm install
npm run dev                        # http://localhost:5173
```

## Files

- `src/Chat.tsx` — chat UI, session handling, suggestion chips
- `src/api.ts` — typed `/ask` client + artifact extraction
- `src/styles.css` — dark theme
- `vite.config.ts` — dev proxy to the orchestrator

## Build

```bash
npm run build                      # tsc + vite build -> dist/
```
