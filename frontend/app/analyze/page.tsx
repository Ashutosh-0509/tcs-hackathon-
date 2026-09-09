"use client";

import { useState } from "react";
import { ArrowRight, Sparkles, ScanSearch, Wand2 } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Label, Input, Textarea } from "@/components/ui/Field";
import { ResultView } from "@/components/ResultView";
import { cn } from "@/lib/cn";
import { api, ApiError } from "@/lib/api";
import type { AnswerResponse } from "@/lib/types";

type Mode = "evaluate" | "generate";

const SAMPLES = [
  {
    label: "Well supported",
    question: "Who created the Linux kernel?",
    answer: "The Linux kernel was created by Linus Torvalds in 1991.",
    evidence: "The Linux kernel was first released by Linus Torvalds in 1991.",
  },
  {
    label: "Contradicted",
    question: "Was the merger approved by regulators in March?",
    answer: "The merger was approved by regulators in March.",
    evidence:
      "Regulators did not approve the merger in March; the proposal was rejected over competition concerns.",
  },
  {
    label: "No evidence",
    question: "What was Acme Corp's market share in 2024?",
    answer: "Acme Corp held a 37% market share in 2024.",
    evidence: "",
  },
];

export default function AnalyzePage() {
  const [mode, setMode] = useState<Mode>("evaluate");
  const [question, setQuestion] = useState(SAMPLES[0].question);
  const [answer, setAnswer] = useState(SAMPLES[0].answer);
  const [evidence, setEvidence] = useState(SAMPLES[0].evidence);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const evidenceList = () =>
    evidence.split("\n").map((s) => s.trim()).filter(Boolean);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res =
        mode === "evaluate"
          ? await api.evaluateAnswer({ question, answer, evidence: evidenceList() })
          : await api.submitQuestion({ question, source_snippets: evidenceList() });
      setResult(res);
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

  function loadSample(s: (typeof SAMPLES)[number]) {
    setMode("evaluate");
    setQuestion(s.question);
    setAnswer(s.answer);
    setEvidence(s.evidence);
    setResult(null);
    setError(null);
  }

  return (
    <Shell>
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Analyze an answer</h1>
        <p className="mt-1 text-sm text-ink-soft">
          {mode === "evaluate"
            ? "Score an answer produced by any AI system against the evidence it should rely on."
            : "Let TrustLens generate an answer strictly from the sources, then score it."}
        </p>
      </div>

      <Card>
        <CardHeader
          title="Input"
          right={
            <div className="flex rounded-control border border-line p-0.5">
              {(["evaluate", "generate"] as Mode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-[7px] px-2.5 py-1 text-xs font-medium capitalize transition",
                    mode === m ? "bg-ink text-bg" : "text-ink-faint hover:text-ink",
                  )}
                >
                  {m === "evaluate" ? (
                    <ScanSearch className="h-3.5 w-3.5" />
                  ) : (
                    <Wand2 className="h-3.5 w-3.5" />
                  )}
                  {m}
                </button>
              ))}
            </div>
          }
        />
        <CardBody className="space-y-4">
          <div>
            <Label htmlFor="q">Question</Label>
            <Input
              id="q"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What do you want answered?"
            />
          </div>

          {mode === "evaluate" && (
            <div>
              <Label htmlFor="a">Answer to evaluate</Label>
              <Textarea
                id="a"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Paste the AI answer you want to check…"
              />
            </div>
          )}

          <div>
            <Label htmlFor="e">
              {mode === "evaluate" ? "Evidence" : "Sources"} — one snippet per line
            </Label>
            <Textarea
              id="e"
              value={evidence}
              onChange={(e) => setEvidence(e.target.value)}
              rows={4}
              placeholder="Paste the source text the answer should be grounded in…"
            />
            <p className="mt-1.5 text-xs text-ink-faint">
              PII (PAN, Aadhaar, email, phone, cards) is redacted before anything is sent to a model.
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex flex-wrap gap-1.5">
              {SAMPLES.map((s) => (
                <button
                  key={s.label}
                  onClick={() => loadSample(s)}
                  className="rounded-full border border-line px-2.5 py-1 text-xs text-ink-soft hover:bg-raised"
                >
                  {s.label}
                </button>
              ))}
            </div>
            <Button onClick={run} loading={loading} disabled={!question.trim()}>
              {mode === "evaluate" ? "Evaluate" : "Generate & evaluate"}
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
          <Sparkles className="h-5 w-5 animate-pulse" />
          Extracting claims · checking evidence · scoring…
        </div>
      )}

      {result && (
        <div className="mt-6">
          <ResultView
            data={{
              question,
              answer: result.answer,
              evidence: result.evidence,
              claims: result.claims,
              metrics: result.metrics,
              reliability: result.reliability,
              security: result.security,
              explanation: result.explanation,
              reviewRequired: result.review_required,
              requestId: result.request_id,
              source: mode === "generate" ? "TRUSTLENS_LLM" : "EXTERNAL",
            }}
          />
        </div>
      )}
    </Shell>
  );
}
