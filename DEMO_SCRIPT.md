# TrustLens — Demo Script (~4 minutes)

> The product is one loop:
> **Question → AI Answer → Claims → Evidence → Reliability Score → Label → Explanation → Human Review → Audit**

## 0. Setup (before the room)

```bash
cp .env.example .env          # optionally set LLM_* for a real model; stub works offline
docker compose up --build     # seeds demo users + demo cases automatically
```

- App: http://localhost:3000
- API docs: http://localhost:8000/api/docs

Demo accounts (password `trustlens`): `user@trustlens.dev`, `editor@trustlens.dev`, `admin@trustlens.dev`.

---

## 1. The problem (15s)

"Enterprises can't ship AI answers they can't trust. TrustLens is a reliability
layer that sits in front of any AI system and tells you *how much to trust each
answer* — with evidence, a score, and a human review trail."

## 2. Analyze — the happy path (45s)

**Analyze** tab → sample **“Well supported”** → *Evaluate*.

- Point at the **gauge → 92, CERTAIN**.
- **Claims**: one atomic claim, ✅ supported — expand it to show the exact matched
  evidence snippet.
- **Signal breakdown**: evidence 50%, semantic 25%, confidence 15%, relevance 10% —
  "these weights are fixed policy, the LLM never touches them."

## 3. Contradiction — the safety override (45s)

Sample **“Contradicted”** → *Evaluate*.

- **NEEDS_VERIFICATION**, score is low and *irrelevant*: "even if the number were
  high, a contradicted critical claim can never be CERTAIN. This is a hard rule."
- Read the **Recommended action** panel: "Do not use as-is. Route to a human."

## 4. No evidence — fail-safe (20s)

Sample **“No evidence”** → *Evaluate*.

- **NEEDS_VERIFICATION**: "No evidence means we can't verify, so we fail safe.
  TrustLens will never bluff a CERTAIN."

## 5. PII redaction (20s)

Type an answer with `PAN ABCPD1234E` and an email in the evidence → *Evaluate*.

- **Security** line: identifiers were redacted *before* the model and *before*
  storage. Show the answer text now reads `[REDACTED_PAN]`.

## 6. Human review + label override (60s)

Sign in as `editor@trustlens.dev` → **Review** tab.

- The uncertain / needs-verification answers are already queued.
- Open one → inspect claims and evidence → write a note →
  **override the label** (e.g. force NEEDS_VERIFICATION) → **Reject**.
- "The machine score is immutable — we record what the human decided on top of it."

## 7. Audit (20s)

**Audit** tab.

- Every generation, evaluation, and review decision, each stamped with the same
  **request ID** (`TRUST-2026-…`) that threads through logs and LLM calls.
- Filter by a request ID to show the full lifecycle of one answer.

## 8. Close (15s)

"Same API works two ways: TrustLens can generate the answer, or score an answer
your existing enterprise AI already produced — `POST /api/v1/evaluate`. That
second mode is how this drops into a TCS client without replacing anything."

---

## If asked

- **Perplexity?** Only shown when the provider returns log-probabilities; otherwise
  `null` — we never fabricate it, the weight is redistributed.
- **Embeddings?** `sentence-transformers` (MiniLM); deterministic hashed fallback
  if the model isn't available, clearly logged.
- **Why no RAG / vector DB?** Out of scope for the MVP — the reliability loop *is*
  the product. pgvector is the documented next step.
