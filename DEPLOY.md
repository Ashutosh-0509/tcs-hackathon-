# Deployment

Two hosts: the Next.js frontend on **Vercel**, the FastAPI backend + PostgreSQL on
**Railway** (Vercel cannot run Python or a database).

```
Vercel  tcs-hackathon.vercel.app   ──REST──▶  Railway  <backend>.up.railway.app
                                                 │
                                            Railway PostgreSQL
```

## Status

| Piece | State |
|---|---|
| Frontend | ✅ live — https://tcs-hackathon.vercel.app (Vercel project `dhruvghanchi/tcs-hackathon`, deployed via `vercel deploy --prod` from `frontend/`; SSO protection disabled) |
| `NEXT_PUBLIC_API_BASE_URL` | set to `https://tcs-hackathon-api.up.railway.app` (placeholder — update once the backend is up) |
| Backend + Postgres | ⛔ not deployed — Railway free plan is at its resource limit ("Free plan resource provision limit exceeded") |
| GitHub auto-deploy | ❌ not connected — the repo `Ashutosh-0509/tcs-hackathon-` is not on the Vercel/Railway account, so neither can watch it for pushes |

## Finish the backend — Render blueprint (recommended)

The repo has [`render.yaml`](render.yaml). In Render:

1. **New +  →  Blueprint**, pick this repo. Render provisions `trustlens-api`
   (Docker, `backend/Dockerfile.slim`) + `trustlens-db` (free PostgreSQL).
2. On the `trustlens-api` service, set **`LLM_API_KEY`** to the Groq key
   (it's the only `sync: false` var).
3. First deploy runs `alembic upgrade head`. Note the service URL
   (`https://trustlens-api-XXXX.onrender.com`).
4. Point the frontend at it:
   ```
   cd frontend
   vercel env rm NEXT_PUBLIC_API_BASE_URL production preview -y
   printf '<render-url>' | vercel env add NEXT_PUBLIC_API_BASE_URL production --visibility config --no-sensitive
   printf '<render-url>' | vercel env add NEXT_PUBLIC_API_BASE_URL preview --visibility config --no-sensitive
   vercel deploy --prod
   ```

Notes: the slim image runs `EMBEDDING_PROVIDER=hashed` (no torch — fits Render's
512 MB free instance); the LLM entailment check is unaffected, semantic-similarity
numbers are approximate. Render free web services cold-start after ~15 min idle.

## Other backend options

**A — Railway (recommended, ~2 min once unblocked)**
1. Upgrade Railway to Hobby, or delete an unused project to free a slot.
2. Create project `tcs-hackathon` → add **PostgreSQL** → add a service from
   Dockerfile with **root directory `backend`**.
3. Set variables:

   | Var | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `JWT_SECRET` | long random string |
   | `LLM_PROVIDER` | `openai_compatible` |
   | `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
   | `LLM_MODEL` | `openai/gpt-oss-120b` |
   | `LLM_API_KEY` | the Groq key |
   | `CORS_ALLOW_ORIGINS` | `https://tcs-hackathon.vercel.app` |
   | `CORS_ALLOW_ORIGIN_REGEX` | `https://tcs-hackathon(-[a-z0-9-]+)?\.vercel\.app` (allows Vercel preview deploys) |
   | `SEED_ON_START` | `1` for the demo |

4. Generate a domain. Then on Vercel:
   `vercel env rm NEXT_PUBLIC_API_BASE_URL production` and re-add it with the real
   Railway URL, then `vercel deploy --prod` from `frontend/`.

Or from a machine with the Railway CLI:
```bash
cd backend && railway up      # signs in, creates project + service, deploys
```

**B — Render (free)**
New Web Service → connect the GitHub repo → root `backend`, Docker runtime →
add a free PostgreSQL → same variables as above → its URL goes in
`NEXT_PUBLIC_API_BASE_URL` on Vercel.

## GitHub auto-deploy

For pushes to `main` to redeploy automatically, the repo owner (`Ashutosh-0509`)
must install the **Vercel** and **Railway** GitHub apps on
`tcs-hackathon-` and grant access, or the repo moves under an account that already
has them. Until then, redeploy with `vercel deploy --prod` (frontend) and
`railway up` / a Railway redeploy (backend).

## Local

`docker compose up --build` runs the whole stack (see README).
