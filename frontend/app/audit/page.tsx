"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/layout/Shell";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Field";
import { CenteredSpinner } from "@/components/ui/Spinner";
import { AuditTimeline } from "@/components/AuditTimeline";
import { api } from "@/lib/api";
import type { AuditPage } from "@/lib/types";

export default function AuditPageView() {
  const [page, setPage] = useState<AuditPage | null>(null);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setPage(null);
      api
        .getAuditLogs({ request_id: q.trim() || undefined, limit: 150 })
        .then(setPage)
        .catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <Shell requireEditor maxWidth="max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold tracking-tight">Audit trail</h1>
        <p className="mt-1 text-sm text-ink-soft">
          Immutable record of every generation, evaluation, and review decision.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Events"
          right={
            page ? <span className="text-xs text-ink-faint">{page.total} total</span> : undefined
          }
        />
        <CardBody>
          <Input
            placeholder="Filter by request ID, e.g. TRUST-2026-000123"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="mb-4 font-mono text-xs"
          />
          {error && <p className="text-sm text-[var(--alert)]">{error}</p>}
          {!page && !error ? <CenteredSpinner /> : page && <AuditTimeline items={page.items} />}
        </CardBody>
      </Card>
    </Shell>
  );
}
