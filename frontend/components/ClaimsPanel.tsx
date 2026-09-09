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
  return { Icon: CircleHelp, tone: "text-[var(--caution)]", word: "Unsupported" };
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

  return (
    <Card>
      <CardHeader
        title="Claims"
        hint={
          claims.length
            ? `${supported} of ${claims.length} supported by evidence`
            : "No atomic claims were extracted"
        }
      />
      <ul className="divide-y divide-line">
        {claims.map((c, i) => {
          const s = statusOf(c);
          const isOpen = open === i;
          const ev =
            c.best_evidence_ordinal != null ? evidence?.[c.best_evidence_ordinal] : undefined;
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
                <ChevronDown
                  className={cn(
                    "mt-0.5 h-4 w-4 shrink-0 text-ink-faint transition-transform",
                    isOpen && "rotate-180",
                  )}
                />
              </button>
              {isOpen && (
                <div className="animate-fade-up space-y-2 bg-raised/40 px-5 pb-4 pt-1 text-xs">
                  <div className="flex gap-4 text-ink-soft">
                    <span>Status: <span className={s.tone}>{s.word}</span></span>
                    <span>Semantic {pct(c.semantic_support)}</span>
                    <span>Evidence {pct(c.evidence_support)}</span>
                  </div>
                  {ev ? (
                    <p className="rounded-control border border-line bg-surface p-2.5 leading-relaxed text-ink-soft">
                      <span className="mr-1 font-mono text-2xs text-ink-faint">
                        E{(c.best_evidence_ordinal ?? 0) + 1}
                      </span>
                      {ev}
                    </p>
                  ) : (
                    <p className="text-ink-faint">No matching evidence snippet.</p>
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
