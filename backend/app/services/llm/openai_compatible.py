"""One concrete provider over an OpenAI-compatible Chat Completions API.

Works with OpenAI, Azure OpenAI, xAI Grok (base_url https://api.x.ai/v1),
Google Gemini's OpenAI shim, Together, Groq, and local servers (llama.cpp, vLLM,
Ollama). Explicit timeout, bounded retry on transient errors only
(TECH_STACK.md §42, §80-81).

Optional request parameters (`logprobs`, `response_format`) are probed at runtime:
if the endpoint rejects one with a 4xx we drop it for the rest of the session and
carry on. So an endpoint without log-probs simply reports
`perplexity_available: false` — it never breaks the pipeline (TECH_STACK.md §22, §84).
"""
from __future__ import annotations

import json
import logging
import math
import time

import httpx

from app.core.errors import LLMUnavailableError
from app.prompts import load_prompt
from app.services.llm.base import (
    ClaimExtraction,
    ClaimJudgement,
    ClaimJudgementResult,
    Entailment,
    ExtractedClaim,
    LLMProvider,
    LLMResult,
    ProviderCapabilities,
)

logger = logging.getLogger("trustlens.llm")

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}

# some models emit exotic whitespace (no-break / narrow-no-break / thin / hair
# space, zero-width space, BOM). Normalise everything to a plain space.
_ODD_WS = str.maketrans({
    " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", "​": "", "﻿": "",
})


def _clean(text: str) -> str:
    return text.translate(_ODD_WS).strip()


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        # optimistic; flipped off if the endpoint 4xx-rejects the param
        self._logprobs_ok = True
        self._json_mode_ok = True

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_logprobs=self._logprobs_ok,
            supports_embeddings=False,
            supports_structured_output=self._json_mode_ok,
            supports_streaming=True,
        )

    # ---- HTTP ----
    def _chat(self, messages: list[dict], *, logprobs: bool = False, json_mode: bool = False) -> dict:
        want_logprobs = logprobs and self._logprobs_ok
        want_json = json_mode and self._json_mode_ok

        payload: dict = {"model": self._model, "messages": messages, "temperature": 0}
        if want_logprobs:
            payload["logprobs"] = True
        if want_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(
                        f"{self._base_url}/chat/completions", json=payload, headers=headers
                    )
                if resp.status_code in _TRANSIENT_STATUS:
                    raise httpx.HTTPStatusError("transient", request=resp.request, response=resp)

                # An unsupported optional parameter → drop it and try once more.
                if resp.status_code in (400, 422) and (want_logprobs or want_json):
                    body = resp.text.lower()
                    dropped = False
                    if want_logprobs and "logprob" in body:
                        self._logprobs_ok = False
                        want_logprobs = False
                        payload.pop("logprobs", None)
                        dropped = True
                    if want_json and ("response_format" in body or "json_object" in body):
                        self._json_mode_ok = False
                        want_json = False
                        payload.pop("response_format", None)
                        dropped = True
                    if dropped:
                        logger.info("endpoint rejected an optional param; retrying without it")
                        continue

                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                # Do not retry non-transient client errors (auth, bad request).
                if status is not None and status not in _TRANSIENT_STATUS:
                    break
                if attempt < self._max_retries:
                    time.sleep(0.5 * (attempt + 1))
        logger.warning("LLM call failed after retries: %s", last_exc)
        raise LLMUnavailableError(f"LLM provider unavailable: {last_exc}")

    # ---- tasks ----
    def generate_answer(self, question: str, sources: list[str]) -> LLMResult:
        sources_block = "\n".join(f"- {s}" for s in sources) or "(no sources provided)"
        prompt = load_prompt("answer").format(question=question, sources=sources_block)
        data = self._chat([{"role": "user", "content": prompt}], logprobs=True)
        choice = data["choices"][0]
        text = _clean(choice["message"]["content"] or "")
        avg_lp, available = _mean_logprob(choice)
        return LLMResult(
            text=text,
            model=data.get("model", self._model),
            avg_logprob=avg_lp,
            logprob_available=available,
        )

    def extract_claims(self, question: str, answer: str) -> ClaimExtraction:
        prompt = load_prompt("claim_extraction").format(question=question, answer=answer)
        data = self._chat([{"role": "user", "content": prompt}], json_mode=True)
        raw = data["choices"][0]["message"]["content"] or "{}"
        claims = _parse_claims(raw)
        return ClaimExtraction(claims=claims, model=data.get("model", self._model))

    def judge_claims(self, claims: list[str], evidence: list[str]) -> ClaimJudgementResult:
        if not claims or not evidence:
            return ClaimJudgementResult(judgements=[], model=self._model, available=False)
        ev_block = "\n".join(f"[{i + 1}] {e}" for i, e in enumerate(evidence))
        cl_block = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
        prompt = load_prompt("entailment").format(evidence=ev_block, claims=cl_block)
        try:
            data = self._chat([{"role": "user", "content": prompt}], json_mode=True)
        except LLMUnavailableError:
            return ClaimJudgementResult(judgements=[], model=self._model, available=False)
        raw = data["choices"][0]["message"]["content"] or "{}"
        by_index = _parse_judgements(raw)
        judgements: list[ClaimJudgement] = []
        for i in range(len(claims)):
            j = by_index.get(i + 1)
            if j is None:
                judgements.append(ClaimJudgement(verdict=Entailment.NOT_STATED))
            else:
                judgements.append(j)
        return ClaimJudgementResult(
            judgements=judgements, model=data.get("model", self._model), available=True
        )

    def generate_explanation(
        self, label: str, score: int, reasons: list[str], claim_summary: str
    ) -> str:
        prompt = load_prompt("explanation").format(
            label=label, score=score, reasons="; ".join(reasons), claim_summary=claim_summary
        )
        try:
            data = self._chat([{"role": "user", "content": prompt}])
            return _clean(data["choices"][0]["message"]["content"] or "")
        except LLMUnavailableError:
            return f"Answer labelled {label} ({score}/100). Reasons: {'; '.join(reasons)}."

    def health(self) -> str:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            return "available" if r.status_code < 500 else "degraded"
        except httpx.HTTPError:
            return "unavailable"


