import { cn } from "@/lib/cn";

type Tone = "certain" | "caution" | "alert" | "neutral";

const TONES: Record<Tone, string> = {
  certain: "bg-[var(--certain-tint)] text-[var(--certain)] border-[var(--certain-line)]",
  caution: "bg-[var(--caution-tint)] text-[var(--caution)] border-[var(--caution-line)]",
  alert: "bg-[var(--alert-tint)] text-[var(--alert)] border-[var(--alert-line)]",
  neutral: "bg-raised text-ink-soft border-line",
};

export function Pill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5",
        "text-2xs font-semibold uppercase tracking-wide",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
