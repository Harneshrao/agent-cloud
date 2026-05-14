"use client";

import * as React from "react";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthButton } from "@/components/auth/auth-button";
import { login } from "@/lib/api";
import { setTokens } from "@/lib/auth";

type SearchParamsPromise = Promise<Record<string, string | string[] | undefined>>;

function getParam(sp: Record<string, string | string[] | undefined> | undefined, key: string): string | null {
  if (!sp || !(key in sp)) return null;
  const v = sp[key];
  return Array.isArray(v) ? v[0] ?? null : (v ?? null);
}

export default function LoginPage({
  searchParams,
}: {
  searchParams?: SearchParamsPromise;
}) {
  const router = useRouter();
  const sp = React.use(searchParams ?? Promise.resolve({}));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const err = getParam(sp, "error");
    const reset = getParam(sp, "reset");
    if (reset === "success") {
      setError("");
      setSuccess("Password reset. You can sign in now.");
      return;
    }
    if (err === "account_inactive") setError("Account is inactive.");
    else if (err) setError("Sign-in failed. Try again.");
  }, [sp]);

  const attemptLogin = async () => {
    setError("");
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    if (!trimmedEmail || !trimmedPassword) {
      setError("Please enter your email and password.");
      return;
    }
    setLoading(true);
    try {
      const data = await login(trimmedEmail, trimmedPassword);
      const accessToken = data.access_token ?? (data as { token?: string }).token;
      const refreshToken = data.refresh_token ?? null;
      if (accessToken) {
        localStorage.setItem("token", accessToken);
        setTokens(accessToken, refreshToken);
        router.replace("/");
        return;
      }
      setError("Invalid response from server.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    attemptLogin();
  };

  const isServerError = error.startsWith("Server unavailable");

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
      <AuthCard>
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
          <p className="mt-2 text-lg text-foreground-secondary">Sign in</p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {success && (
            <div
              className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
              role="alert"
            >
              {success}
            </div>
          )}
          {error && (
            <div
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              <span>{error}</span>
              {isServerError && (
                <button
                  type="button"
                  onClick={() => attemptLogin()}
                  disabled={loading}
                  className="mt-2 block w-full rounded-md border border-red-300 bg-white py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  {loading ? "Connecting…" : "Retry"}
                </button>
              )}
            </div>
          )}

          <AuthInput
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="you@example.com"
          />

          <AuthInput
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <AuthButton type="submit" loading={loading}>
            Sign In
          </AuthButton>

          <p className="text-center text-sm">
            <Link href="/forgot-password" className="text-[#0A66C2] hover:underline">
              Forgot password?
            </Link>
          </p>
        </form>

        <p className="mt-6 text-center text-sm text-foreground-secondary">
          New here?{" "}
          <Link href="/signup" className="font-semibold text-[#0A66C2] hover:underline">
            Join now
          </Link>
        </p>
      </AuthCard>
    </div>
  );
}
