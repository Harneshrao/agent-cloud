"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { fetchTasks, fetchAgentsStore, fetchSchedules } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Search, GitBranch, Bot, Calendar } from "lucide-react";

type ResultType = "workflow" | "agent" | "schedule";

interface SearchResult {
  id: string;
  type: ResultType;
  label: string;
  subtitle?: string;
  href: string;
}

function fuzzyMatch(query: string, text: string): boolean {
  const q = query.toLowerCase().trim();
  if (!q) return true;
  const t = text.toLowerCase();
  let j = 0;
  for (let i = 0; i < t.length && j < q.length; i++) {
    if (t[i] === q[j]) j++;
  }
  return j === q.length;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(0);

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const [tasksRes, agentsRes, schedulesRes] = await Promise.all([
        fetchTasks().catch(() => []),
        fetchAgentsStore().then((r) => r.agents ?? []).catch(() => []),
        fetchSchedules().then((r) => r.schedules ?? []).catch(() => []),
      ]);
      const tasks = Array.isArray(tasksRes) ? tasksRes : [];
      const agents = Array.isArray(agentsRes) ? agentsRes : [];
      const schedules = Array.isArray(schedulesRes) ? schedulesRes : [];

      const out: SearchResult[] = [];
      tasks.forEach((t) => {
        const label = `Task #${t.id}`;
        const subtitle = typeof t.task_text === "string" ? t.task_text : "";
        if (fuzzyMatch(q, label) || fuzzyMatch(q, subtitle)) {
          out.push({
            id: `task-${t.id}`,
            type: "workflow",
            label,
            subtitle: subtitle.slice(0, 60),
            href: `/workflows/${t.id}`,
          });
        }
      });
      agents.forEach((a) => {
        const label = a.name;
        const sub = [a.description, a.version].filter(Boolean).join(" ");
        if (fuzzyMatch(q, label) || fuzzyMatch(q, sub)) {
          out.push({
            id: `agent-${a.name}-${a.version}`,
            type: "agent",
            label: `${a.name} (v${a.version})`,
            subtitle: a.description?.slice(0, 50),
            href: "/agents",
          });
        }
      });
      schedules.forEach((s) => {
        const label = s.task_text?.slice(0, 40) ?? `Schedule #${s.id}`;
        if (fuzzyMatch(q, label) || fuzzyMatch(q, s.cron_expression ?? "")) {
          out.push({
            id: `schedule-${s.id}`,
            type: "schedule",
            label: label,
            subtitle: s.cron_expression,
            href: "/schedules",
          });
        }
      });
      setResults(out.slice(0, 12));
      setSelected(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => runSearch(query), 200);
    return () => clearTimeout(t);
  }, [query, runSearch]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && results[selected]) {
      e.preventDefault();
      onOpenChange(false);
      router.push(results[selected].href);
    } else if (e.key === "Escape") {
      onOpenChange(false);
    }
  };

  const icon = (r: SearchResult) => {
    if (r.type === "workflow") return <GitBranch className="h-4 w-4 text-neutral-500" />;
    if (r.type === "agent") return <Bot className="h-4 w-4 text-neutral-500" />;
    return <Calendar className="h-4 w-4 text-neutral-500" />;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl p-0 gap-0 overflow-hidden">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <div className="flex items-center border-b border-border px-3">
          <Search className="h-4 w-4 text-neutral-500 shrink-0 mr-2" />
          <Input
            placeholder="Search workflows, agents, schedules…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0 rounded-none bg-transparent"
            autoFocus
          />
        </div>
        <div className="max-h-[60vh] overflow-y-auto">
          {loading ? (
            <div className="py-8 text-center text-sm text-neutral-500">Searching…</div>
          ) : results.length === 0 ? (
            <div className="py-8 text-center text-sm text-neutral-500">
              {query.trim() ? "No results" : "Type to search"}
            </div>
          ) : (
            <ul className="py-2">
              {results.map((r, i) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors",
                      i === selected ? "bg-accent/15 text-foreground" : "text-neutral-300 hover:bg-white/5"
                    )}
                    onMouseEnter={() => setSelected(i)}
                    onClick={() => {
                      onOpenChange(false);
                      router.push(r.href);
                    }}
                  >
                    {icon(r)}
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate">{r.label}</p>
                      {r.subtitle && (
                        <p className="text-xs text-neutral-500 truncate mt-0.5">{r.subtitle}</p>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="border-t border-border px-3 py-2 text-xs text-neutral-500">
          ↑↓ navigate · Enter open · Esc close
        </div>
      </DialogContent>
    </Dialog>
  );
}
