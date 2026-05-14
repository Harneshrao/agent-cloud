"use client";

import { Search, Bell, UserCircle2 } from "lucide-react";

export function Topbar() {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-6 border-b border-border bg-background/75 px-6 backdrop-blur">
      <div className="relative w-full max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          placeholder="Search agents, workflows…"
          className="h-10 w-full rounded-full border-0 bg-[#EEF3F8] px-10 text-sm text-foreground placeholder:text-foreground-secondary shadow-none outline-none transition duration-200 focus:ring-2 focus:ring-primary/15"
        />
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/60 bg-card text-foreground transition duration-200 hover:bg-card-hover"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-border/60 bg-card px-3 text-sm font-medium text-foreground transition duration-200 hover:bg-card-hover"
          aria-label="Profile"
        >
          <UserCircle2 className="h-5 w-5 text-muted" />
          <span className="hidden sm:inline">Account</span>
        </button>
      </div>
    </header>
  );
}
