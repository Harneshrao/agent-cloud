"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";

const PUBLIC_PREFIXES = [
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/auth/",
];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p)
  );
}

export function ProductLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const skipAuth =
    process.env.NEXT_PUBLIC_SKIP_AUTH === "1" ||
    process.env.NEXT_PUBLIC_ALLOW_ANONYMOUS_DEV === "1";

  if (isPublicRoute(pathname)) {
    return <>{children}</>;
  }

  if (skipAuth) {
    return <AppShell>{children}</AppShell>;
  }

  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
