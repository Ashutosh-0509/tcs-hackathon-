import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import { LABEL_META, toneFor } from "@/lib/labels";
import { cn } from "@/lib/cn";
import type { ReliabilityLabel, SecurityBlock } from "@/lib/types";

const ICON: Record<ReliabilityLabel, typeof ShieldCheck> = {
  CERTAIN: ShieldCheck,
  UNCERTAIN: ShieldAlert,
  NEEDS_VERIFICATION: ShieldX,
};

export function WarningPanel({
  label,
  reasons,
  security,
  reviewRequired,
}: {
  label: ReliabilityLabel;
  reasons: string[];
  security?: SecurityBlock;
  reviewRequired?: boolean;
}) {
  const meta = LABEL_META[label];
  const tone = toneFor(label);
  const Icon = ICON[label];

  return (
    <div className={cn("rounded-card border p-4", tone.bg, tone.border)}>
      <div className="flex gap-3">
        <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", tone.text)} />
        <div className="space-y-2">
          <p className={cn("text-sm font-semibold", tone.text)}>
            Recommended action — {meta.text}
          </p>
          <p className="text-sm text-ink-soft">{meta.action}</p>

          {reasons.length > 0 && (
            <ul className="mt-1 space-y-1 text-xs text-ink-soft">
              {reasons.map((r, i) => (
                <li key={i} className="flex gap-1.5">
                  <span className={tone.text}>—</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          )}

          {reviewRequired && (
            <p className="text-xs text-ink-faint">
              This answer was routed to the human review queue.
            </p>
          )}

          {security?.pii_detected && (
            <p className="text-xs text-ink-faint">
              {security.pii_findings.map((f) => `${f.type}×${f.count}`).join(", ")} redacted
              before the model and before storage.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
