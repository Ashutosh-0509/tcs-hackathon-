"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ScanEye, LogOut } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const NAV = [
  { href: "/analyze", label: "Analyze" },
  { href: "/history", label: "History" },
  { href: "/review", label: "Review", editor: true },
  { href: "/audit", label: "Audit", editor: true },
];

export function TopBar() {
  const pathname = usePathname();
  const { user, isEditor, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Link href="/analyze" className="flex items-center gap-2">
          <ScanEye className="h-[18px] w-[18px]" />
          <span className="text-[15px] font-semibold tracking-tight">TrustLens</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV.filter((n) => !n.editor || isEditor).map((n) => {
            const active = pathname === n.href || pathname.startsWith(n.href + "/");
            return (
              <Link
                key={n.href}
                href={n.href}
                className={cn(
                  "rounded-control px-2.5 py-1.5 text-[13px] font-medium transition",
                  active ? "bg-raised text-ink" : "text-ink-faint hover:text-ink hover:bg-raised/60",
                )}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <>
              <span className="hidden text-xs text-ink-faint sm:inline">
                {user.email} · {user.role}
              </span>
              <button
                onClick={logout}
                title="Sign out"
                className="grid h-8 w-8 place-items-center rounded-control border border-line text-ink-soft hover:text-ink hover:bg-raised"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-control bg-ink px-3 py-1.5 text-[13px] font-medium text-bg hover:opacity-90"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
