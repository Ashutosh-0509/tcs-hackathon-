"use client";

import { cn } from "@/lib/cn";
import { relativeTime } from "@/lib/format";
import { REVIEW_STATUS_META } from "@/lib/labels";
import { Pill } from "@/components/ui/Pill";
import { ReliabilityBadge } from "@/components/ReliabilityBadge";
import type { ReviewQueueItem } from "@/lib/types";

export function ReviewQueue({
  items,
  activeId,
  onSelect,
}: {
  items: ReviewQueueItem[];
  activeId?: string;
  onSelect: (item: ReviewQueueItem) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="px-5 py-16 text-center text-sm text-ink-faint">
        Nothing in the queue. Answers below <span className="font-medium">Certain</span> land here
        automatically.
      </div>
    );
  }
  return (
    <ul className="divide-y divide-line">
      {items.map((it) => {
        const status = REVIEW_STATUS_META[it.status];
        return (
          <li key={it.review_id}>
            <button
              onClick={() => onSelect(it)}
              className={cn(
                "w-full px-4 py-3 text-left transition hover:bg-raised/70",
                activeId === it.review_id && "bg-raised",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="line-clamp-1 text-sm font-medium">{it.question}</span>
                <Pill tone={status.tone === "neutral" ? "neutral" : status.tone}>
                  {status.text}
                </Pill>
              </div>
              <p className="mt-1 line-clamp-1 text-xs text-ink-faint">{it.answer}</p>
              <div className="mt-2 flex items-center gap-2">
                <ReliabilityBadge
                  label={it.effective_label}
                  size="sm"
                  overridden={!!it.overridden_label}
                />
                <span className="tnum text-2xs text-ink-faint">{it.final_score}/100</span>
                <span className="text-2xs text-ink-faint">· {relativeTime(it.created_at)}</span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
