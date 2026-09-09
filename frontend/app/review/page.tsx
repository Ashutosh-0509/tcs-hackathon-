"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, ChevronsUp, X } from "lucide-react";
import { Shell } from "@/components/layout/Shell";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Label, Textarea } from "@/components/ui/Field";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { ReviewQueue } from "@/components/ReviewQueue";
import { ReliabilityBadge } from "@/components/ReliabilityBadge";
import { ClaimsPanel } from "@/components/ClaimsPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { WarningPanel } from "@/components/WarningPanel";
import { AnswerCard } from "@/components/AnswerCard";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";
import { LABEL_META } from "@/lib/labels";
import type {
  ReliabilityLabel,
  ReviewDetail,
  ReviewQueueItem,
  ReviewStatus,
} from "@/lib/types";

const LABELS: ReliabilityLabel[] = ["CERTAIN", "UNCERTAIN", "NEEDS_VERIFICATION"];

export default function ReviewPage() {
  const [queue, setQueue] = useState<ReviewQueueItem[] | null>(null);
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | "ALL">("PENDING");
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadQueue = useCallback(() => {
    setQueue(null);
    api
      .getReviewQueue(statusFilter === "ALL" ? undefined : statusFilter)
      .then((q) => {
        setQueue(q);
        setSelected((s) => s ?? q[0]?.review_id ?? null);
      })
      .catch(() => setQueue([]));
  }, [statusFilter]);

  useEffect(loadQueue, [loadQueue]);

  useEffect(() => {
    if (!selected) return setDetail(null);
    setDetailLoading(true);
    api
      .getReview(selected)
      .then(setDetail)
      .finally(() => setDetailLoading(false));
  }, [selected]);

  return (
    <Shell requireEditor maxWidth="max-w-7xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Review queue</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Answers below <span className="font-medium">Certain</span> are held here for a human decision.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(300px,360px)_1fr]">
        <Card className="h-fit lg:sticky lg:top-20">
          <CardHeader
            title="Queue"
            right={
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as ReviewStatus | "ALL")}
                className="rounded-control border border-line bg-surface px-2 py-1 text-xs"
              >
                {["PENDING", "APPROVED", "REJECTED", "ESCALATED", "ALL"].map((s) => (
                  <option key={s} value={s}>
                    {s[0] + s.slice(1).toLowerCase()}
                  </option>
                ))}
              </select>
            }
          />
          {!queue ? (
            <CenteredSpinner />
          ) : (
            <ReviewQueue
              items={queue}
              activeId={selected ?? undefined}
              onSelect={(it) => setSelected(it.review_id)}
            />
          )}
        </Card>

        <div>
          {detailLoading && !detail && <CenteredSpinner />}
          {detail && (
            <ReviewDetailPane
              key={detail.review_id}
              detail={detail}
              onDecided={() => {
                loadQueue();
                api.getReview(detail.review_id).then(setDetail);
              }}
            />
          )}
          {!detail && !detailLoading && (
            <Card className="grid place-items-center py-24 text-sm text-ink-faint">
              Select an item from the queue.
            </Card>
          )}
        </div>
      </div>
    </Shell>
  );
}

function ReviewDetailPane({
  detail,
  onDecided,
}: {
  detail: ReviewDetail;
  onDecided: () => void;
}) {
  const decided = detail.status !== "PENDING";
  const [note, setNote] = useState(detail.decision_note ?? "");
  const [override, setOverride] = useState<ReliabilityLabel | null>(
    detail.overridden_label,
  );
  const [busy, setBusy] = useState<ReviewStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(status: ReviewStatus) {
    setBusy(status);
    setError(null);
    try {
      await api.submitReview(detail.review_id, {
        status,
        decision_note: note || undefined,
        override_label: override,
      });
      onDecided();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <WarningPanel
        label={detail.effective_label}
        reasons={detail.reasons}
        reviewRequired={!decided}
      />

      <AnswerCard
        question={detail.question}
        answer={detail.answer}
        requestId={detail.request_id}
      />
      <ClaimsPanel claims={detail.claims} sources={detail.sources} />
      <EvidencePanel sources={detail.sources} claims={detail.claims} />

      {detail.explanation && (
        <Card>
          <CardHeader title="Explanation" />
          <CardBody>
            <p className="text-sm leading-relaxed text-ink-soft">{detail.explanation}</p>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Decision"
          right={
            decided ? (
              <span className="text-xs text-ink-faint">
                Decided{detail.decided_at ? ` · ${new Date(detail.decided_at).toLocaleString()}` : ""}
              </span>
            ) : undefined
          }
        />
        <CardBody className="space-y-4">
          <div>
            <Label>Final label</Label>
            <div className="flex flex-wrap gap-1.5">
              {LABELS.map((l) => {
                const active = (override ?? detail.label) === l;
                return (
                  <button
                    key={l}
                    disabled={decided}
                    onClick={() => setOverride(l === detail.label ? null : l)}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs font-medium transition disabled:opacity-60",
                      active
                        ? "border-ink bg-ink text-bg"
                        : "border-line text-ink-soft hover:bg-raised",
                    )}
                  >
                    {LABEL_META[l].text}
                  </button>
                );
              })}
            </div>
            <p className="mt-1.5 text-xs text-ink-faint">
              Machine label:{" "}
              <span className="font-medium text-ink-soft">{LABEL_META[detail.label].text}</span>{" "}
              ({detail.final_score}/100).
              {override && override !== detail.label && " You are overriding it."}
            </p>
          </div>

          <div>
            <Label htmlFor="note">Reviewer note</Label>
            <Textarea
              id="note"
              value={note}
              disabled={decided}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Why this decision? What did you verify?"
              rows={3}
            />
          </div>

          {error && <p className="text-xs text-[var(--alert)]">{error}</p>}

          {decided ? (
            <div className="flex items-center gap-2">
              <ReliabilityBadge
                label={detail.effective_label}
                size="sm"
                overridden={!!detail.overridden_label}
              />
              <span className="text-sm text-ink-soft">
                Marked <span className="font-medium">{detail.status.toLowerCase()}</span>.
              </span>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                loading={busy === "APPROVED"}
                onClick={() => decide("APPROVED")}
              >
                <Check className="h-4 w-4" /> Approve
              </Button>
              <Button
                variant="danger"
                loading={busy === "REJECTED"}
                onClick={() => decide("REJECTED")}
              >
                <X className="h-4 w-4" /> Reject
              </Button>
              <Button
                variant="secondary"
                loading={busy === "ESCALATED"}
                onClick={() => decide("ESCALATED")}
              >
                <ChevronsUp className="h-4 w-4" /> Escalate
              </Button>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
