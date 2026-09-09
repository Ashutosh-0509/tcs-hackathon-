// Mirrors backend app/schemas. Keep in sync with OpenAPI at /api/docs.

export type ReliabilityLabel = "CERTAIN" | "UNCERTAIN" | "NEEDS_VERIFICATION";
export type ReviewStatus = "PENDING" | "APPROVED" | "REJECTED" | "ESCALATED";
export type QuestionMode = "ASK" | "GENERATE" | "EVALUATE";
export type AnswerSource = "TRUSTLENS_LLM" | "EXTERNAL";
export type Role = "USER" | "EDITOR" | "ADMIN";

export interface ClaimResult {
  text: string;
  is_critical: boolean;
  supported: boolean;
  semantic_support: number;
  evidence_support: number;
  contradicted: boolean;
  best_evidence_ordinal: number | null;
  support_source?: "llm" | "heuristic";
  rationale?: string | null;
}

export interface MetricsBlock {
  semantic_support: number;
  evidence_support: number;
  answer_relevance: number;
  uncertainty: number;
  perplexity: number | null;
  perplexity_available: boolean;
  evidence_count: number;
}

export interface ReliabilityBlock {
  final_score: number;
  label: ReliabilityLabel;
  reasons: string[];
  weights: Record<string, number>;
  thresholds: Record<string, number>;
  evidence_score: number;
  semantic_score: number;
  uncertainty_score: number;
  relevance_score: number;
}

export interface SecurityBlock {
  pii_detected: boolean;
  pii_findings: { type: string; count: number }[];
  redaction_applied: boolean;
  redacted_fields: string[];
}

export interface SourceRef {
  ordinal: number;
  snippet: string;
  title: string | null;
  url: string | null;
}

export interface AnswerResponse {
  request_id: string;
  answer_id: string;
  question_id: string;
  question: string;
  answer: string;
  mode: QuestionMode;
  evidence: string[];
  sources: SourceRef[];
  claims: ClaimResult[];
  metrics: MetricsBlock;
  reliability: ReliabilityBlock;
  security: SecurityBlock;
  explanation: string | null;
  review_required: boolean;
}

export interface AnswerSummary {
  answer_id: string;
  question_id: string;
  request_id: string;
  question: string;
  answer: string;
  mode: QuestionMode;
  source: AnswerSource;
  model: string | null;
  label: ReliabilityLabel;
  effective_label: ReliabilityLabel;
  final_score: number;
  review_status: ReviewStatus | null;
  created_at: string;
}

export interface ReviewSummary {
  review_id: string;
  status: ReviewStatus;
  overridden_label: ReliabilityLabel | null;
  decision_note: string | null;
  decided_at: string | null;
}

export interface AnswerDetail extends AnswerSummary {
  claims: ClaimResult[];
  metrics: MetricsBlock;
  reliability: ReliabilityBlock;
  evidence: string[];
  sources: SourceRef[];
  explanation: string | null;
  review: ReviewSummary | null;
}

export interface ReviewQueueItem {
  review_id: string;
  answer_id: string;
  question_id: string;
  request_id: string;
  question: string;
  answer: string;
  label: ReliabilityLabel;
  effective_label: ReliabilityLabel;
  overridden_label: ReliabilityLabel | null;
  final_score: number;
  status: ReviewStatus;
  created_at: string;
}

export interface ReviewDetail extends ReviewQueueItem {
  reasons: string[];
  claims: ClaimResult[];
  evidence: string[];
  sources: SourceRef[];
  explanation: string | null;
  decision_note: string | null;
  reviewed_by: string | null;
  decided_at: string | null;
}

export interface AuditEntry {
  id: string;
  request_id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}
