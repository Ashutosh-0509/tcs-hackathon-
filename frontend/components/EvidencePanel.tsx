import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import type { ClaimResult } from "@/lib/types";

export function EvidencePanel({
  evidence,
  claims,
}: {
  evidence: string[];
  claims?: ClaimResult[];
}) {
  const citing = (ordinal: number) =>
    (claims ?? [])
      .map((c, i) => ({ c, i }))
      .filter(({ c }) => c.best_evidence_ordinal === ordinal);

  return (
    <Card>
      <CardHeader
        title="Evidence"
        hint={
          evidence.length
            ? `${evidence.length} source snippet${evidence.length > 1 ? "s" : ""} — this is what claims are checked against`
            : undefined
        }
      />
      {evidence.length === 0 ? (
        <div className="px-5 py-6 text-sm text-ink-faint">
          No evidence was supplied. With nothing to check against, TrustLens fails
          safe to <span className="font-medium text-ink-soft">Needs verification</span>.
        </div>
      ) : (
        <ol className="divide-y divide-line">
          {evidence.map((snippet, i) => {
            const cited = citing(i);
            return (
              <li key={i} className="px-5 py-3 text-sm leading-relaxed">
                <div className="flex gap-3">
                  <span className="mt-0.5 font-mono text-2xs text-ink-faint">E{i + 1}</span>
                  <span className="flex-1 text-ink-soft">{snippet}</span>
                </div>
                {cited.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1 pl-8">
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
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
