import { cn } from "@/lib/cn";
import { LABEL_META, toneFor } from "@/lib/labels";
import type { ReliabilityLabel } from "@/lib/types";

export function ReliabilityBadge({
  label,
  size = "md",
  overridden = false,
}: {
  label: ReliabilityLabel;
  size?: "sm" | "md";
  overridden?: boolean;
}) {
  const meta = LABEL_META[label];
  const tone = toneFor(label);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border font-semibold uppercase tracking-wide",
        tone.bg,
        tone.text,
        tone.border,
        size === "sm" ? "px-2.5 py-0.5 text-2xs" : "px-3 py-1 text-xs",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} />
      {meta.text}
      {overridden && (
        <span className="font-normal normal-case opacity-70">· human override</span>
      )}
    </span>
  );
}
