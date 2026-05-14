"use client";

import * as React from "react";
import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthButton } from "@/components/auth/auth-button";
import { resetPassword } from "@/lib/api";

type SearchParamsRecord = Record<string, string | string[] | undefined>;

function getParam(sp: SearchParamsRecord | undefined, key: string): string | null {
  if (!sp || !(key in sp)) return null;
  const v = sp[key];
  return Array.isArray(v) ? v[0] ?? null : (v ?? null);
}

function ResetPasswordForm({ sp }: { sp: SearchParamsRecord }) {
  const router = useRouter();
  const tokenFromUrl = getParam(sp, "token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8 || password.length > 256) {
      setError("Password must be between 8 and 256 characters.");
      return;
    }
    if (!/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      setError("Password must contain at least one letter and one number.");
      return;
    }
    const token = getParam(sp, "token");
    if (!token) {
      setError("Missing reset token. Use the link from your email.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      router.replace("/login?reset=success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  if (!tokenFromUrl) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
        <AuthCard>
          <div className="text-center">
            <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
            <p className="mt-2 text-foreground-secondary">Invalid or missing reset link. Request a new link from the forgot password page.</p>
            <Link href="/forgot-password" className="mt-4 inline-block font-semibold text-[#0A66C2] hover:underline">
              Forgot password
            </Link>
          </div>
        </AuthCard>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
      <AuthCard>
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
          <p className="mt-2 text-lg text-foreground-secondary">Set new password</p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {error && (
            <div
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              {error}
            </div>
          )}

          <AuthInput
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            maxLength={256}
            placeholder="8–256 characters, one letter and one number"
          />

          <AuthInput
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
            maxLength={256}
            placeholder="Repeat new password"
          />

          <AuthButton type="submit" loading={loading}>
            Reset password
          </AuthButton>
        </form>

        <p className="mt-6 text-center text-sm text-foreground-secondary">
          <Link href="/login" className="font-semibold text-[#0A66C2] hover:underline">
            Back to sign in
          </Link>
        </p>
      </AuthCard>
    </div>
  );
}

export default function ResetPasswordPage({
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
      <ResetPasswordForm sp={sp} />
    </Suspense>
  );
}
