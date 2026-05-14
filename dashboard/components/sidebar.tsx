"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Store,
  PlayCircle,
  Calendar,
  GitBranch,
  CreditCard,
  Code,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/marketplace", label: "Marketplace", icon: Store },
  { href: "/runs", label: "Run History", icon: PlayCircle },
  { href: "/automation", label: "Automation", icon: Calendar },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
  { href: "/usage", label: "Usage & Billing", icon: CreditCard },
  { href: "/developer", label: "Developer Console", icon: Code },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-56 border-r border-border bg-[#F8FAFC]">
      <div className="flex h-full flex-col">
        <div className="flex h-16 items-center border-b border-border px-6">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-[15px] font-semibold text-foreground"
          >
            <span className="text-primary">Agent</span>
            <span className="text-foreground">Cloud</span>
          </Link>
        </div>
        <nav className="flex-1 p-4">
          <div className="grid gap-2">
          {nav.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative flex items-center gap-3 rounded-[10px] px-[14px] py-3 text-sm font-medium transition-all duration-200",
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
          })}
          </div>
        </nav>
      </div>
    </aside>
  );
}