def _mean_logprob(choice: dict) -> tuple[float | None, bool]:
    lp = choice.get("logprobs")
    if not lp or not lp.get("content"):
        return None, False
    values = [tok.get("logprob") for tok in lp["content"] if tok.get("logprob") is not None]
    if not values:
        return None, False
    return sum(values) / len(values), True


def _parse_claims(raw: str) -> list[ExtractedClaim]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        # last-resort: strip markdown fences
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("could not parse claim JSON from LLM")
            return []
    out: list[ExtractedClaim] = []
    for item in obj.get("claims", []):
        if isinstance(item, dict) and item.get("text"):
            out.append(
                ExtractedClaim(text=_clean(str(item["text"])), is_critical=bool(item.get("is_critical")))
            )
        elif isinstance(item, str) and item.strip():
            out.append(ExtractedClaim(text=_clean(item)))
    return out


def _parse_judgements(raw: str) -> dict[int, ClaimJudgement]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("could not parse entailment JSON from LLM")
            return {}
    out: dict[int, ClaimJudgement] = {}
    for item in obj.get("judgements", []):
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item["index"])
            verdict = Entailment(str(item["verdict"]).strip().upper())
        except (KeyError, ValueError):
            continue
        ev = item.get("evidence_index")
        out[idx] = ClaimJudgement(
            verdict=verdict,
            evidence_ordinal=(int(ev) - 1) if isinstance(ev, int) else None,
            rationale=str(item.get("rationale", ""))[:300],
        )
    return out


def logprob_to_perplexity(avg_logprob: float) -> float:
    return math.exp(-avg_logprob)
