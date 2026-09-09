"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { ResultView } from "@/components/ResultView";
import { Pill } from "@/components/ui/Pill";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { REVIEW_STATUS_META } from "@/lib/labels";
import type { AnswerDetail } from "@/lib/types";

export default function AnswerDetailPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<AnswerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAnswer(params.id).then(setData).catch((e) => setError(e.message));
  }, [params.id]);

  return (
    <Shell>
      <Link
        href="/history"
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-ink-faint hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" /> History
      </Link>

      {error && <p className="text-sm text-[var(--alert)]">{error}</p>}
      {!data && !error && <CenteredSpinner />}

      {data && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
            <span className="font-mono">{data.request_id}</span>
            <span>· {relativeTime(data.created_at)}</span>
            <Pill tone="neutral">{data.mode === "ASK" ? "Asked" : data.mode === "GENERATE" ? "Generated" : "Evaluated"}</Pill>
            {data.review && (
              <Pill
                tone={
                  REVIEW_STATUS_META[data.review.status].tone === "neutral"
                    ? "neutral"
                    : REVIEW_STATUS_META[data.review.status].tone
                }
              >
                Review: {REVIEW_STATUS_META[data.review.status].text}
              </Pill>
            )}
          </div>

          <ResultView
            data={{
              question: data.question,
              answer: data.answer,
              sources: data.sources,
              claims: data.claims,
              metrics: data.metrics,
              reliability: data.reliability,
              explanation: data.explanation,
              requestId: data.request_id,
              source: data.source,
              model: data.model,
              effectiveLabel: data.effective_label,
              mode: data.mode,
            }}
          />

          {data.review?.decision_note && (
            <div className="mt-4 rounded-card border border-line bg-raised/40 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                Reviewer note
              </p>
              <p className="mt-1 text-sm text-ink-soft">{data.review.decision_note}</p>
            </div>
          )}
        </>
      )}
    </Shell>
  );
}
