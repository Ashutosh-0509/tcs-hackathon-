# TrustLens — Architecture

> **Purpose:** This document is the single source of truth for the *structure* of
> TrustLens — its components, boundaries, data model, request flows, and the
> deterministic reliability policy.
>
> Claude Code MUST read this document (and `TECH_STACK.md`) before adding a
> module, changing a boundary, or altering the reliability engine.

---

## 1. What TrustLens is

TrustLens is a **reliability layer for AI answers**. Given a question and a set of
source snippets (evidence), it:

1. Optionally **generates** an answer with a configured LLM (Mode A), or accepts
   an answer produced by another system (Mode B).
2. **Extracts atomic factual claims** from the answer.
3. **Evaluates** each claim against the supplied evidence using deterministic
   signals (evidence support, semantic similarity, uncertainty, relevance,
   contradiction).
4. Produces a **reliability score (0–100)** and a **label**
   (`CERTAIN` / `UNCERTAIN` / `NEEDS_VERIFICATION`) via a fixed policy with
   safety overrides and a fail-safe default.
5. **Redacts PII** before anything is sent to the LLM.
6. **Persists** the question, answer, claims, evidence, score, label, and an
   **audit record**, all under one database transaction.
7. Routes low-confidence answers into a **human review queue** (RBAC: `EDITOR` /
   `ADMIN`).

The LLM never decides the label. The application does.

---

## 2. Architectural style — modular monolith

One FastAPI process. Internal modules have clear boundaries so they can later be
extracted into services, but for the MVP they are Python packages, not containers.

```text
                          ┌─────────────────────────┐
   Next.js frontend ─────▶ │   FastAPI  (app.main)   │
   Enterprise client ────▶ │   /api/v1/*             │
                          └───────────┬─────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             ▼                        ▼                        ▼
      ┌────────────┐          ┌───────────────┐         ┌──────────────┐
      │ AI / LLM   │          │  Evaluation   │         │  Security    │
      │ services   │          │  engine       │         │  layer       │
      │            │          │               │         │              │
      │ LLMProvider│          │ EmbeddingSvc  │         │ PIIService   │
      │  (abstract)│          │ semantic sim  │         │ JWT / RBAC   │
      │ answer     │          │ perplexity    │         │ password hash│
      │ claims     │          │ reliability   │         │ audit        │
      │ explanation│          │  policy       │         │              │
      └─────┬──────┘          └───────┬───────┘         └──────┬───────┘
            └─────────────────────────┼────────────────────────┘
                                      ▼
                         ┌─────────────────────────┐
                         │   PostgreSQL (SQLAlchemy)│
                         │   Alembic migrations     │
                         └─────────────────────────┘
```

### Module boundaries (enforced by convention)

| Package | Owns | May import | Must NOT import |
|---|---|---|---|
| `app.api` | HTTP routing, request/response, auth deps | `schemas`, `services`, `policies`, `db`, `core` | — |
| `app.services` | business logic, orchestration | `policies`, `models`, `schemas`, `core`, `db` | `app.api` |
| `app.policies` | pure deterministic reliability math | `schemas`, `core` | `services`, `api`, `db`, `models` |
| `app.models` | SQLAlchemy ORM entities only | `db.base`, `core` | `services`, `api`, `policies` |
| `app.schemas` | Pydantic DTOs | `core` | everything else |
| `app.core` | config, logging, security primitives, request context | stdlib + libs | project packages |
| `app.db` | engine, session, Base | `core` | `models` (import-time), `services`, `api` |

`app.policies` is deliberately dependency-free (no DB, no network, no LLM) so the
reliability logic is trivially unit-testable and audit-reviewable.

---

## 3. Component responsibilities

### 3.1 API layer — `app/api/v1`

- `routes/health.py` — `GET /api/v1/health` with dependency status (db, llm).
- `routes/auth.py` — `POST /register`, `POST /login` (JWT issuance).
- `routes/answer.py` — `POST /answer` — **Mode A**: generate + evaluate + persist.
- `routes/evaluate.py` — `POST /evaluate` — **Mode B**: evaluate a supplied
  answer + persist.
- `routes/reviews.py` — `GET /reviews` (queue), `GET /reviews/{id}`,
  `POST /reviews/{id}` (decision). `EDITOR`/`ADMIN` only.
- `routes/audit.py` — `GET /audit` — audit timeline. `EDITOR`/`ADMIN` only.

All protected routes resolve the caller from the JWT via `app/api/deps.py`
(`get_current_user`, `require_role(...)`). `user_id` / `role` are **never** read
from the request body.

