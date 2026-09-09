import { ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import type { ClaimResult, SourceRef } from "@/lib/types";

export function EvidencePanel({
  sources,
  claims,
  retrieved,
}: {
  sources: SourceRef[];
  claims?: ClaimResult[];
  /** true = TrustLens fetched these; false = user supplied them */
  retrieved?: boolean;
}) {
  const citing = (ordinal: number) =>
    (claims ?? [])
      .map((c, i) => ({ c, i }))
      .filter(({ c }) => c.best_evidence_ordinal === ordinal);

  return (
    <Card>
      <CardHeader
        title="Sources"
        hint={
          sources.length
            ? retrieved
              ? `${sources.length} retrieved — the answer is checked against these`
              : `${sources.length} supplied`
            : undefined
        }
      />
      {sources.length === 0 ? (
        <div className="px-5 py-6 text-sm text-ink-faint">
          No sources were found to check this answer against, so TrustLens fails safe
          to <span className="font-medium text-ink-soft">Needs verification</span> —
          a confident-sounding answer with nothing behind it is exactly what this catches.
        </div>
      ) : (
        <ol className="divide-y divide-line">
          {sources.map((s, i) => {
            const cited = citing(s.ordinal ?? i);
            return (
              <li key={i} className="px-5 py-3 text-sm leading-relaxed">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 font-mono text-2xs text-ink-faint">
                    E{(s.ordinal ?? i) + 1}
                  </span>
                  <div className="flex-1">
                    {s.url ? (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-ink hover:underline"
                      >
                        {s.title || s.url}
                        <ExternalLink className="h-3 w-3 text-ink-faint" />
                      </a>
                    ) : (
                      s.title && <span className="font-medium">{s.title}</span>
                    )}
                    <p className="mt-0.5 text-ink-soft">{s.snippet}</p>
                    {cited.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {cited.map(({ c, i: ci }) => (
                          <span
                            key={ci}
                            className={cn(
                              "rounded-full border px-1.5 py-0.5 text-2xs",
                              c.contradicted
                                ? "border-[var(--alert-line)] text-[var(--alert)]"
                                : c.supported
                                ? "border-[var(--certain-line)] text-[var(--certain)]"
                                : "border-line text-ink-faint",
                            )}
                          >
                            claim {ci + 1}
                            {c.contradicted ? " ✕" : c.supported ? " ✓" : " ?"}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
