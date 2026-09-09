"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ScanEye } from "lucide-react";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Label, Input } from "@/components/ui/Field";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

const DEMO = [
  { email: "user@trustlens.dev", role: "USER" },
  { email: "editor@trustlens.dev", role: "EDITOR" },
  { email: "admin@trustlens.dev", role: "ADMIN" },
];

function LoginInner() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("editor@trustlens.dev");
  const [password, setPassword] = useState("trustlens");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.replace(params.get("next") === "editor" ? "/review" : "/analyze");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <ScanEye className="h-5 w-5" />
          <span className="text-lg font-semibold tracking-tight">TrustLens</span>
        </div>

        <Card>
          <CardBody className="space-y-4">
            <div>
              <h1 className="text-base font-semibold">Sign in</h1>
              <p className="mt-0.5 text-xs text-ink-faint">
                Reviewer and admin tools require an account. Analysis is open.
              </p>
            </div>
            <form onSubmit={submit} className="space-y-3">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="pw">Password</Label>
                <Input
                  id="pw"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              {error && (
                <p className="text-xs text-[var(--alert)]">{error}</p>
              )}
              <Button type="submit" loading={loading} className="w-full">
                Sign in
              </Button>
            </form>

            <div className="rounded-control border border-line bg-raised/50 p-3">
              <p className="mb-2 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                Demo accounts · password “trustlens”
              </p>
              <div className="space-y-1">
                {DEMO.map((d) => (
                  <button
                    key={d.email}
                    onClick={() => {
                      setEmail(d.email);
                      setPassword("trustlens");
                    }}
                    className={cn(
                      "flex w-full items-center justify-between rounded-[7px] px-2 py-1 text-xs",
                      "hover:bg-surface",
                      email === d.email && "bg-surface",
                    )}
                  >
                    <span className="font-mono">{d.email}</span>
                    <span className="text-ink-faint">{d.role}</span>
                  </button>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>

        <a href="/analyze" className="mt-4 block text-center text-xs text-ink-faint hover:text-ink">
          Continue without signing in →
        </a>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}