### 3.2 AI / LLM services — `app/services/llm`

- `base.py` — `LLMProvider` ABC + `ProviderCapabilities`
  (`supports_logprobs`, `supports_embeddings`, `supports_structured_output`,
  `supports_streaming`).
- `openai_compatible.py` — one concrete provider over an OpenAI-compatible HTTP
  API (`httpx`, explicit timeout, bounded retry on transient errors only).
  Reads `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.
- `stub.py` — deterministic offline provider used when `LLM_PROVIDER=stub` or no
  API key is configured, so the demo runs with zero external dependencies. Its
  output is clearly synthetic and it reports `supports_logprobs = False`.
- `factory.py` — `get_llm_provider(settings)` — the only place a provider is
  chosen.

Tasks: `generate_answer(question, evidence)`, `extract_claims(answer)` (structured
JSON, Pydantic-validated), `generate_explanation(context)`. Prompts come from
`app/prompts/*.txt` via `app/prompts/__init__.py` (versioned).

### 3.3 Evaluation engine — `app/services/evaluation.py` + `app/policies`

Pipeline (`EvaluationEngine.evaluate`):

```text
answer + claims + evidence
   │
   ├─▶ EmbeddingService.embed(claims), embed(evidence)      (app/services/embeddings.py)
   │      cosine similarity  →  per-claim semantic_support ∈ [0,1]
   │
   ├─▶ evidence support      per-claim best-match ≥ τ_support  →  supported / unsupported
   │
   ├─▶ contradiction check   negation / antonym heuristic against best evidence
   │
   ├─▶ relevance             cosine(question, answer) ∈ [0,1]
   │
   ├─▶ uncertainty           1 - normalized_perplexity  (or neutral 0.5 if unavailable)
   │
   └─▶ ReliabilityPolicy.score(signals)     →  final_score 0-100
       ReliabilityPolicy.label(score, flags) →  label + reasons  (safety overrides)
```

`EmbeddingService` wraps `sentence-transformers` (`all-MiniLM-L6-v2`). If the
model cannot load (offline CI), it falls back to a deterministic hashed
bag-of-words vector — **clearly logged**, never silently. Cosine similarity is
`numpy` / `scikit-learn`.

**Perplexity:** if the provider reports `supports_logprobs`, compute
`PPL = exp(-mean(log p(token)))` from returned logprobs. Otherwise the response
carries `perplexity: null, perplexity_available: false` and the uncertainty
signal uses a neutral prior. Perplexity is **never fabricated**.

### 3.4 Reliability policy — `app/policies/reliability.py`

Pure functions. No I/O.

```text
weights  (configurable):   evidence 0.50 | semantic 0.25 | uncertainty 0.15 | relevance 0.10
final_score = 100 * (evidence*0.50 + semantic*0.25 + uncertainty*0.15 + relevance*0.10)

thresholds (configurable): CERTAIN_THRESHOLD=80, UNCERTAIN_THRESHOLD=50
   score ≥ 80            → CERTAIN
   50 ≤ score < 80       → UNCERTAIN
   score < 50            → NEEDS_VERIFICATION

SAFETY OVERRIDES (win over the number):
   evaluation_failed              → NEEDS_VERIFICATION
   no_evidence_available          → NEEDS_VERIFICATION
   critical_unsupported_claim     → NEEDS_VERIFICATION
   contradictory_evidence         → at most UNCERTAIN

FAIL-SAFE: any unhandled path / insufficient evidence → NEEDS_VERIFICATION.
Never emit CERTAIN when evidence is absent or the evaluator errored.
```

Every label carries a machine-readable `reasons: string[]` explaining which rule
fired.

### 3.5 Security layer

- `app/services/pii.py` — `PIIService.scan(text)` → findings;
  `PIIService.redact(text)` → masked text + findings. Deterministic regex
  recognizers for **PAN, Aadhaar, Indian phone, email, credit card (Luhn), bank
  account**, plus an optional Presidio pass when `PII_USE_PRESIDIO=true` and the
  package is installed. PII is redacted **before** any LLM call and before
  persistence (only the redacted answer/question are stored).
- `app/core/security.py` — Argon2 password hashing (`passlib[argon2]`, bcrypt
  fallback), JWT encode/decode (`python-jose`), `create_access_token`.
- `app/api/deps.py` — `get_current_user`, `require_role(*roles)` for RBAC
  (`USER` < `EDITOR` < `ADMIN`).

### 3.6 Persistence & audit — `app/services/audit.py`, `app/db`

One SQLAlchemy session per request (`app/db/session.py`, dependency
`get_db`). The answer/evaluate flow commits **once**: question + answer + claims +
evidence + reliability score + audit log succeed or roll back together
(TECH_STACK §75).

---

## 4. Data model

```text
users
  id (uuid, pk)
  email (unique, citext-ish lower)
  password_hash
  role                enum: USER | EDITOR | ADMIN
  created_at

questions
  id (uuid, pk)
  request_id          e.g. TRUST-2026-000123  (indexed)
  text                redacted question text
  mode                enum: GENERATE | EVALUATE
  created_by -> users.id (nullable for anonymous demo)
  created_at

answers
  id (uuid, pk)
  question_id -> questions.id
  text                redacted answer text
  source              enum: TRUSTLENS_LLM | EXTERNAL
  model               model name string (nullable)
  perplexity          float (nullable)
  perplexity_available bool
  created_at

claims
  id (uuid, pk)
  answer_id -> answers.id
  text
  is_critical         bool
  supported           bool
  semantic_support    float [0,1]
  evidence_support    float [0,1]
  contradicted        bool
  best_evidence_id -> evidence.id (nullable)

evidence
  id (uuid, pk)
  question_id -> questions.id
  snippet             redacted snippet text
  ordinal             int

reliability_scores
  id (uuid, pk)
  answer_id -> answers.id (unique)
  evidence_score      float [0,1]
  semantic_score      float [0,1]
  uncertainty_score   float [0,1]
  relevance_score     float [0,1]
  final_score         int [0,100]
  label               enum: CERTAIN | UNCERTAIN | NEEDS_VERIFICATION
  reasons             json (string[])
  weights             json  (snapshot of weights used)
  thresholds          json  (snapshot of thresholds used)
  created_at

reviews
  id (uuid, pk)
  answer_id -> answers.id
  status              enum: PENDING | APPROVED | REJECTED | ESCALATED
  decision_note       text (nullable)
  reviewed_by -> users.id (nullable until decided)
  created_at
  decided_at (nullable)

audit_logs
  id (uuid, pk)
  request_id          (indexed)
  actor_id -> users.id (nullable)
  action              e.g. ANSWER_GENERATED, ANSWER_EVALUATED, REVIEW_DECIDED, LOGIN
  entity_type         e.g. answer | review
  entity_id           uuid
  metadata            json  (latency_ms, model, label, score, pii_findings_count, ...)
  created_at
```

`claims`, `reliability_scores.reasons/weights/thresholds`, and
`audit_logs.metadata` use `JSON` columns (JSONB on PostgreSQL). Only redacted
text is ever stored (TECH_STACK §74).

Migrations: Alembic, `app/alembic/`, initial revision `0001_initial`. Run with
`alembic upgrade head` (invoked automatically by the backend container entrypoint
in `docker-compose`).

---

## 5. Request flows

### 5.1 Mode A — `POST /api/v1/answer` (generate + evaluate)

```text
client → FastAPI
  middleware: assign request_id TRUST-2026-000123, start latency timer
  auth: optional (demo) — actor may be anonymous or a USER
  1. PIIService.redact(question, source_snippets)      → redacted inputs + findings
  2. provider.generate_answer(redacted_question, redacted_evidence)
  3. provider.extract_claims(answer)                   → claims[] (Pydantic-validated)
  4. EvaluationEngine.evaluate(answer, claims, evidence, logprobs?)
        → signals, flags, per-claim results
  5. ReliabilityPolicy.score + label                   → final_score, label, reasons
  6. optional provider.generate_explanation(...)       → human-readable text
  7. BEGIN TX: persist question, answer, evidence, claims, reliability_score,
               audit_log(ANSWER_GENERATED, metadata)   COMMIT
  8. if label != CERTAIN: create reviews row (PENDING)
  response: { request_id, answer, claims, metrics, reliability, security, explanation }
```

### 5.2 Mode B — `POST /api/v1/evaluate` (evaluate external answer)

Same as Mode A but step 2 is skipped; `answer` comes from the request body,
`answers.source = EXTERNAL`, audit action `ANSWER_EVALUATED`. This is the
strategic TCS integration path (TECH_STACK §94–96).

### 5.3 Review — `POST /api/v1/reviews/{id}`

`EDITOR`/`ADMIN` only. Sets `reviews.status`, `reviewed_by`, `decided_at`,
`decision_note`; writes `audit_log(REVIEW_DECIDED)`. The reliability score is
immutable — a review records a human decision, it does not rewrite history.

### 5.4 Failure handling

Any exception in steps 2–6 → the engine returns `evaluation_failed = true`, the
policy forces `NEEDS_VERIFICATION`, the partial result + audit log are still
persisted, and the response is `200` with `reliability.label =
NEEDS_VERIFICATION` and `reasons` explaining the failure. LLM timeout (default
`LLM_TIMEOUT_SECONDS=30`) is one such failure.

---

## 6. Configuration (`app/core/config.py`, pydantic-settings)

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://trustlens:trustlens@postgres:5432/trustlens` | DB DSN |
| `JWT_SECRET` | — (required) | token signing |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `LLM_PROVIDER` | `stub` | `stub` \| `openai_compatible` |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `gpt-4o-mini` | model name (not hardcoded elsewhere) |
| `LLM_API_KEY` | `""` | secret; empty → forces `stub` |
| `LLM_TIMEOUT_SECONDS` | `30` | outbound LLM timeout |
| `LLM_MAX_RETRIES` | `2` | transient-error retries only |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `CERTAIN_THRESHOLD` | `80` | |
| `UNCERTAIN_THRESHOLD` | `50` | |
| `WEIGHT_EVIDENCE` / `WEIGHT_SEMANTIC` / `WEIGHT_UNCERTAINTY` / `WEIGHT_RELEVANCE` | `0.50 / 0.25 / 0.15 / 0.10` | policy weights |
| `EVIDENCE_SUPPORT_THRESHOLD` | `0.55` | cosine cutoff for "supported" |
| `PII_USE_PRESIDIO` | `false` | enable optional Presidio pass |
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | explicit CORS allowlist |
| `RATE_LIMIT_PER_MINUTE` | `60` | basic app-level rate limit |

Secrets are never logged. `.env` is git-ignored; `.env.example` is committed.

---

## 7. Cross-cutting concerns

- **Request IDs** — `app/core/request_context.py` holds a `ContextVar`;
  `app/core/middleware.py` assigns `TRUST-<year>-<zero-padded-seq>` per request,
  echoes it in the `X-Request-ID` response header, and threads it into every log
  line, LLM call, and audit row.
- **Logging** — stdlib `logging`, JSON-ish structured formatter, fields:
  `request_id, ts, level, endpoint, user_id?, latency_ms?, model?, eval_status?`.
  A redaction filter drops known secret/PII patterns as defence-in-depth.
- **Errors** — a single exception handler maps domain errors to structured JSON
  `{ error, detail, request_id }`; unexpected errors are logged with the
  request_id and return `500` without leaking internals.
- **CORS** — explicit allowlist from config; no wildcard in non-dev.
- **Rate limiting** — in-process token bucket keyed by client IP / user id
  (MVP-grade; production delegates to a gateway).

---

## 8. Deployment

`docker-compose.yml` — three services:

```text
postgres   postgres:16-alpine      volume: pgdata           healthcheck: pg_isready
backend    ./backend               depends_on: postgres     entrypoint: alembic upgrade head && uvicorn app.main:app
frontend   ./frontend              depends_on: backend      next dev / next start
```

No separate containers for claim / evidence / scoring / PII / LLM (TECH_STACK
§54). `docker compose up` brings up the whole stack.

---

## 9. Testing strategy (`backend/tests`)

| File | Covers |
|---|---|
| `test_reliability_policy.py` | score formula, thresholds, every safety override, fail-safe, weight config |
| `test_pii.py` | PAN / Aadhaar / phone / email / card detection + masking, redaction-before-LLM |
| `test_rbac.py` | USER cannot reach `/reviews` or `/audit`; EDITOR/ADMIN can; body-supplied role ignored |
| `test_evaluation.py` | no-evidence → NEEDS_VERIFICATION, contradiction → ≤ UNCERTAIN, supported → CERTAIN |
| `test_api_flow.py` | `/evaluate` end-to-end with stub provider + deterministic embeddings |

Tests run against SQLite in-memory with the stub provider and the hashed-embedding
fallback, so `pytest` needs no Postgres and no network.

---

## 10. Future evolution (not built now)

Extraction seams already in place: `LLMProvider` → LLM Gateway service;
`app.policies` + `EvaluationEngine` → Evaluation service; `PIIService` → PII/DLP
service; `audit_logs` → Audit service. Add pgvector + a `documents`/`chunks`
schema for RAG. Swap JWT for OIDC/Entra ID behind the existing `deps.py` seam.
None of this changes the public `/api/v1` contract.

---

END OF ARCHITECTURE.md
