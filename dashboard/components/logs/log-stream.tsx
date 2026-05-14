"use client";

import { useEffect, useRef, useState } from "react";
import { getWorkflowLogStreamUrl } from "@/lib/stream";
import { cn } from "@/lib/utils";
import { Terminal } from "lucide-react";

interface LogStreamProps {
  taskId: number;
  className?: string;
}

export function LogStream({ taskId, className }: LogStreamProps) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const url = getWorkflowLogStreamUrl(taskId);
    setLines([]);
    setError(null);
    try {
      const es = new EventSource(url);
      es.onopen = () => setConnected(true);
      es.onmessage = (event) => {
        try {
          const data = typeof event.data === "string" ? event.data : "";
          setLines((prev) => [...prev.slice(-199), data].filter(Boolean));
        } catch (_) {}
      };
      es.onerror = () => {
        es.close();
        setConnected(false);
        setError("Log stream ended or unavailable");
      };
      return () => es.close();
    } catch (_) {
      setError("Could not connect to log stream");
    }
  }, [taskId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className={cn("flex flex-col rounded-2xl border border-border bg-[#0d0d0d] overflow-hidden", className)}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
        <div className="flex items-center gap-2 text-sm font-medium text-neutral-400">
          <Terminal className="h-4 w-4" />
          Agent logs
          {connected && (
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </div>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </div>
      <div
        ref={containerRef}
        className="h-[240px] overflow-y-auto p-4 font-mono text-xs text-neutral-300 whitespace-pre-wrap break-words"
      >
        {lines.length === 0 && !error && (
          <p className="text-neutral-500">Waiting for logs…</p>
        )}
        {lines.map((line, i) => (
          <div key={i} className="leading-relaxed">
            {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
