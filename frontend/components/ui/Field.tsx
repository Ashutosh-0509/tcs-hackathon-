"use client";

import { cn } from "@/lib/cn";

const base =
  "w-full rounded-control border border-line bg-surface px-3 py-2 text-sm text-ink " +
  "placeholder:text-ink-faint focus-visible:outline-none focus-visible:ring-2 " +
  "focus-visible:ring-ink/20 focus-visible:border-ink/30 transition";

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-[13px] font-medium text-ink-soft">
      {children}
    </label>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(base, props.className)} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(base, "min-h-[84px] resize-y leading-relaxed", props.className)}
    />
  );
}
