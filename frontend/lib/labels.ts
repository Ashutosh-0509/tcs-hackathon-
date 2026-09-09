import type { ReliabilityLabel, ReviewStatus } from "./types";

interface LabelMeta {
  text: string;
  tone: "certain" | "caution" | "alert";
  /** one-line plain-language reading */
  gloss: string;
  /** recommended action shown in the WarningPanel */
  action: string;
}

export const LABEL_META: Record<ReliabilityLabel, LabelMeta> = {
  CERTAIN: {
    text: "Certain",
    tone: "certain",
    gloss: "Claims are well supported by the supplied evidence.",
    action: "Safe to use. Spot-check before high-stakes decisions.",
  },
  UNCERTAIN: {
    text: "Uncertain",
    tone: "caution",
    gloss: "Partial support, or a signal disagrees with the evidence.",
    action: "Review the flagged claims before relying on this answer.",
  },
  NEEDS_VERIFICATION: {
    text: "Needs verification",
    tone: "alert",
    gloss: "Evidence is missing, contradictory, or a critical claim is unsupported.",
    action: "Do not use as-is. Route to a human reviewer.",
  },
};

export const TONE_CLASSES: Record<LabelMeta["tone"], { text: string; bg: string; border: string; dot: string; ring: string }> = {
  certain: {
    text: "text-[var(--certain)]",
    bg: "bg-[var(--certain-tint)]",
    border: "border-[var(--certain-line)]",
    dot: "bg-[var(--certain)]",
    ring: "stroke-[var(--certain)]",
  },
  caution: {
    text: "text-[var(--caution)]",
    bg: "bg-[var(--caution-tint)]",
    border: "border-[var(--caution-line)]",
    dot: "bg-[var(--caution)]",
    ring: "stroke-[var(--caution)]",
  },
  alert: {
    text: "text-[var(--alert)]",
    bg: "bg-[var(--alert-tint)]",
    border: "border-[var(--alert-line)]",
    dot: "bg-[var(--alert)]",
    ring: "stroke-[var(--alert)]",
  },
};

export function toneFor(label: ReliabilityLabel) {
  return TONE_CLASSES[LABEL_META[label].tone];
}

export const REVIEW_STATUS_META: Record<ReviewStatus, { text: string; tone: "certain" | "caution" | "alert" | "neutral" }> = {
  PENDING: { text: "Pending", tone: "caution" },
  APPROVED: { text: "Approved", tone: "certain" },
  REJECTED: { text: "Rejected", tone: "alert" },
  ESCALATED: { text: "Escalated", tone: "alert" },
};
