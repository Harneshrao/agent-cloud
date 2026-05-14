"use client";

import { useState } from "react";
import Link from "next/link";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthButton } from "@/components/auth/auth-button";
import { forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await forgotPassword(email.trim());
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
      <AuthCard>
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
          <p className="mt-2 text-lg text-foreground-secondary">Forgot password</p>
        </div>

        {success ? (
          <div className="mt-8 space-y-4">
            <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
              If an account exists for this email, you will receive a reset link shortly. Check your inbox and spam folder.
            </p>
            <Link
              href="/login"
              className="block w-full rounded-lg bg-[#0A66C2] py-2.5 text-center font-semibold text-white hover:bg-[#004182]"
            >
              Back to sign in
            </Link>
          </div>
        ) : (
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
              label="Email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
            />

            <AuthButton type="submit" loading={loading}>
              Send reset link
            </AuthButton>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-foreground-secondary">
          <Link href="/login" className="font-semibold text-[#0A66C2] hover:underline">
            Back to sign in
          </Link>
        </p>
      </AuthCard>
    </div>
  );
}
