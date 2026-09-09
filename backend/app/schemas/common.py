from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import ReliabilityLabel


class PIIFinding(BaseModel):
    type: str = Field(examples=["PAN", "AADHAAR", "EMAIL"])
    count: int


class SourceRef(BaseModel):
    ordinal: int
    snippet: str
    title: str | None = None
    url: str | None = None


class SecurityBlock(BaseModel):
    pii_detected: bool
    pii_findings: list[PIIFinding] = []
    redaction_applied: bool
    redacted_fields: list[str] = []


class ClaimResult(BaseModel):
    text: str
    is_critical: bool
    supported: bool
    semantic_support: float = Field(ge=0.0, le=1.0)
    evidence_support: float = Field(ge=0.0, le=1.0)
    contradicted: bool
    best_evidence_ordinal: int | None = None
    support_source: str = "heuristic"  # "llm" | "heuristic"
    rationale: str | None = None


class MetricsBlock(BaseModel):
    semantic_support: float = Field(ge=0.0, le=1.0)
    evidence_support: float = Field(ge=0.0, le=1.0)
    answer_relevance: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    perplexity: float | None = None
    perplexity_available: bool = False
    evidence_count: int


class ReliabilityBlock(BaseModel):
    final_score: int = Field(ge=0, le=100)
    label: ReliabilityLabel
    reasons: list[str]
    weights: dict[str, float]
    thresholds: dict[str, int]
    evidence_score: float
    semantic_score: float
    uncertainty_score: float
    relevance_score: float


class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    version: str
