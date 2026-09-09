"use client";

import { useState } from "react";
import { Check, ChevronDown, CircleAlert, CircleHelp } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { pct } from "@/lib/format";
import type { ClaimResult } from "@/lib/types";

function statusOf(c: ClaimResult) {
  if (c.contradicted) return { Icon: CircleAlert, tone: "text-[var(--alert)]", word: "Contradicted" };
  if (c.supported) return { Icon: Check, tone: "text-[var(--certain)]", word: "Supported" };
  return { Icon: CircleHelp, tone: "text-[var(--caution)]", word: "Not in evidence" };
}

export function ClaimsPanel({
  claims,
  evidence,
}: {
  claims: ClaimResult[];
  evidence?: string[];
}) {
  const [open, setOpen] = useState<number | null>(0);
  const supported = claims.filter((c) => c.supported).length;
  const checkedByLlm = claims.some((c) => c.support_source === "llm");

  return (
    <Card>
      <CardHeader
        title="Claims"
        hint={
          claims.length
            ? `${supported} of ${claims.length} verified against evidence`
            : "No atomic claims were extracted"
        }
        right={
          claims.length ? (
            <span className="text-2xs text-ink-faint">
              {checkedByLlm ? "checked by model" : "lexical check"}
            </span>
          ) : undefined
        }
      />
      <ul className="divide-y divide-line">
        {claims.map((c, i) => {
          const s = statusOf(c);
          const isOpen = open === i;
          const evIdx = c.best_evidence_ordinal;
          const ev = evIdx != null ? evidence?.[evIdx] : undefined;
          return (
            <li key={i}>
              <button
                onClick={() => setOpen(isOpen ? null : i)}
                className="flex w-full items-start gap-3 px-5 py-3 text-left hover:bg-raised/60"
              >
                <s.Icon className={cn("mt-0.5 h-4 w-4 shrink-0", s.tone)} />
                <span className="flex-1 text-sm leading-relaxed">
                  {c.text}
                  {c.is_critical && (
                    <span className="ml-2 align-middle text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                      critical
                    </span>
                  )}
                </span>
                {evIdx != null && (
                  <span className="mt-0.5 shrink-0 rounded border border-line px-1 font-mono text-2xs text-ink-faint">
                    E{evIdx + 1}
                  </span>
                )}
                <ChevronDown
                  className={cn(
                    "mt-0.5 h-4 w-4 shrink-0 text-ink-faint transition-transform",
                    isOpen && "rotate-180",
                  )}
                />
              </button>
              {isOpen && (
                <div className="animate-fade-up space-y-2 bg-raised/40 px-5 pb-4 pt-1 text-xs">
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-ink-soft">
                    <span>
                      Verdict: <span className={s.tone}>{s.word}</span>
                    </span>
                    <span>Similarity {pct(c.semantic_support)}</span>
                  </div>
                  {c.rationale && (
                    <p className="text-ink-soft">
                      <span className="text-ink-faint">Why: </span>
                      {c.rationale}
                    </p>
                  )}
                  {ev ? (
                    <p className="rounded-control border border-line bg-surface p-2.5 leading-relaxed text-ink-soft">
                      <span className="mr-1 font-mono text-2xs text-ink-faint">
                        Source E{(evIdx ?? 0) + 1}
                      </span>
                      {ev}
                    </p>
                  ) : (
                    <p className="text-ink-faint">No evidence snippet addresses this claim.</p>
                  )}
                </div>
              )}
            </li>
          );
        })}
        {claims.length === 0 && (
          <li className="px-5 py-4 text-sm text-ink-faint">
            The model produced no verifiable factual claims.
          </li>
        )}
      </ul>
    </Card>
  );
}
