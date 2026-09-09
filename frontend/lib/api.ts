// Centralized API client. No raw fetch() in components (TECH_STACK.md §50).
import type {
  AnswerDetail,
  AnswerResponse,
  AnswerSummary,
  AuditPage,
  ReliabilityLabel,
  ReviewDetail,
  ReviewQueueItem,
  ReviewStatus,
  Role,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const PREFIX = "/api/v1";
const TOKEN_KEY = "trustlens.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode */
  }
}

export class ApiError extends Error {
  status: number;
  requestId?: string;
  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${BASE}${PREFIX}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Cannot reach the TrustLens API.", 0);
  }

  const requestId = res.headers.get("X-Request-ID") ?? undefined;
  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      (body as { detail?: string }).detail || `${res.status} ${res.statusText}`,
      res.status,
      requestId,
    );
  }
  return body as T;
}

export interface AskPayload {
  question: string;
  include_explanation?: boolean;
}
export interface EvaluatePayload {
  question: string;
  answer: string;
  evidence: string[];
  model?: string;
  include_explanation?: boolean;
}
export interface GeneratePayload {
  question: string;
  source_snippets: string[];
  include_explanation?: boolean;
}
export interface DecisionPayload {
  status: ReviewStatus;
  decision_note?: string;
  override_label?: ReliabilityLabel | null;
}

export const api = {
  health: () =>
    request<{ status: string; database: string; llm: string; version: string }>(
      "/health",
    ),

  register: (email: string, password: string, role: Role = "USER") =>
    request<{ access_token: string; role: Role }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, role }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; role: Role }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ id: string; email: string; role: Role }>("/auth/me"),

  ask: (p: AskPayload) =>
    request<AnswerResponse>("/ask", { method: "POST", body: JSON.stringify(p) }),
  submitQuestion: (p: GeneratePayload) =>
    request<AnswerResponse>("/answer", { method: "POST", body: JSON.stringify(p) }),
  evaluateAnswer: (p: EvaluatePayload) =>
    request<AnswerResponse>("/evaluate", { method: "POST", body: JSON.stringify(p) }),

  listAnswers: (opts: { mine?: boolean; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (opts.mine) q.set("mine", "true");
    if (opts.limit) q.set("limit", String(opts.limit));
    return request<AnswerSummary[]>(`/answers?${q.toString()}`);
  },
  getAnswer: (id: string) => request<AnswerDetail>(`/answers/${id}`),

  getReviewQueue: (status?: ReviewStatus) =>
    request<ReviewQueueItem[]>(
      `/reviews${status ? `?status=${status}` : ""}`,
    ),
  getReview: (id: string) => request<ReviewDetail>(`/reviews/${id}`),
  submitReview: (id: string, payload: DecisionPayload) =>
    request<ReviewDetail>(`/reviews/${id}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getAuditLogs: (opts: { request_id?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (opts.request_id) q.set("request_id", opts.request_id);
    q.set("limit", String(opts.limit ?? 100));
    return request<AuditPage>(`/audit?${q.toString()}`);
  },
};
