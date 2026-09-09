"""Deterministic offline provider.

Used when LLM_PROVIDER=stub or no API key is configured, so the demo and the test
suite run with zero external dependencies. Output is obviously synthetic and this
provider reports supports_logprobs = False (it never fabricates perplexity).

Its `judge_claims` is a transparent lexical heuristic — content-word coverage plus
a negation check — so the reliability policy still gets a real SUPPORTED /
CONTRADICTED / NOT_STATED signal offline, just a coarse one.
"""
from __future__ import annotations

import re

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

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+")
_NO_ANSWER = "The provided sources do not answer this question."

_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "and", "or", "is",
    "are", "was", "were", "be", "been", "it", "its", "this", "that", "these", "those",
    "as", "with", "from", "which", "who", "whom", "what", "when", "where", "how",
    "has", "have", "had", "will", "would", "can", "could", "may", "might", "do",
    "does", "did", "not", "no",
}
_NEGATIONS = {
    "not", "no", "never", "none", "cannot", "cant", "didnt", "doesnt", "isnt",
    "wasnt", "arent", "werent", "without", "nor", "neither", "false", "incorrect",
    "rejected", "denied", "refused",
}


def _content(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 1}


def _all_tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class StubProvider(LLMProvider):
    name = "stub"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_logprobs=False,
            supports_embeddings=False,
            supports_structured_output=True,
            supports_streaming=False,
        )

    def generate_answer(self, question: str, sources: list[str]) -> LLMResult:
        joined = " ".join(s.strip() for s in sources if s.strip())
        if not joined:
            text = _NO_ANSWER
        else:
            q_words = {w.lower() for w in re.findall(r"\w+", question) if len(w) > 2}
            best = ""
            best_overlap = -1
            for sent in _SENT_SPLIT.split(joined):
                overlap = len({w.lower() for w in re.findall(r"\w+", sent)} & q_words)
                if overlap > best_overlap:
                    best_overlap, best = overlap, sent
            text = best.strip() or joined[:300]
        return LLMResult(text=text, model="stub-extractive-v1", logprob_available=False)

    def answer_question(self, question: str) -> LLMResult:
        # Offline: no real knowledge. Return a clearly-hedged placeholder so the
        # Ask flow still exercises retrieval + verification end to end.
        return LLMResult(
            text=(
                f"(offline stub) A direct answer to “{question.strip().rstrip('?')}” "
                "is not available without a configured language model."
            ),
            model="stub-extractive-v1",
            logprob_available=False,
        )

    def extract_claims(self, question: str, answer: str) -> ClaimExtraction:
        if answer.strip() == _NO_ANSWER or not answer.strip():
            return ClaimExtraction(claims=[], model="stub-extractive-v1")
        sentences = [s.strip() for s in _SENT_SPLIT.split(answer) if len(s.strip()) > 3]
        if not sentences:
            sentences = [answer.strip()]
        claims = [
            ExtractedClaim(text=s, is_critical=(i == 0)) for i, s in enumerate(sentences)
        ]
        return ClaimExtraction(claims=claims, model="stub-extractive-v1")

    def judge_claims(self, claims: list[str], evidence: list[str]) -> ClaimJudgementResult:
        if not claims or not evidence:
            return ClaimJudgementResult(judgements=[], model="stub-nli-v1", available=False)
        ev_content = [_content(e) for e in evidence]
        ev_tokens = [_all_tokens(e) for e in evidence]
        judgements: list[ClaimJudgement] = []
        for claim in claims:
            c_content = _content(claim)
            c_tokens = _all_tokens(claim)
            c_neg = bool(c_tokens & _NEGATIONS)
            best_j, best_cov = 0, 0.0
            for j, ecov in enumerate(ev_content):
                cov = (len(c_content & ecov) / len(c_content)) if c_content else 0.0
                if cov > best_cov:
                    best_cov, best_j = cov, j
            shared = c_content & ev_content[best_j]
            e_neg = bool(ev_tokens[best_j] & _NEGATIONS)
            if len(shared) >= 2 and c_neg != e_neg:
                verdict = Entailment.CONTRADICTED
            elif best_cov >= 0.6:
                verdict = Entailment.SUPPORTED
            else:
                verdict = Entailment.NOT_STATED
            judgements.append(ClaimJudgement(verdict=verdict, evidence_ordinal=best_j))
        return ClaimJudgementResult(
            judgements=judgements, model="stub-nli-v1", available=True
        )

    def generate_explanation(
        self, label: str, score: int, reasons: list[str], claim_summary: str
    ) -> str:
        reason_txt = "; ".join(reasons) if reasons else "no specific flags"
        return (
            f"This answer was labelled {label} with a reliability score of {score}/100. "
            f"Basis: {reason_txt}. "
            f"Claim support summary: {claim_summary or 'n/a'}. "
            f"(Explanation generated by the offline stub provider.)"
        )
