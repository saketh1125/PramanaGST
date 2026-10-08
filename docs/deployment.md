# Deployment plan — PramanaGST P9

## 1. Architecture chosen

```
browser ──► frontend (nginx:80, static dist/ + /api reverse proxy)
                 │ same-origin, no CORS involved
                 ▼
              api (uvicorn 0.0.0.0:8000, 1 worker)
                 │ offline CSV batch (default) or bolt://neo4j:7687
                 ▼
              neo4j:5.26 (named volume neo4j_data)
```

No PostgreSQL: verified zero references in code — state is CSVs + Neo4j +
in-memory NetworkX. Do not add a database the application does not use.

- Single uvicorn worker is intentional: `_Analytics` is a process-wide lazy
  snapshot. Multi-worker is acceptable (each worker builds its own snapshot)
  but responses may differ briefly after `POST /ingest` until all workers
  rebuild; prefer 1 worker unless load-tested.
- Frontend is static hosting compatible (any CDN/static host works) as long
  as `/api/*` is proxied to the API, or `VITE_API_URL` is baked to the API
  origin at build time.

## 2. Environment reference

See `.env.example`. Summary:

| Variable | Dev default | Prod rule |
|---|---|---|
| `PRAMANAGST_ENV` | `dev` | `prod` disables `/docs`, locks CORS |
| `PRAMANAGST_API_KEY` | unset (open) | **required**; guards `POST /ingest` |
| `PRAMANAGST_DATA_DIR` | repo `generated_data/` | absolute path or mounted volume; `demo_scenarios/` for demos |
| `CORS_ORIGINS` | localhost:5173 ×2 | explicit allowlist (empty = same-origin only) |
| `PRAMANAGST_USE_NEO4J` | unset (offline) | `1` + `NEO4J_URI=bolt://neo4j:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | `neo4j` / `pramanagst` | **real secret** via compose env / secret store |
| `PRAMANAGST_LLM_URL` / `OPENAI_API_KEY` | unset (template narration) | optional; template fallback always works |
| `PORT` / `WORKERS` / `PRAMANAGST_LOG_LEVEL` | 8000 / 1 / INFO | as needed |

Prod fails fast at import when `PRAMANAGST_API_KEY` is missing (or
`NEO4J_PASSWORD` when Neo4j mode is on).

## 3. Security baseline (implemented)

- API-key guard on the mutating `POST /api/v1/ingest` whenever a key is
  configured; reads stay public (documented choice for a demo-grade API).
- Env-driven CORS, tightened methods/headers; `/docs` disabled in prod.
- Neo4j driver errors sanitized to `"Neo4j unavailable"` (full trace logged
  server-side only); no stack traces reach clients.
- Structured JSON logs carry route templates, never raw paths (paths contain
  GSTINs), and never bodies/headers/amounts/keys.
- Request IDs (`X-Request-ID` in/out) on every response, including errors.

Not in scope for this milestone (do before internet exposure): rate limiting,
per-vendor authZ, WAF, secret rotation, backup/restore runbooks.

## 4. Health / readiness

- `GET /api/v1/health` — liveness: process alive, version, neo4j mode. Cheap.
- `GET /api/v1/ready` — readiness: all 5 dataset CSVs present (+ Neo4j
  `verify_connectivity` with 2s timeout when enabled). Gate deploys on this.
- Compose: `neo4j` has a `cypher-shell` healthcheck; `api` depends on it;
  the API image has a `/health` HEALTHCHECK.

## 5. CI (`.github/workflows/ci.yml`)

Backend: install → pytest → regenerate contract schemas and fail on diff →
validate all examples against schemas. Frontend: `npm ci` → oxlint → build.
Docker: `compose config` + build both images.

## 6. Demo data

`backend/ingestion/dataset/demo_scenarios/` — 7 labelled synthetic vendors
(NORMAL / MISMATCH_HEAVY / TAX_SHORTFALL / 2-vendor CIRCULAR / MULTI_HIGH /
loop partner), pinned by `tests/test_demo_scenarios.py`. GHOST_INVOICE is
intentionally absent (pipeline auto-emits GSTR-1 returns; covered by unit
tests — see its README). Serve with
`PRAMANAGST_DATA_DIR=backend/ingestion/dataset/demo_scenarios`.

## 7. Staging checklist (exact next step)

1. Provision host (any Docker host: single VM, Render/Fly.io/AWS ECS —
   pick by cost/simplicity; all support compose-style env + volumes).
2. Managed Neo4j (Aura) **or** the compose `neo4j` service with a persistent
   volume; set `NEO4J_*` from the secret store, never in git.
3. `cp .env.example .env`, set `PRAMANAGST_ENV=prod`, `PRAMANAGST_API_KEY`
   (32+ random bytes), `CORS_ORIGINS=https://<dashboard-host>`.
4. `docker compose up --build -d`; gate on `GET /api/v1/ready == 200`.
5. Smoke: `/risks`, `/risks/{gstin}`, `/explain`, `/risk-summary`,
   `/graph/ego/{gstin}`, dashboard load, 401 without key, 404 envelope,
   template narration (no LLM env), logs contain no secrets.
6. If Neo4j mode: `POST /api/v1/ingest?persist=true` with key, re-run ready.

## 8. Honest status

Dockerfiles + compose + CI were written but **not built here** (no Docker
daemon on this machine) — CI's docker job is the first real build gate.
Everything else above (config, auth, CORS, logging, health/ready, pins,
tests, prod-mode uvicorn smoke) was executed and verified locally.
