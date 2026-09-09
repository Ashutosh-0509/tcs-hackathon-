"use client";

import { useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Field";
import { ResultView } from "@/components/ResultView";
import { api, ApiError } from "@/lib/api";
import type { AnswerResponse } from "@/lib/types";

const EXAMPLES = [
  "Who invented the light bulb?",
  "Did Einstein win the Nobel Prize for relativity?",
  "Is Pluto a planet?",
  "What year did the Berlin Wall fall?",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(q?: string) {
    const text = (q ?? question).trim();
    if (!text) return;
    if (q) setQuestion(q);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.ask({ question: text }));
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.message}${e.requestId ? ` (${e.requestId})` : ""}`
          : "Something went wrong.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Shell>
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Ask a question</h1>
        <p className="mt-1 text-sm text-ink-soft">
          The AI answers, then TrustLens pulls real sources — Wikipedia, Wikidata
          and Wikinews — and checks the answer against them, claim by claim, with a
          confidence score and links you can open.
        </p>
      </div>

      <Card>
        <CardBody className="space-y-3">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run();
            }}
            rows={3}
            placeholder="Ask anything factual…  (⌘/Ctrl + Enter to submit)"
            autoFocus
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-ink-faint">Try:</span>
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  onClick={() => run(q)}
                  disabled={loading}
                  className="rounded-full border border-line px-2.5 py-1 text-xs text-ink-soft hover:bg-raised disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
            <Button onClick={() => run()} loading={loading} disabled={!question.trim()}>
              Verify answer
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </div>
        </CardBody>
      </Card>

      {error && (
        <div className="mt-4 rounded-card border border-[var(--alert-line)] bg-[var(--alert-tint)] p-3 text-sm text-[var(--alert)]">
          {error}
        </div>
      )}

      {loading && (
        <div className="mt-10 flex flex-col items-center gap-3 text-sm text-ink-faint">
          <Search className="h-5 w-5 animate-pulse" />
          Answering · retrieving sources · checking each claim…
        </div>
      )}

      {result && (
        <div className="mt-6">
          <ResultView
            data={{
              question: result.question,
              answer: result.answer,
              sources: result.sources,
              claims: result.claims,
              metrics: result.metrics,
              reliability: result.reliability,
              security: result.security,
              explanation: result.explanation,
              reviewRequired: result.review_required,
              requestId: result.request_id,
              source: "TRUSTLENS_LLM",
              model: null,
              mode: "ASK",
            }}
          />
        </div>
      )}
    </Shell>
  );
}
