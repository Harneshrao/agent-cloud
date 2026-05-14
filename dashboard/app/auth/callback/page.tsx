"use client";

import * as React from "react";
import { useEffect, useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import { setTokens } from "@/lib/auth";

type SearchParamsRecord = Record<string, string | string[] | undefined>;

function getParam(sp: SearchParamsRecord | undefined, key: string): string | null {
  if (!sp || !(key in sp)) return null;
  const v = sp[key];
  return Array.isArray(v) ? v[0] ?? null : (v ?? null);
}

function CallbackHandler({ sp }: { sp: SearchParamsRecord }) {
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    const accessToken = getParam(sp, "access_token");
    const refreshToken = getParam(sp, "refresh_token");
    const error = getParam(sp, "error");
    if (error) {
      setStatus("error");
      router.replace(`/login?error=${encodeURIComponent(error)}`);
      return;
    }
    if (accessToken) {
      setTokens(accessToken, refreshToken ?? undefined);
      setStatus("ok");
      router.replace("/dashboard");
      return;
    }
    setStatus("error");
    router.replace("/login?error=missing_tokens");
  }, [sp, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF]">
      {status === "loading" && (
        <p className="text-foreground-secondary">Signing you in…</p>
      )}
      {status === "error" && (
        <p className="text-foreground-secondary">Redirecting to login…</p>
      )}
    </div>
  );
}

export default function AuthCallbackPage({
  searchParams,
}: {
  searchParams?: Promise<SearchParamsRecord>;
}) {
  const sp = React.use(searchParams ?? Promise.resolve({}));
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF]">
        <span className="text-foreground-secondary">Loading…</span>
      </div>
    }>
      <CallbackHandler sp={sp} />
    </Suspense>
  );
}
