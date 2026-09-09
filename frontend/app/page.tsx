"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { AnswerResponse, ReliabilityLabel } from "@/lib/types";

const LABEL_STYLES: Record<ReliabilityLabel, string> = {
  CERTAIN: "bg-green-100 text-green-800 border-green-300",
  UNCERTAIN: "bg-amber-100 text-amber-800 border-amber-300",
  NEEDS_VERIFICATION: "bg-red-100 text-red-800 border-red-300",
};

export default function Home() {
  const [question, setQuestion] = useState("Who invented Python?");
  const [answer, setAnswer] = useState(
    "Python was created by Guido van Rossum in 1991."
  );
  const [evidence, setEvidence] = useState(
    "Python was created by Guido van Rossum and first released in 1991."
  );
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.evaluateAnswer({
        question,
        answer,
        evidence: evidence.split("\n").map((s) => s.trim()).filter(Boolean),
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="space-y-6">
      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
        <label className="block text-sm font-medium">Question</label>
        <input
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <label className="block text-sm font-medium">Answer to evaluate</label>
        <textarea
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          rows={3}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
        />
        <label className="block text-sm font-medium">Evidence (one per line)</label>
        <textarea
          className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
          rows={3}
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
        />
        <button
          onClick={run}
          disabled={loading}
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Evaluating…" : "Evaluate"}
        </button>
      </section>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && (
        <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <span
              className={`rounded-full border px-3 py-1 text-sm font-semibold ${
                LABEL_STYLES[result.reliability.label]
              }`}
            >
              {result.reliability.label}
            </span>
            <span className="text-2xl font-bold">
              {result.reliability.final_score}
              <span className="text-sm font-normal text-slate-400">/100</span>
            </span>
          </div>

          <p className="text-sm text-slate-600">{result.explanation}</p>

          <div>
            <h3 className="mb-1 text-sm font-semibold">Why this label</h3>
            <ul className="list-disc pl-5 text-sm text-slate-600">
              {result.reliability.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="mb-1 text-sm font-semibold">Claims</h3>
            <ul className="space-y-1 text-sm">
              {result.claims.map((c, i) => (
                <li key={i} className="flex gap-2">
                  <span>{c.supported ? "✅" : c.contradicted ? "⚠️" : "❔"}</span>
                  <span>{c.text}</span>
                </li>
              ))}
            </ul>
          </div>

          <dl className="grid grid-cols-2 gap-2 text-sm">
            <Metric label="Evidence support" value={result.metrics.evidence_support} />
            <Metric label="Semantic support" value={result.metrics.semantic_support} />
            <Metric label="Answer relevance" value={result.metrics.answer_relevance} />
            <Metric label="Uncertainty" value={result.metrics.uncertainty} />
          </dl>

          {result.security.pii_detected && (
            <div className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800">
              PII detected and redacted before evaluation:{" "}
              {result.security.pii_findings
                .map((f) => `${f.type}×${f.count}`)
                .join(", ")}
            </div>
          )}

          <p className="text-xs text-slate-400">
            request {result.request_id}
            {result.review_required && " · queued for human review"}
          </p>
        </section>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-slate-50 p-2">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="font-mono">{(value * 100).toFixed(0)}%</dd>
    </div>
  );
}
