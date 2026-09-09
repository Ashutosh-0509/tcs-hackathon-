import { Card, CardHeader } from "@/components/ui/Card";
import type { ClaimResult } from "@/lib/types";

export function EvidencePanel({
  evidence,
  claims,
}: {
  evidence: string[];
  claims?: ClaimResult[];
}) {
  const matchedBy = (ordinal: number) =>
    (claims ?? []).filter((c) => c.best_evidence_ordinal === ordinal).length;

  return (
    <Card>
      <CardHeader
        title="Evidence"
        hint={evidence.length ? `${evidence.length} source snippet${evidence.length > 1 ? "s" : ""}` : undefined}
      />
      {evidence.length === 0 ? (
        <div className="px-5 py-6 text-sm text-ink-faint">
          No evidence was supplied. With nothing to check against, TrustLens fails
          safe to <span className="font-medium text-ink-soft">Needs verification</span>.
        </div>
      ) : (
        <ol className="divide-y divide-line">
          {evidence.map((snippet, i) => {
            const n = matchedBy(i);
            return (
              <li key={i} className="flex gap-3 px-5 py-3 text-sm leading-relaxed">
                <span className="mt-0.5 font-mono text-2xs text-ink-faint">E{i + 1}</span>
                <span className="flex-1 text-ink-soft">{snippet}</span>
                {n > 0 && (
                  <span className="mt-0.5 shrink-0 text-2xs text-ink-faint">
                    ↳ {n} claim{n > 1 ? "s" : ""}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
