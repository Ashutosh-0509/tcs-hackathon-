# Deployment

Two hosts: the Next.js frontend on **Vercel**, the FastAPI backend + PostgreSQL on
**Railway** (Vercel cannot run Python or a database).

```
Vercel  tcs-hackathon.vercel.app   ──REST──▶  Railway  <backend>.up.railway.app
                                                 │
                                            Railway PostgreSQL
```

## Backend — Railway

Service builds from `backend/` (Dockerfile). Required variables:

| Var | Value |
|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway reference) |
| `JWT_SECRET` | a long random string |
| `LLM_PROVIDER` | `openai_compatible` |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | `openai/gpt-oss-120b` |
| `LLM_API_KEY` | the Groq key (never commit it) |
| `CORS_ALLOW_ORIGINS` | `https://tcs-hackathon.vercel.app` |
| `SEED_ON_START` | `1` for the demo, `0` otherwise |

The container runs `alembic upgrade head`, optional seed, then `uvicorn` on `$PORT`.
Health: `GET /api/v1/health`.

## Frontend — Vercel

- Root directory: `frontend/`
- Env: `NEXT_PUBLIC_API_BASE_URL` = the Railway backend URL (e.g.
  `https://tcs-hackathon-backend.up.railway.app`)
- Framework preset: Next.js (auto)

## Wiring order

1. Deploy backend on Railway, note its public URL.
2. Set `NEXT_PUBLIC_API_BASE_URL` on Vercel to that URL, deploy frontend.
3. Set `CORS_ALLOW_ORIGINS` on Railway to the Vercel URL, redeploy backend.
4. Both are git-connected to `main` for auto-deploy on push.
