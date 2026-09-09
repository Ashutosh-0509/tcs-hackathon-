# TrustLens

A reliability layer for AI answers. TrustLens generates or ingests an AI answer,
extracts atomic claims, checks them against supplied evidence with deterministic
signals, and returns a **reliability score (0–100)** and a **label**
(`CERTAIN` / `UNCERTAIN` / `NEEDS_VERIFICATION`) — plus PII redaction, a human
review queue, and a full audit trail.

The LLM never decides the label. The application does.

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — components, boundaries, data model, flows, reliability policy.
- **[TECH_STACK.md](TECH_STACK.md)** — the locked-in technology decisions.

## Two modes

| Mode | Endpoint | Use |
|---|---|---|
| A — generate + evaluate | `POST /api/v1/answer` | demo: TrustLens produces the answer |
| B — evaluate existing output | `POST /api/v1/evaluate` | enterprise: score another AI's answer |

## Quick start (Docker)

```bash
cp .env.example .env
# set JWT_SECRET; leave LLM_PROVIDER=stub to run with no external LLM
docker compose up --build
```

- API: http://localhost:8000  · Docs: http://localhost:8000/api/docs
- Frontend: http://localhost:3000
- Postgres: localhost:5432 (`trustlens` / `trustlens`)

The backend container runs `alembic upgrade head` on start.

## Quick start (backend only, local)

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows
pip install -r requirements.txt
export DATABASE_URL=sqlite+pysqlite:///./trustlens.db   # or a real Postgres DSN
export JWT_SECRET=dev-secret
alembic upgrade head
uvicorn app.main:app --reload
```

## Try it

```bash
# Mode B — evaluate an answer against evidence (no auth required for demo)
curl -s http://localhost:8000/api/v1/evaluate -H 'content-type: application/json' -d '{
  "question": "Who invented Python?",
  "answer": "Python was created by Guido van Rossum in 1991.",
  "evidence": ["Python was created by Guido van Rossum and first released in 1991."]
}' | python -m json.tool
```

## Embeddings note

On first real use, `EmbeddingService` downloads `all-MiniLM-L6-v2` (~90 MB) from
HuggingFace. If it can't (offline / no cache), it logs a warning and falls back to
deterministic hashed vectors — the pipeline keeps working, semantic scores are
approximate. To pre-cache: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`.

## Tests

```bash
cd backend
pytest            # SQLite in-memory + stub LLM + hermetic embeddings, no network
```

The suite is hermetic (`HF_HUB_OFFLINE=1` in `tests/conftest.py`). Deterministic
safety guarantees (no-evidence → NEEDS_VERIFICATION, contradiction cap, fail-safe,
RBAC, PII masking) are asserted on every backend; the exact CERTAIN/UNCERTAIN
boundary for the positive path is only asserted when the real embedding model is
cached locally.

## Demo cases

`data/demo_cases.json` holds deterministic cases with expected labels
(`python_supported` → CERTAIN, `telephone_partial` → UNCERTAIN,
`unsupported_ceo` → NEEDS_VERIFICATION).
