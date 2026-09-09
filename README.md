# TrustLens

A reliability layer for AI answers. TrustLens generates or ingests an AI answer,
extracts atomic claims, checks them against supplied evidence with deterministic
signals, and returns a **reliability score (0–100)** and a **label**
(`CERTAIN` / `UNCERTAIN` / `NEEDS_VERIFICATION`) — plus PII redaction, a human
review queue with label override, and a full audit trail.

The LLM never decides the label. The application does.

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — components, boundaries, data model, flows, reliability policy.
- **[TECH_STACK.md](TECH_STACK.md)** — the locked-in technology decisions.
- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** — the ~4-minute jury walkthrough.

## The loop

```
Question → AI Answer → Claims → Evidence → Reliability Score → Label → Explanation → Human Review → Audit
```

## Two modes

| Mode | Endpoint | Use |
|---|---|---|
| A — generate + evaluate | `POST /api/v1/answer` | TrustLens produces the answer from the sources |
| B — evaluate existing output | `POST /api/v1/evaluate` | score an answer another AI produced (enterprise path) |

## Quick start (Docker)

```bash
cp .env.example .env
# set JWT_SECRET; leave LLM_PROVIDER=stub to run with no external LLM
docker compose up --build
```

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js UI |
| API | http://localhost:8000 | docs at `/api/docs` |
| Postgres | localhost:5432 | `trustlens` / `trustlens` |

On start the backend runs `alembic upgrade head` and (when `SEED_ON_START=1`, the
default) loads demo users + demo cases.

**Demo accounts** — password `trustlens`:
`user@trustlens.dev` · `editor@trustlens.dev` · `admin@trustlens.dev`
Analysis is open to everyone; the Review and Audit tools require `EDITOR`/`ADMIN`.

## Quick start (local, no Docker)

```bash
# backend
cd backend
python -m venv .venv && . .venv/Scripts/activate     # Windows
pip install -r requirements.txt
export DATABASE_URL=sqlite+pysqlite:///./trustlens.db  # or a Postgres DSN
export JWT_SECRET=dev-secret
alembic upgrade head
python -m app.scripts.seed          # demo users + demo cases (optional)
uvicorn app.main:app --reload       # :8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev                         # :3000
```

## Try the API

```bash
curl -s http://localhost:8000/api/v1/evaluate -H 'content-type: application/json' -d '{
  "question": "Who created the Linux kernel?",
  "answer": "The Linux kernel was created by Linus Torvalds in 1991.",
  "evidence": ["The Linux kernel was first released by Linus Torvalds in 1991."]
}' | python -m json.tool
```

## Frontend

`frontend/` is a Next.js 14 + TypeScript + Tailwind app (App Router). Pages:
`/analyze` (the core loop), `/history` + `/history/[id]`, `/review` (editor queue
with approve / reject / escalate + label override), `/audit`. A teammate may
replace it via the `frontend` branch — this is the fallback.

```bash
cd frontend && npm run build && npm run typecheck
```

## Embeddings note

On first real use, `EmbeddingService` downloads `all-MiniLM-L6-v2` (~90 MB) from
HuggingFace. If it can't (offline / no cache) it logs a warning and falls back to
deterministic hashed vectors — the pipeline keeps working, semantic scores are
approximate. Pre-cache:
`python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`.

## Tests

```bash
cd backend && pytest          # SQLite in-memory + stub LLM + hermetic embeddings, no network
```

44 tests. Deterministic safety guarantees (no-evidence → NEEDS_VERIFICATION,
contradiction cap, fail-safe, RBAC, PII masking, label override) are asserted on
every backend.

## Demo cases

`data/demo_cases.json` — six deterministic cases, one per outcome
(`linux_supported` → CERTAIN, `library_hours_partial` → UNCERTAIN,
`acme_market_share_unsupported` / `merger_contradiction` / `no_evidence_capital`
→ NEEDS_VERIFICATION, `applicant_pii` shows redaction).
