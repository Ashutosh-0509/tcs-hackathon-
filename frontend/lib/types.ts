// Mirrors backend app/schemas. Keep in sync with the OpenAPI at /api/docs.

export type ReliabilityLabel = "CERTAIN" | "UNCERTAIN" | "NEEDS_VERIFICATION";

export interface ClaimResult {
  text: string;
  is_critical: boolean;
  supported: boolean;
  semantic_support: number;
  evidence_support: number;
  contradicted: boolean;
  best_evidence_ordinal: number | null;
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

export interface AnswerResponse {
  request_id: string;
  answer_id: string;
  question_id: string;
  answer: string;
  claims: ClaimResult[];
  metrics: MetricsBlock;
  reliability: ReliabilityBlock;
  security: SecurityBlock;
  explanation: string | null;
  review_required: boolean;
}

export interface ReviewQueueItem {
  review_id: string;
  answer_id: string;
  question_id: string;
  request_id: string;
  question: string;
  answer: string;
  label: ReliabilityLabel;
  final_score: number;
  status: "PENDING" | "APPROVED" | "REJECTED" | "ESCALATED";
  created_at: string;
}
