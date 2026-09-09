# TrustLens — Technology Stack

> **Purpose:** This document is the single source of truth for the technologies,
> frameworks, libraries, infrastructure, and development conventions used to
> build TrustLens.
>
> Claude Code MUST read this document before selecting dependencies or introducing
> new technologies.
>
> The project is a hackathon MVP with enterprise-grade architectural principles.
> The stack must remain simple, modular, reliable, and fast to implement.

---

# 1. TECHNOLOGY PHILOSOPHY

TrustLens follows these principles:

1. Prefer mature and stable technologies.
2. Prefer Python for AI/evaluation workloads.
3. Prefer TypeScript for frontend development.
4. Use PostgreSQL as the primary persistent database.
5. Keep AI provider integrations abstract.
6. Avoid unnecessary infrastructure.
7. Avoid microservices for the MVP.
8. Prefer deterministic libraries for deterministic tasks.
9. Never fabricate AI metrics or provider capabilities.
10. Every dependency must have a clear purpose.

---

# 2. HIGH-LEVEL STACK

```text
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│                                                         │
│  Next.js + React + TypeScript + Tailwind CSS            │
└───────────────────────────┬─────────────────────────────┘
                            │
                            │ REST / JSON
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     BACKEND                             │
│                                                         │
│  Python + FastAPI + Pydantic + SQLAlchemy               │
└───────────────────────────┬─────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
     AI / LLM          Evaluation          Security
     Layer             Engine              Layer
          │                 │                  │
          ▼                 ▼                  ▼
     LLM Provider      Embeddings          PII Detection
                       + Scoring            + Masking
          │                 │
          └─────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                    DATABASE                             │
│                                                         │
│                    PostgreSQL                           │
└─────────────────────────────────────────────────────────┘
```

# 3. FRONTEND

## Framework

**Next.js** — use the App Router.

Responsibilities: user interface, authentication state, user dashboard, editor
dashboard, API communication, reliability visualization, review workflow,
loading/error states.

The frontend MUST NOT contain reliability-scoring business logic. The backend is
the source of truth.

## Language

**TypeScript** for all frontend code. Do not use plain JavaScript unless there is
a specific compatibility requirement.

## UI Library

**Tailwind CSS.** The UI should be clean, professional, enterprise-oriented,
responsive, accessible, and simple enough for a hackathon demo. Avoid excessive
animations.

## Recommended frontend structure

```text
frontend/
├── app/
│   ├── page.tsx
│   ├── login/
│   ├── dashboard/
│   ├── review/
│   └── api/
├── components/
│   ├── AnswerCard.tsx
│   ├── ReliabilityBadge.tsx
│   ├── ScoreCard.tsx
│   ├── EvidencePanel.tsx
│   ├── ClaimsPanel.tsx
│   ├── WarningPanel.tsx
│   ├── ReviewQueue.tsx
│   └── AuditTimeline.tsx
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── types.ts
├── hooks/
├── types/
└── styles/
```

# 4. BACKEND

**Python 3.12+** for: LLM integration, claim extraction, evidence evaluation,
semantic similarity, perplexity, reliability scoring, PII detection, API layer,
database integration. Python is preferred because the AI/NLP ecosystem is
significantly stronger.

# 5. API FRAMEWORK

**FastAPI** is the primary backend framework: REST API, request validation,
response serialization, authentication middleware, error handling, dependency
injection, API documentation. Development endpoints: `/api/docs`, `/api/redoc`.

# 6. API STYLE

REST APIs, JSON primary format.

```text
POST /api/v1/answer
{ "question": "Who invented Python?",
  "source_snippets": ["Python was created by Guido van Rossum."] }
→ { "answer": "...", "claims": [], "metrics": {}, "reliability": {}, "security": {} }
```

# 7. DATA VALIDATION

**Pydantic** models for API request/response schemas, configuration, internal
validation. Never trust raw request payloads.

# 8. ORM

**SQLAlchemy 2.x** for PostgreSQL: ORM models, queries, relationships,
transactions, database abstraction. Do not place complex business logic inside
ORM models — business logic belongs in service modules.

# 9. DATABASE

**PostgreSQL** — primary database for users, questions, answers, claims,
evidence, reliability scores, reviews, audit logs, configuration.

# 10. WHY POSTGRESQL

