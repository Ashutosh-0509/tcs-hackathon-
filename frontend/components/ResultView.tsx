import { AnswerCard } from "@/components/AnswerCard";
import { ScoreCard } from "@/components/ScoreCard";
import { ClaimsPanel } from "@/components/ClaimsPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { WarningPanel } from "@/components/WarningPanel";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  AnswerSource,
  ClaimResult,
  MetricsBlock,
  QuestionMode,
  ReliabilityBlock,
  ReliabilityLabel,
  SecurityBlock,
  SourceRef,
} from "@/lib/types";

export interface ResultViewData {
  question: string;
  answer: string;
  sources: SourceRef[];
  claims: ClaimResult[];
  metrics: MetricsBlock;
  reliability: ReliabilityBlock;
  security?: SecurityBlock;
  explanation?: string | null;
  reviewRequired?: boolean;
  requestId?: string;
  source?: AnswerSource;
  model?: string | null;
  effectiveLabel?: ReliabilityLabel;
  mode?: QuestionMode;
}

export function ResultView({ data }: { data: ResultViewData }) {
  const label = data.effectiveLabel ?? data.reliability.label;
  const retrieved = data.mode === "ASK";
  return (
    <div className="animate-fade-up space-y-4">
      <WarningPanel
        label={label}
        reasons={data.reliability.reasons}
        security={data.security}
        reviewRequired={data.reviewRequired}
      />

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          <AnswerCard
            question={data.question}
            answer={data.answer}
            source={data.source}
            model={data.model}
            requestId={data.requestId}
            mode={data.mode}
          />
          <ClaimsPanel claims={data.claims} sources={data.sources} />
          <EvidencePanel sources={data.sources} claims={data.claims} retrieved={retrieved} />
        </div>

        <div className="space-y-4 lg:col-span-2">
          <ScoreCard
            reliability={data.reliability}
            metrics={data.metrics}
            effectiveLabel={data.effectiveLabel}
          />
          {data.explanation && (
            <Card>
              <CardHeader title="Why this verdict" hint="Plain-language — does not change the score" />
              <CardBody>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">
                  {data.explanation}
                </p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
