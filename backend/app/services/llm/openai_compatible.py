"""One concrete provider over an OpenAI-compatible Chat Completions API.

Works with OpenAI, Azure OpenAI (with base_url), and most local servers
(llama.cpp, vLLM, Ollama's OpenAI shim). Explicit timeout, bounded retry on
transient errors only (TECH_STACK.md §42, §80-81).
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
    ExtractedClaim,
    LLMProvider,
    LLMResult,
    ProviderCapabilities,
)

logger = logging.getLogger("trustlens.llm")

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


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

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_logprobs=True,
            supports_embeddings=False,
            supports_structured_output=True,
            supports_streaming=True,
        )

    # ---- HTTP ----
    def _chat(self, messages: list[dict], *, logprobs: bool = False, json_mode: bool = False) -> dict:
        payload: dict = {"model": self._model, "messages": messages, "temperature": 0}
        if logprobs:
            payload["logprobs"] = True
        if json_mode:
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
                    raise httpx.HTTPStatusError(
                        "transient", request=resp.request, response=resp
                    )
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
        text = (choice["message"]["content"] or "").strip()
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

    def generate_explanation(
        self, label: str, score: int, reasons: list[str], claim_summary: str
    ) -> str:
        prompt = load_prompt("explanation").format(
            label=label, score=score, reasons="; ".join(reasons), claim_summary=claim_summary
        )
        try:
            data = self._chat([{"role": "user", "content": prompt}])
            return (data["choices"][0]["message"]["content"] or "").strip()
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
                ExtractedClaim(text=str(item["text"]).strip(), is_critical=bool(item.get("is_critical")))
            )
        elif isinstance(item, str) and item.strip():
            out.append(ExtractedClaim(text=item.strip()))
    return out


def logprob_to_perplexity(avg_logprob: float) -> float:
    return math.exp(-avg_logprob)