Mature relational model, strong transactions, JSON support, excellent Python
support, enterprise adoption, easy local development, optional pgvector later.

# 11. VECTOR SEARCH

MVP: vector database is NOT required. Source snippets are passed directly to the
evaluation pipeline. Optional: PostgreSQL + pgvector before any separate vector
DB. Do not introduce Pinecone, Weaviate, Milvus, Chroma, etc. without demonstrated
need.

# 12. DATABASE MIGRATIONS

**Alembic** for schema migrations, database versioning, reproducible
environments. Must support `alembic upgrade head`.

# 13. LLM ARCHITECTURE

LLM providers MUST be abstracted. Do not tightly couple business logic to one
provider.

```python
class LLMProvider(ABC):
    def generate_answer(self, ...): ...
    def extract_claims(self, ...): ...
    def generate_explanation(self, ...): ...
```

# 14. LLM PROVIDER

Configurable through environment variables:

```text
LLM_PROVIDER=openai
LLM_MODEL=<configured-model>
LLM_API_KEY=<secret>
```

The MVP uses exactly ONE configured provider. Do not implement multiple providers
unless required.

# 15. LLM SDK

Use the official SDK / an OpenAI-compatible HTTP client for the selected
provider. Do not introduce LangChain merely for calling an LLM.

`FastAPI → LLM Service → Provider SDK` is preferred.

# 16. AI TASKS

- **Answer generation:** question → answer
- **Claim extraction:** generated answer → atomic factual claims
- **Explanation generation:** claims + evidence + scores + reliability result →
  human-readable explanation

# 17. LLM SHOULD NOT CONTROL

The LLM must NOT independently determine: final reliability label,
authentication, authorization, PII security decisions, audit records, database
integrity, threshold calculations, workflow status, editor permissions. These are
deterministic application responsibilities.

# 18. EMBEDDINGS

Embeddings for semantic comparison: `claim → embedding → compare → evidence
embedding`. Similarity metric: **cosine similarity**.

# 19. EMBEDDING IMPLEMENTATION

Preferred MVP option: **sentence-transformers**, lightweight model
`all-MiniLM-L6-v2`. Use a local model if it runs reliably; a managed embedding
API may be used instead if easier to deploy. Implementation hidden behind
`EmbeddingService`.

# 20. SEMANTIC SCORE

Normalized to `0.0 → 1.0`. The system distinguishes semantic similarity from
factual correctness. Similarity is only one evaluation signal.

# 21. PERPLEXITY

Auxiliary uncertainty metric. If the LLM API exposes token log probabilities:
`PPL = exp(-1/N * Σ log(P(token_i)))`.

# 22. PERPLEXITY FALLBACK

If the provider does not expose log probabilities, DO NOT invent perplexity,
return a random value, or pretend the value is provider-generated. Instead:

```json
{ "perplexity": null, "perplexity_available": false }
```

The evaluation pipeline continues using other signals.

# 23. OPTIONAL LOCAL PERPLEXITY

A local causal LM may estimate perplexity, but it must be clearly identified as an
auxiliary metric — never "Probability that the answer is true."

# 24. PII DETECTION

Deterministic and NLP-based. Recommended MVP: Regex + custom recognizers +
optional Presidio.

# 25. MICROSOFT PRESIDIO

May be used for advanced PII detection and anonymization (named entities, regex
recognizers, custom recognizers, anonymization, masking). Presidio is not a
complete security guarantee; additional controls remain required.

# 26. CUSTOM PII RULES

Explicit rules for Indian identifiers: PAN, Aadhaar, Phone, Email, Credit Card,
Bank Account. Do not store real sensitive values in demo data — synthetic/test
values only.

# 27. PII PIPELINE

```text
User Input → PII Detector → (No PII) → LLM
                          → (PII Detected) → Mask / Redact → LLM
```

# 28. SECURITY PRINCIPLE

The AI provider receives the minimum information necessary. `PAN: <value>` →
`PAN: [REDACTED]`.

# 29. RELIABILITY ENGINE

Deterministic. Inputs: Evidence Support, Semantic Support, Uncertainty, Answer
Relevance, Contradiction flags, Evidence availability.

# 30. RELIABILITY FORMULA

```text
Evidence Support   50%
Semantic Support   25%
Uncertainty        15%
Answer Relevance   10%

final_score = evidence*0.50 + semantic*0.25 + uncertainty*0.15 + relevance*0.10
```

