import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustLens",
  description: "A reliability layer for AI answers.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-3xl px-4 py-8">
          <header className="mb-8">
            <h1 className="text-2xl font-semibold tracking-tight">TrustLens</h1>
            <p className="text-sm text-slate-500">
              A reliability layer for AI answers. The backend is the source of truth.
            </p>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
