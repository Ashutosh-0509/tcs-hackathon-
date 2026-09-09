"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { Card } from "@/components/ui/Card";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { ReliabilityBadge } from "@/components/ReliabilityBadge";
import { Pill } from "@/components/ui/Pill";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";
import { REVIEW_STATUS_META } from "@/lib/labels";
import type { AnswerSummary } from "@/lib/types";

export default function HistoryPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<AnswerSummary[] | null>(null);
  const [mine, setMine] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    setItems(null);
    api
      .listAnswers({ mine: mine && !!user, limit: 50 })
      .then(setItems)
      .catch((e) => setError(e.message));
  }, [mine, user, authLoading]);

  return (
    <Shell maxWidth="max-w-4xl">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">History</h1>
          <p className="mt-1 text-sm text-ink-soft">Every analysis is persisted with its score and audit trail.</p>
        </div>
        {user && (
          <div className="flex rounded-control border border-line p-0.5 text-xs">
            {[
              { k: true, label: "Mine" },
              { k: false, label: "All" },
            ].map((o) => (
              <button
                key={String(o.k)}
                onClick={() => setMine(o.k)}
                className={`rounded-[7px] px-2.5 py-1 font-medium ${
                  mine === o.k ? "bg-ink text-bg" : "text-ink-faint"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-sm text-[var(--alert)]">{error}</p>}
      {!items && !error && <CenteredSpinner />}

      {items && items.length === 0 && (
        <Card className="px-5 py-16 text-center text-sm text-ink-faint">
          Nothing yet. Run an analysis and it will show up here.
        </Card>
      )}

      <div className="space-y-2">
        {items?.map((a) => {
          const rs = a.review_status ? REVIEW_STATUS_META[a.review_status] : null;
          return (
            <Link key={a.answer_id} href={`/history/${a.answer_id}`}>
              <Card className="group px-4 py-3 transition hover:border-ink/20 hover:shadow-pop">
                <div className="flex items-center justify-between gap-3">
                  <span className="line-clamp-1 text-sm font-medium">{a.question}</span>
                  <ArrowUpRight className="h-4 w-4 shrink-0 text-ink-faint opacity-0 transition group-hover:opacity-100" />
                </div>
                <p className="mt-1 line-clamp-1 text-xs text-ink-faint">{a.answer}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <ReliabilityBadge
                    label={a.effective_label}
                    size="sm"
                    overridden={a.effective_label !== a.label}
                  />
                  <span className="tnum text-2xs text-ink-faint">{a.final_score}/100</span>
                  <Pill tone="neutral">{a.mode === "GENERATE" ? "Generated" : "Evaluated"}</Pill>
                  {rs && <Pill tone={rs.tone === "neutral" ? "neutral" : rs.tone}>{rs.text}</Pill>}
                  <span className="ml-auto text-2xs text-ink-faint">{relativeTime(a.created_at)}</span>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </Shell>
  );
}
