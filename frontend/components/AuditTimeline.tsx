import {
  FileSearch,
  Gavel,
  LogIn,
  Sparkles,
  UserPlus,
  Dot,
} from "lucide-react";
import { relativeTime, titleCase } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";

const ICONS: Record<string, typeof Dot> = {
  LOGIN: LogIn,
  REGISTER: UserPlus,
  ANSWER_GENERATED: Sparkles,
  ANSWER_EVALUATED: FileSearch,
  REVIEW_DECIDED: Gavel,
};

function metaChips(m: Record<string, unknown>) {
  const keys = ["label", "score", "status", "overridden_label", "model", "latency_ms", "pii_findings"];
  return keys
    .filter((k) => m[k] !== undefined && m[k] !== null && m[k] !== "")
    .map((k) => `${k.replace(/_/g, " ")}: ${String(m[k])}`);
}

export function AuditTimeline({ items }: { items: AuditEntry[] }) {
  if (items.length === 0) {
    return <p className="px-5 py-16 text-center text-sm text-ink-faint">No audit records yet.</p>;
  }
  return (
    <ol className="relative ml-3 border-l border-line">
      {items.map((e) => {
        const Icon = ICONS[e.action] ?? Dot;
        return (
          <li key={e.id} className="relative py-3.5 pl-6">
            <span className="absolute -left-[9px] top-4 grid h-4 w-4 place-items-center rounded-full border border-line bg-surface">
              <Icon className="h-2.5 w-2.5 text-ink-soft" />
            </span>
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-sm font-medium">{titleCase(e.action)}</span>
              <span className="text-xs text-ink-faint">{e.entity_type}</span>
              <span className="text-xs text-ink-faint">· {relativeTime(e.created_at)}</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-ink-soft">
              {metaChips(e.metadata).map((c, i) => (
                <span key={i}>{c}</span>
              ))}
            </div>
            <p className="mt-0.5 font-mono text-2xs text-ink-faint">{e.request_id}</p>
          </li>
        );
      })}
    </ol>
  );
}
