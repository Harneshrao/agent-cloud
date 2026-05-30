"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FolderKanban,
  Rocket,
  PlayCircle,
  KeyRound,
  AlertTriangle,
  BarChart3,
  Server,
  LineChart,
} from "lucide-react";
import { cn } from "@/lib/utils";

/** Core activation loop — always visible. */
const coreNav = [
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/deployments", label: "Deployments", icon: Rocket },
  { href: "/runs", label: "Runs & traces", icon: PlayCircle },
  { href: "/dlq", label: "Failed tasks", icon: AlertTriangle },
  { href: "/api-keys", label: "API keys", icon: KeyRound },
];

/** Optional ops — demoted so they don't compete with deploy → run. */
const advancedNav = [
  { href: "/usage", label: "Usage", icon: BarChart3 },
  { href: "/workers", label: "Workers", icon: Server },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-56 border-r border-border bg-[#F8FAFC]">
      <div className="flex h-full flex-col">
        <div className="flex h-16 items-center border-b border-border px-6">
          <Link
            href="/projects"
            className="flex items-center gap-2 text-[15px] font-semibold text-foreground"
          >
            <span className="text-primary">Agent</span>
            <span className="text-foreground">Cloud</span>
          </Link>
        </div>
        <nav className="flex-1 overflow-y-auto p-4">
          <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Build & run
          </p>
          <div className="grid gap-1">
            {coreNav.map((item) => (
              <NavLink key={item.href} item={item} pathname={pathname} />
            ))}
          </div>
          <p className="mb-2 mt-6 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Ops (optional)
          </p>
          <div className="grid gap-1">
            {advancedNav.map((item) => (
              <NavLink key={item.href} item={item} pathname={pathname} muted />
            ))}
          </div>
        </nav>
        <div className="border-t border-border p-4 space-y-2">
          {process.env.NEXT_PUBLIC_FOUNDER_ANALYTICS === "1" ? (
            <Link
              href="/founder"
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname === "/founder"
                  ? "bg-primary/10 text-primary"
                  : "text-neutral-600 hover:bg-black/5 hover:text-foreground"
              )}
            >
              <LineChart className="h-4 w-4" />
              PMF (founder)
            </Link>
          ) : null}
          <Link
            href="/limits"
            className="text-xs text-neutral-500 hover:text-primary"
          >
            Limits & quotas
          </Link>
        </div>
      </div>
    </aside>
  );
}

function NavLink({
  item,
  pathname,
  muted,
}: {
  item: { href: string; label: string; icon: React.ComponentType<{ className?: string }> };
  pathname: string;
  muted?: boolean;
}) {
  const isActive =
    pathname === item.href || pathname.startsWith(`${item.href}/`);
  return (
    <Link
      href={item.href}
      className={cn(
        "relative flex items-center gap-3 rounded-[10px] px-[14px] py-3 text-sm font-medium transition-all duration-200",
        muted && !isActive && "py-2.5 text-neutral-500",
        isActive
          ? "bg-accent-soft text-primary font-semibold shadow-[inset_0_0_0_1px_rgba(37,99,235,0.14)]"
          : "text-foreground-secondary hover:bg-[var(--hover-bg)] hover:text-primary"
      )}
    >
      {isActive ? (
        <span className="absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded bg-primary" />
      ) : null}
      <item.icon className="h-5 w-5 shrink-0" />
      {item.label}
    </Link>
  );
}
