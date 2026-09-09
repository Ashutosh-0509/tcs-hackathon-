"use client";

import { useState } from "react";
import { Check, ChevronDown, CircleAlert, CircleHelp, ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { pct } from "@/lib/format";
import type { ClaimResult, SourceRef } from "@/lib/types";

function statusOf(c: ClaimResult) {
  if (c.contradicted) return { Icon: CircleAlert, tone: "text-[var(--alert)]", word: "Contradicted by a source" };
  if (c.supported) return { Icon: Check, tone: "text-[var(--certain)]", word: "Backed by a source" };
  return { Icon: CircleHelp, tone: "text-[var(--caution)]", word: "No source confirms this" };
}

export function ClaimsPanel({
  claims,
  sources,
}: {
  claims: ClaimResult[];
  sources?: SourceRef[];
}) {
  const [open, setOpen] = useState<number | null>(0);
  const supported = claims.filter((c) => c.supported).length;
  const checkedByLlm = claims.some((c) => c.support_source === "llm");

  return (
    <Card>
      <CardHeader
        title="Claim check"
        hint={
          claims.length
            ? `${supported} of ${claims.length} claims backed by a source`
            : "No atomic claims were extracted"
        }
        right={
          claims.length ? (
            <span className="text-2xs text-ink-faint">
              {checkedByLlm ? "verified by model" : "lexical check"}
            </span>
          ) : undefined
        }
      />
      <ul className="divide-y divide-line">
        {claims.map((c, i) => {
          const s = statusOf(c);
          const isOpen = open === i;
          const src = c.best_evidence_ordinal != null ? sources?.[c.best_evidence_ordinal] : undefined;
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
                      key claim
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
                  <p>
                    <span className={cn("font-medium", s.tone)}>{s.word}.</span>{" "}
                    {c.rationale && <span className="text-ink-soft">{c.rationale}</span>}
                  </p>
                  {src ? (
                    <div className="rounded-control border border-line bg-surface p-2.5">
                      {src.url ? (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 font-medium text-ink hover:underline"
                        >
                          {src.title || src.url}
                          <ExternalLink className="h-3 w-3 text-ink-faint" />
                        </a>
                      ) : (
                        <span className="font-mono text-2xs text-ink-faint">
                          E{(c.best_evidence_ordinal ?? 0) + 1}
                        </span>
                      )}
                      <p className="mt-1 leading-relaxed text-ink-soft">{src.snippet}</p>
                    </div>
                  ) : (
                    <p className="text-ink-faint">No source addresses this claim.</p>
                  )}
                  <p className="text-ink-faint">Semantic similarity to nearest source: {pct(c.semantic_support)}</p>
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
