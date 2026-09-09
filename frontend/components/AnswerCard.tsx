import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import type { AnswerSource } from "@/lib/types";

export function AnswerCard({
  question,
  answer,
  source,
  model,
  requestId,
}: {
  question: string;
  answer: string;
  source?: AnswerSource;
  model?: string | null;
  requestId?: string;
}) {
  return (
    <Card>
      <CardHeader
        title="Answer"
        right={
          <div className="flex items-center gap-2">
            {source && (
              <Pill tone="neutral">
                {source === "TRUSTLENS_LLM" ? "Generated" : "External"}
              </Pill>
            )}
            {model && <span className="text-xs text-ink-faint">{model}</span>}
          </div>
        }
      />
      <CardBody className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">
          Question
        </p>
        <p className="text-[15px] leading-relaxed text-ink-soft">{question}</p>
        <div className="my-3 h-px bg-line" />
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{answer}</p>
        {requestId && (
          <p className="pt-1 font-mono text-2xs text-ink-faint">{requestId}</p>
        )}
      </CardBody>
    </Card>
  );
}
