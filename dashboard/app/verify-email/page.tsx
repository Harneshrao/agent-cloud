"use client";

import * as React from "react";
import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { verifyEmail } from "@/lib/api";

type SearchParamsRecord = Record<string, string | string[] | undefined>;

function getParam(sp: SearchParamsRecord | undefined, key: string): string | null {
  if (!sp || !(key in sp)) return null;
  const v = sp[key];
  return Array.isArray(v) ? v[0] ?? null : (v ?? null);
}

function VerifyEmailHandler({ sp }: { sp: SearchParamsRecord }) {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = getParam(sp, "token");
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token. Use the link from your email.");
      return;
    }
    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message ?? "Email verified. You can now log in.");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [sp]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
      <AuthCard>
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
          <p className="mt-2 text-lg text-foreground-secondary">Email verification</p>
        </div>

        <div className="mt-8 space-y-4">
          {status === "loading" && (
            <p className="text-foreground-secondary">Verifying your email…</p>
          )}
          {status === "success" && (
            <>
              <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
                {message}
              </p>
              <Link
                href="/login"
                className="block w-full rounded-lg bg-[#0A66C2] py-2.5 text-center font-semibold text-white hover:bg-[#004182]"
              >
                Sign in
              </Link>
            </>
          )}
          {status === "error" && (
            <>
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {message}
              </p>
              <Link
                href="/login"
                className="block w-full rounded-lg border border-border py-2.5 text-center font-medium text-foreground hover:bg-muted/50"
              >
                Back to sign in
              </Link>
              <p className="text-center text-sm text-foreground-secondary">
                Need a new link?{" "}
                <Link href="/login" className="font-semibold text-[#0A66C2] hover:underline">
                  Sign in
                </Link>{" "}
                and request verification again.
              </p>
            </>
          )}
        </div>
      </AuthCard>
    </div>
  );
}

export default function VerifyEmailPage({
  searchParams,
}: {
  searchParams?: Promise<SearchParamsRecord>;
}) {
  const sp = React.use(searchParams ?? Promise.resolve({}));
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF]">
          <span className="text-foreground-secondary">Loading…</span>
        </div>
      }
    >
      <VerifyEmailHandler sp={sp} />
    </Suspense>
  );
}