Convert to `0–100`.

# 31. RELIABILITY THRESHOLDS

```text
80–100 → CERTAIN
50–79  → UNCERTAIN
0–49   → NEEDS_VERIFICATION
```

Configurable: `CERTAIN_THRESHOLD=80`, `UNCERTAIN_THRESHOLD=50`.

# 32. SAFETY OVERRIDES

Numerical score cannot override critical safety conditions:

```text
Contradictory evidence     → UNCERTAIN
No evidence                → NEEDS_VERIFICATION
Critical unsupported claim  → NEEDS_VERIFICATION
Evaluation failure         → NEEDS_VERIFICATION
```

# 33. FAIL-SAFE PRINCIPLE

If the evaluator cannot establish sufficient evidence, NEVER return CERTAIN.
Default fallback: `NEEDS_VERIFICATION`.

# 34. BACKEND DEPENDENCIES

`fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `sqlalchemy`, `alembic`,
`psycopg`, `python-dotenv`, `httpx`, `numpy`, `scikit-learn`,
`sentence-transformers`. Additional dependencies only when justified.

# 35. OPTIONAL PYTHON DEPENDENCIES

`presidio-analyzer`, `presidio-anonymizer`, `transformers`, `torch`,
`python-multipart`, `pypdf`. Use only if the corresponding feature is implemented.

# 36. AUTHENTICATION

JWT-based authentication. `python-jose` or equivalent maintained JWT library.
Passwords must be hashed. Never store plaintext passwords.

# 37. PASSWORD HASHING

Preferred: **Argon2**. Fallback: **bcrypt**. Do not implement custom password
hashing.

# 38. AUTHORIZATION

RBAC. Roles: `USER`, `EDITOR`, `ADMIN`. Authorization happens on the backend.
Frontend hiding a button is NOT authorization.

# 39. HTTP SERVER

**Uvicorn.** `uvicorn app.main:app --reload`. Production container runs Uvicorn
appropriately.

# 40. LOGGING

Standard `logging` framework. Log: request_id, timestamp, endpoint, user_id where
appropriate, latency, model, evaluation status, errors. Never log: API keys,
passwords, raw PAN, raw Aadhaar, full sensitive customer records.

# 41. REQUEST IDs

Every API request gets a unique request ID, e.g. `TRUST-2026-000123`, used across
API logs, LLM calls, evaluation, audit records, errors.

# 42. HTTP CLIENT

**httpx** for outbound HTTP. Configure timeout, retry where safe, error handling.
Never retry blindly on non-idempotent operations.

# 43. CONFIGURATION

**pydantic-settings**:

```python
class Settings(BaseSettings):
    database_url: str
    llm_provider: str
    llm_model: str
    llm_api_key: str
    certain_threshold: int = 80
    uncertain_threshold: int = 50
