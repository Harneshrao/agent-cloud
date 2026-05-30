"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { analyzeWarRoom, type WarRoomResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function WarRoomPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<WarRoomResponse | null>(null);

  const canAnalyze = useMemo(() => input.trim().length > 0 && !loading, [input, loading]);

  const run = async () => {
    const text = input.trim();
    if (!text) return;
    setError(null);
    setLoading(true);
    try {
      const res = await analyzeWarRoom(text);
      setData(res);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div className="page-title">Growth War Room</div>
        <div className="page-subtitle">
          Fast, structured growth insights for a competitor, product, or URL description.
        </div>
      </div>

      <Card className="p-6">
        <div className="text-sm font-medium text-foreground">Input</div>
        <div className="mt-2 text-sm text-foreground-secondary">
          Paste a URL description, competitor notes, or product positioning.
        </div>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Competitor landing page for AI agents targeting SMBs. Pricing is unclear, signup is long."
          className="mt-4 w-full min-h-[120px] rounded-xl border border-border bg-background px-3 py-2 text-body text-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        />
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={!canAnalyze} className="min-w-[120px]">
            {loading ? "Analyzing…" : "Analyze"}
          </Button>
          {error && <div className="text-sm text-error">{error}</div>}
        </div>
      </Card>

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-6">
            <div className="text-[18px] font-medium text-foreground">Free insights</div>
            <div className="mt-1 text-sm text-foreground-secondary">
              Two high-impact opportunities to act on immediately.
            </div>
            <div className="mt-5 space-y-3">
              {data.free_layer.opportunities.map((o, idx) => (
                <div key={idx} className="rounded-xl border border-border bg-elevated/30 p-4">
                  <div className="text-sm font-semibold text-foreground">{o.title}</div>
                  <div className="mt-1 text-sm text-foreground-secondary">{o.why_it_matters}</div>
                  <div className="mt-2 text-xs text-foreground-secondary">
                    Expected impact: <span className="text-foreground">{o.expected_impact}</span>
                  </div>
                </div>
              ))}
              <div className="text-xs text-foreground-secondary">{data.free_layer.note}</div>
            </div>
          </Card>

          <Card className="p-6 relative overflow-hidden">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[18px] font-medium text-foreground">Premium layer</div>
                <div className="mt-1 text-sm text-foreground-secondary">
                  Full opportunity set, actions, weaknesses, and quick wins.
                </div>
              </div>
              <div className="text-xs rounded-full border border-border bg-elevated px-3 py-1 text-foreground-secondary">
                Locked
              </div>
            </div>

            <div className={cn("mt-5 space-y-4", "blur-[7px] select-none pointer-events-none")}>
              <div className="space-y-2">
                <div className="text-sm font-semibold text-foreground">Opportunities</div>
                <ul className="space-y-2">
                  {data.premium_layer.opportunities.map((o, idx) => (
                    <li key={idx} className="rounded-xl border border-border bg-elevated/30 p-3">
                      <div className="text-sm font-medium text-foreground">{o.title}</div>
                      <div className="text-xs text-foreground-secondary mt-1">{o.why_it_matters}</div>
                      <div className="text-xs text-foreground-secondary mt-2">
                        Impact: <span className="text-foreground">{o.expected_impact}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <div className="text-sm font-semibold text-foreground mb-2">Actions</div>
                  <ul className="space-y-1 text-sm text-foreground-secondary">
                    {data.premium_layer.actions.map((a, idx) => (
                      <li key={idx}>- {a}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground mb-2">Quick wins</div>
                  <ul className="space-y-1 text-sm text-foreground-secondary">
                    {data.premium_layer.quick_wins.map((a, idx) => (
                      <li key={idx}>- {a}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-foreground mb-2">Weaknesses</div>
                <ul className="space-y-1 text-sm text-foreground-secondary">
                  {data.premium_layer.weaknesses.map((w, idx) => (
                    <li key={idx}>- {w}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="absolute inset-x-0 bottom-0 p-5">
              <div className="rounded-xl border border-border bg-background/85 backdrop-blur px-4 py-3 text-sm text-foreground-secondary">
                Upgrade to unlock the full War Room playbook.
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

