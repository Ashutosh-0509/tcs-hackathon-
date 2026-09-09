import { Card } from "@/components/ui/Card";
import { ReliabilityBadge } from "@/components/ReliabilityBadge";
import { ScoreGauge } from "@/components/ScoreGauge";
import { LABEL_META } from "@/lib/labels";
import { pct } from "@/lib/format";
import type { MetricsBlock, ReliabilityBlock } from "@/lib/types";

function SignalBar({
  name,
  value,
  weight,
}: {
  name: string;
  value: number;
  weight?: number;
}) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="text-ink-soft">
          {name}
          {weight != null && (
            <span className="ml-1.5 text-ink-faint">·&nbsp;{Math.round(weight * 100)}% wt</span>
          )}
        </span>
        <span className="tnum font-medium">{pct(value)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full bg-ink/70"
          style={{ width: `${Math.max(2, Math.round(value * 100))}%` }}
        />
      </div>
    </div>
  );
}

export function ScoreCard({
  reliability,
  metrics,
  effectiveLabel,
}: {
  reliability: ReliabilityBlock;
  metrics: MetricsBlock;
  effectiveLabel?: ReliabilityBlock["label"];
}) {
  const w = reliability.weights;
  const overridden = !!effectiveLabel && effectiveLabel !== reliability.label;
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col items-center gap-3 border-b border-line px-5 py-6 sm:flex-row sm:items-center sm:gap-6">
        <ScoreGauge score={reliability.final_score} label={effectiveLabel ?? reliability.label} />
        <div className="flex-1 text-center sm:text-left">
          <ReliabilityBadge label={effectiveLabel ?? reliability.label} overridden={overridden} />
          <p className="mt-2 text-sm text-ink-soft">
            {LABEL_META[effectiveLabel ?? reliability.label].gloss}
          </p>
          {overridden && (
            <p className="mt-1 text-xs text-ink-faint">
              Machine label was{" "}
              <span className="font-medium">{LABEL_META[reliability.label].text}</span>{" "}
              ({reliability.final_score}/100).
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-3.5 px-5 py-4 sm:grid-cols-2">
        <SignalBar name="Evidence support" value={reliability.evidence_score} weight={w.evidence} />
        <SignalBar name="Semantic support" value={reliability.semantic_score} weight={w.semantic} />
        <SignalBar name="Confidence" value={reliability.uncertainty_score} weight={w.uncertainty} />
        <SignalBar name="Answer relevance" value={reliability.relevance_score} weight={w.relevance} />
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-5 py-3 text-xs text-ink-faint">
        <span>
          Perplexity:{" "}
          {metrics.perplexity_available && metrics.perplexity != null
            ? metrics.perplexity.toFixed(2)
            : "not available"}
        </span>
        <span>Evidence snippets: {metrics.evidence_count}</span>
        <span>
          Thresholds: certain ≥ {reliability.thresholds.certain}, uncertain ≥{" "}
          {reliability.thresholds.uncertain}
        </span>
      </div>
    </Card>
  );
}
