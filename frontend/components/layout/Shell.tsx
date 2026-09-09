"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

export function Shell({
  children,
  requireEditor = false,
  maxWidth = "max-w-6xl",
}: {
  children: React.ReactNode;
  requireEditor?: boolean;
  maxWidth?: string;
}) {
  const { loading, isEditor } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (requireEditor && !loading && !isEditor) router.replace("/login?next=editor");
  }, [requireEditor, loading, isEditor, router]);

  return (
    <div className="min-h-dvh">
      <TopBar />
      <main className={`mx-auto ${maxWidth} px-4 py-8 sm:px-6`}>
        {requireEditor && (loading || !isEditor) ? (
          <CenteredSpinner label={loading ? "Checking access…" : "Redirecting…"} />
        ) : (
          children
        )}
      </main>
    </div>
  );
}
