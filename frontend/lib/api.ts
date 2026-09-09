// Centralized API client. No raw fetch() elsewhere (TECH_STACK.md §50).
import type { AnswerResponse, ReviewQueueItem } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const PREFIX = "/api/v1";

let token: string | null = null;
export function setToken(t: string | null) {
  token = t;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${PREFIX}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface EvaluatePayload {
  question: string;
  answer: string;
  evidence: string[];
  model?: string;
}

export interface GeneratePayload {
  question: string;
  source_snippets: string[];
}

export const api = {
  health: () => request<{ status: string; database: string; llm: string }>("/health"),

  submitQuestion: (payload: GeneratePayload) =>
    request<AnswerResponse>("/answer", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  evaluateAnswer: (payload: EvaluatePayload) =>
    request<AnswerResponse>("/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getReviewQueue: () => request<ReviewQueueItem[]>("/reviews"),

  getReview: (id: string) => request<Record<string, unknown>>(`/reviews/${id}`),

  submitReview: (id: string, status: string, note?: string) =>
    request<Record<string, unknown>>(`/reviews/${id}`, {
      method: "POST",
      body: JSON.stringify({ status, decision_note: note }),
    }),

  getAuditLogs: () =>
    request<{ items: unknown[]; total: number }>("/audit"),
};