```

# 44. ENVIRONMENT MANAGEMENT

Development: `.env`. Repository: `.env.example`. Never commit `.env`, API keys,
passwords, JWT secrets, database credentials.

# 45. API DOCUMENTATION

FastAPI OpenAPI docs remain enabled during development (`/api/docs`).

# 46. TESTING

Backend: **pytest**. API tests: pytest + httpx. Categories: unit, integration,
API, security, reliability regression.

# 47. CRITICAL UNIT TESTS

Mandatory: score calculation, threshold logic, safety overrides, no-evidence
handling, contradiction handling, PII masking, RBAC, fail-safe behavior.

# 48. DEMO DATA

Deterministic demo cases in `data/demo_cases.json`.

# 49. FRONTEND-BACKEND COMMUNICATION

`Next.js → HTTPS/REST → FastAPI`. Do not connect the frontend directly to
PostgreSQL. Do not expose database credentials to the browser.

# 50. API CLIENT

Centralized API client `frontend/lib/api.ts`: `submitQuestion()`,
`getReviewQueue()`, `getReview()`, `submitReview()`, `getAuditLogs()`. Avoid
scattering raw `fetch()` calls.

# 51. TYPES

Frontend API types correspond to backend schemas.
`type ReliabilityLabel = "CERTAIN" | "UNCERTAIN" | "NEEDS_VERIFICATION";`

# 52. CONTAINERIZATION

Docker. Required: `backend/Dockerfile`, `frontend/Dockerfile`,
`docker-compose.yml`.

# 53. LOCAL DEVELOPMENT

`docker compose up` eventually starts frontend, backend, PostgreSQL.

# 54. MVP INFRASTRUCTURE

Three primary containers: frontend, backend, postgres. Do NOT create separate
containers for claim/evidence/scoring/PII/LLM services — backend modules for the
MVP.

# 55. ARCHITECTURAL STYLE

Modular monolith. `FastAPI → {AI Services, Evaluation, Security} → PostgreSQL`.

# 56. WHY MODULAR MONOLITH

Fast implementation, simple deployment, low operational overhead, easy debugging,
clear architecture. Internal module boundaries still allow future extraction.

# 57. OPTIONAL RAG STACK

If RAG becomes necessary: `Document parser → Chunker → EmbeddingService →
PostgreSQL + pgvector → Retriever → Evidence`. No separate vector infrastructure
for the MVP.

# 58. DOCUMENT PROCESSING

Optional `pypdf` for PDF text extraction. Only add document upload after core
Q&A + reliability evaluation is stable.

# 59. FRONTEND OPTIONAL COMPONENT LIBRARY

`shadcn/ui` or Radix UI may be used if already available. Do not spend
significant hackathon time customizing a UI framework.

# 60. CODE QUALITY

Backend: PEP 8, type hints, docstrings for important services, small modules,
explicit error handling. Frontend: TypeScript, reusable components, strict
typing, no duplicated API logic.

# 61. FORMATTERS / LINTERS

Backend: **ruff**. Frontend: ESLint + Prettier.

# 62. GIT

Branches: `main`, `develop`, `feature/*` (feature branches optional for a small
team). Commit messages describe the change (`feat: add reliability scoring
engine`).

# 63. CI/CD

Optional for the hackathon. Future: GitHub Actions (Lint → Tests → Build →
Security Scan → Deploy).

# 64. OBSERVABILITY

MVP: structured application logs, request IDs, latency tracking, audit database.
Future: OpenTelemetry, Prometheus, Grafana, Arize Phoenix, Langfuse, TruLens.

# 65. EVALUATION FRAMEWORKS

RAGAS, DeepEval, TruLens, RAGChecker, Arize Phoenix, Langfuse — NOT mandatory for
the MVP. The core evaluator stays understandable and controlled by the TrustLens
codebase.

# 66. WHY NOT USE RAGAS DIRECTLY FOR EVERYTHING?

TrustLens requires an application-level workflow: Generate → Evaluate → Label →
Explain → Review → Audit. TrustLens implements its core reliability policy
independently. RAGAS can become a future benchmarking integration.

# 67. WHY NOT LANGCHAIN?

TrustLens MVP does not require agent/RAG complexity. Preferred: `FastAPI →
LLMProvider → Provider SDK`. LangChain/LangGraph can be evaluated later.

# 68. WHY NOT MICROSERVICES?

The MVP does not need independent scaling of every component. Modular monolith
now; future extraction of PII Service, Evaluation Service, LLM Gateway, Audit
Service if scale requires.

# 69. WHY NOT KAFKA?

The core request-response workflow does not require event streaming.

# 70. WHY NOT REDIS?

Optional. Do not introduce unless there is a real requirement for caching, rate
limiting, background task coordination, or session management. PostgreSQL is
sufficient for the hackathon.

# 71. ASYNC PROCESSING

MVP: synchronous API processing where latency is acceptable. Future: Celery / RQ /
cloud queue for large documents, batch evaluation, offline benchmarking.

# 72. SECURITY STACK

MVP: HTTPS, JWT, RBAC, Argon2/bcrypt, PII detection, PII masking, input
validation, environment secrets, structured audit logs. Future: OAuth2/OIDC,
Enterprise SSO, Entra ID, Okta, Secrets Manager, KMS, WAF, API Gateway.

# 73. ENTERPRISE IDENTITY

Hackathon uses local JWT. Production supports OAuth2, OIDC, Enterprise SSO, Entra
ID, Okta. The authentication service stays abstract enough for future enterprise
identity integration.

# 74. DATA STORAGE RULES

Store: question, answer, claims, evidence, scores, reliability label, review
decision, audit metadata. Avoid storing sensitive raw PII unless explicitly
required — store redacted representation where possible.

# 75. DATABASE TRANSACTIONS

Operations involving answer + claims + scores + audit record use appropriate
transactions. An answer must not appear persisted if critical evaluation records
failed.

# 76. CACHE POLICY

No cache for MVP. Future candidates: embedding results, repeated questions, static
evidence, model metadata. Caching must never bypass security or produce stale
enterprise answers.

# 77. RATE LIMITING

MVP: basic application-level rate limiting may be implemented. Production: API
Gateway, Redis, WAF.

# 78. API SECURITY

All protected endpoints validate authentication, authorization, input, content
size, request structure. Never trust `user_id`, `role`, `editor_id` from frontend
payloads — these come from authenticated server-side context.

# 79. CORS

Configure CORS explicitly. Dev: localhost frontend. Production: specific
enterprise frontend origins. Do NOT use unrestricted CORS in production.

# 80. TIMEOUTS

External LLM requests have explicit timeouts (e.g. 30s), configurable. On
timeout: `NEEDS_VERIFICATION` or a structured evaluation failure.

# 81. RETRY POLICY

Retries only for transient failures. Do not retry invalid requests, auth
failures, malformed prompts, policy violations. Retries have a bounded limit.

# 82. AI COST CONTROL

Avoid unnecessary LLM calls: one answer generation call, one claim extraction
call, optional explanation call. Future: batch claims, cache embeddings, smaller
models for simple tasks.

# 83. MODEL AGNOSTICISM

Business logic must not contain `if model == "specific-model"`. `LLMProvider`
exposes normalized capabilities.

# 84. CAPABILITY DETECTION

```python
class ProviderCapabilities:
    supports_logprobs: bool
    supports_embeddings: bool
    supports_structured_output: bool
    supports_streaming: bool
```

Prevents unsupported features from being falsely reported.

# 85. STRUCTURED LLM OUTPUT

Where supported, use structured JSON output for claim extraction. Validate with
Pydantic. Never blindly trust LLM-generated JSON.

# 86. PROMPT MANAGEMENT

Prompts live in `backend/app/prompts/` (`answer.txt`, `claim_extraction.txt`,
`explanation.txt`). Prompt versions are tracked (`claim_extraction_v1`).

# 87. MODEL CONFIGURATION

Model name configurable via `LLM_MODEL`. Do not hardcode provider-specific models.

# 88. DEVELOPMENT ENVIRONMENT

Python 3.12+, Node.js 20+, npm/pnpm, PostgreSQL 16+, Docker, Git. Versions pinned
via `requirements.txt`, lockfiles, Docker images.

# 89. REPOSITORY STRUCTURE

```text
trustlens/
├── ARCHITECTURE.md
├── TECH_STACK.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── policies/
│   │   └── prompts/
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   └── types/
├── data/
│   └── demo_cases.json
└── docs/
```

# 90. MVP DEPENDENCY POLICY

Do NOT add a new dependency simply because it is convenient. Ask: Is it necessary?
Does Python/TypeScript already provide it? Does an existing dependency solve it?
Does it introduce setup complexity? Does it improve reliability? Is it stable
enough? If no → do not add it.

# 91. PROHIBITED MVP COMPLEXITY

Kubernetes, Kafka, Elasticsearch, MongoDB, Redis, multiple vector databases,
multiple LLM frameworks, multiple LLM providers, custom model training,
fine-tuning, complex agent orchestration, service mesh, event-driven
microservices — unless explicitly required later.

# 92. PRODUCTION EVOLUTION

```text
API Gateway → Auth/SSO → TrustLens API
   → {LLM Gateway, Evaluation Engine, Security}
   → {Enterprise LLM, Knowledge/RAG, PII/DLP}
   → PostgreSQL → Observability
```

# 93. TCS ENTERPRISE TECHNOLOGY EVOLUTION

Future: Entra ID, Azure OpenAI, Azure AI, AWS, GCP, enterprise API gateways,
ServiceNow, Salesforce, SAP, SharePoint, Confluence, enterprise data lakes, SIEM.
TrustLens exposes clean REST APIs for integration regardless of ecosystem.

# 94. API-FIRST DESIGN

- **Mode 1:** Direct web application. `User → TrustLens UI`
- **Mode 2:** Enterprise integration. `Existing Enterprise AI → TrustLens API →
  Reliability Result`

Mode 2 is strategically important for TCS.

# 95. EXTERNAL ENTERPRISE INTEGRATION

```text
POST /api/v1/evaluate
{ "question": "...", "answer": "...", "evidence": ["..."] }
```

Evaluates an answer generated by another AI system. TrustLens does not have to
generate the answer itself.

# 96. TWO MODES OF OPERATION

- **Mode A — Generate + Evaluate:** `Question → TrustLens LLM → Evaluate` (demo).
- **Mode B — Evaluate Existing AI Output:** `Enterprise AI → TrustLens →
  Reliability` (TCS enterprise integration, strategic differentiator).

# 97. VERSIONED API

`/api/v1/answer`, `/api/v1/evaluate`, `/api/v1/reviews`, `/api/v1/audit`.

# 98. HEALTH CHECK

```text
GET /api/v1/health
→ { "status": "healthy", "database": "healthy", "llm": "available" }
```

Do not expose sensitive infrastructure details.

# 99. FINAL TECHNOLOGY DECISION TABLE

| Layer | Technology | Required |
|---|---|---|
| Frontend | Next.js | YES |
| Frontend Language | TypeScript | YES |
| UI | Tailwind CSS | YES |
| Backend | Python | YES |
| API | FastAPI | YES |
| Validation | Pydantic | YES |
| ORM | SQLAlchemy | YES |
| Database | PostgreSQL | YES |
| Migrations | Alembic | YES |
| LLM | Configurable provider | YES |
| LLM SDK | Official provider SDK / OpenAI-compatible | YES |
| Embeddings | sentence-transformers / provider embeddings | YES |
| Semantic Similarity | Cosine similarity | YES |
| Perplexity | Provider logprobs where available | YES |
| PII | Regex + optional Presidio | YES |
| Authentication | JWT | YES |
| Password Hashing | Argon2 / bcrypt | YES |
| Testing | pytest | YES |
| HTTP Server | Uvicorn | YES |
| Containerization | Docker | YES |
| Orchestration | Docker Compose | YES |
| Vector DB | pgvector | OPTIONAL |
| RAG | Custom / lightweight | OPTIONAL |
| Redis | Redis | FUTURE |
| Kafka | Kafka | FUTURE |
| Kubernetes | Kubernetes | FUTURE |
| Observability | OpenTelemetry | FUTURE |
| RAG Evaluation | RAGAS | FUTURE |
| LLM Observability | Langfuse / Phoenix / TruLens | FUTURE |

# 100. FINAL STACK

```text
                    TRUSTLENS
        ┌──────────────┴──────────────┐
    FRONTEND                       BACKEND
    Next.js                        Python / FastAPI
    React                          Pydantic
    TypeScript                     SQLAlchemy
    Tailwind              ┌────────┼─────────┐
                         LLM   EVALUATION   PII
                          │     Embeddings  Regex
                          │     Semantic    Presidio*
                          │     Perplexity
                          │     Scoring
                          └────────┼─────────
                                   ▼
                              PostgreSQL → Alembic → Docker
```

\* Presidio is optional depending on setup reliability.

# 101. GOLDEN RULE

```text
RELIABILITY               >  COMPLEXITY
DETERMINISTIC CONTROL     >  UNNECESSARY AI
ENTERPRISE INTEGRABILITY  >  HACKATHON-ONLY IMPLEMENTATION
```

The architecture must be simple enough to build quickly, but structured enough to
evolve into a TCS enterprise service.

---

END OF TECH_STACK.md

---

## APPENDIX — Locked-in hackathon stack

**Frontend:** Next.js · React · TypeScript · Tailwind
**Backend:** Python 3.12+ · FastAPI · Pydantic · SQLAlchemy 2.x · Alembic
**AI:** one configurable LLM provider · official/OpenAI-compatible SDK ·
`sentence-transformers` for semantic similarity · perplexity via logprobs where
supported
**Security:** JWT + RBAC · Argon2/bcrypt · Regex + optional Presidio · no raw
secrets/PII in logs
**Data:** PostgreSQL · pgvector only if RAG is added
**DevOps:** Docker · Docker Compose · pytest · Ruff · ESLint/Prettier

No Kafka, Kubernetes, Redis, Elasticsearch, microservices, LangChain, or separate
vector DB for the MVP.
