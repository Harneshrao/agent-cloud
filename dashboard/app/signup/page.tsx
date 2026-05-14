"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth/auth-card";
import { AuthInput } from "@/components/auth/auth-input";
import { AuthButton } from "@/components/auth/auth-button";
import { register } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [success, setSuccess] = useState(false);

  const attemptSignup = async () => {
    setError("");
    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();
    const pwd = password.trim();

    if (!pwd || pwd.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (pwd.length > 256) {
      setError("Password cannot exceed 256 characters.");
      return;
    }

    setLoading(true);
    try {
      await register(trimmedName, trimmedEmail, pwd);
      setSuccess(true);
      setTimeout(() => router.replace("/login"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    attemptSignup();
  };

  const isServerError = error.startsWith("Server unavailable");

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F3F2EF] px-4 py-8">
      <AuthCard>
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-primary">Agent Cloud</h1>
          <p className="mt-2 text-lg text-foreground-secondary">Join the platform</p>
        </div>

        {success ? (
          <div className="mt-8 space-y-4">
            <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
              Account created. You can sign in now.
            </p>
            <Link
              href="/login"
              className="block w-full rounded-lg bg-[#0A66C2] py-2.5 text-center font-semibold text-white hover:bg-[#004182]"
            >
              Go to sign in
            </Link>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {error && (
            <div
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              <span>{error}</span>
              {isServerError && (
                <button
                  type="button"
                  onClick={() => attemptSignup()}
                  disabled={loading}
                  className="mt-2 block w-full rounded-md border border-red-300 bg-white py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                >
                  {loading ? "Connecting…" : "Retry"}
                </button>
              )}
            </div>
          )}

          <AuthInput
            label="Name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Your name"
          />

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
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            maxLength={256}
            placeholder="8–256 characters, one letter and one number"
          />

          <AuthButton type="submit" loading={loading}>
            Create account
          </AuthButton>
        </form>
        )}

        <p className="mt-6 text-center text-sm text-foreground-secondary">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-[#0A66C2] hover:underline">
            Sign in
          </Link>
        </p>
      </AuthCard>
    </div>
  );
}
