"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Copy, Check } from "lucide-react";
import { createApiKey, fetchApiKeys, deleteApiKey, fetchDeployments } from "@/lib/api";
import { getActiveProjectId } from "@/lib/project";
import { getApiBaseUrl } from "@/lib/api";
import { hasOnboardingStep, markOnboardingStep } from "@/lib/onboarding";
import { ACTIVATION_COPY } from "@/lib/trust-copy";
import { EmptyState } from "@/components/product/empty-state";
import { PlatformAlert } from "@/components/product/platform-alert";
import { ProjectGate } from "@/components/product/project-gate";
import { GlassCard } from "@/components/product/glass-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UserResearchPrompt } from "@/components/product/user-research-prompt";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<Array<{ id: number; name: string; created_at?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("My first key");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [deploymentId, setDeploymentId] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [keysRes, depRes] = await Promise.all([
        fetchApiKeys(),
        fetchDeployments().catch(() => ({ deployments: [] })),
      ]);
      setKeys(keysRes.api_keys ?? []);
      const active = (depRes.deployments ?? []).find((d) => d.status === "active");
      setDeploymentId(active?.deployment_id ?? depRes.deployments?.[0]?.deployment_id ?? "");
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onCreate() {
    setCreating(true);
    setError(null);
    try {
      const res = await createApiKey(name.trim() || "API Key");
      setNewKey(res.key);
      markOnboardingStep("api_key");
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setCreating(false);
    }
  }

  async function onCopy() {
    if (!newKey) return;
    await navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const projectId = getActiveProjectId();
  const apiBase = getApiBaseUrl();
  const depId = deploymentId || "<DEPLOYMENT_ID>";
  const curlExample =
    projectId && newKey
      ? `curl -X POST "${apiBase}/deployments/${depId}/run" \\
  -H "Authorization: Bearer ${newKey}" \\
  -H "X-Project-ID: ${projectId}" \\
  -H "Content-Type: application/json" \\
  -d '{"input":{"message":"hello from curl"}}'`
      : "";

  return (
    <ProjectGate>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">API keys</h1>
          <p className="mt-1 text-neutral-400">{ACTIVATION_COPY.apiKeyContext}</p>
        </div>

        {hasOnboardingStep("viewed_logs") && !hasOnboardingStep("api_key") ? (
          <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-neutral-300">
            You completed a run — create a key below to call the same deployment from your terminal
            or CI.
          </div>
        ) : null}

        {error ? (
          <PlatformAlert error={error} onRetry={() => load()} />
        ) : null}

        {newKey ? (
          <GlassCard className="border-primary/30 bg-primary/5 p-6">
            <p className="text-sm font-medium text-primary">Copy your key now — it won&apos;t be shown again</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <code className="flex-1 break-all rounded-lg bg-black/30 px-3 py-2 text-xs text-foreground">
                {newKey}
              </code>
              <Button type="button" size="sm" variant="outline" onClick={() => onCopy()}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            {curlExample ? (
              <div className="mt-4">
                <p className="text-xs text-neutral-500">
                  Example: run your active deployment from the terminal
                </p>
                <pre className="mt-2 overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-neutral-300">
                  {curlExample}
                </pre>
              </div>
            ) : null}
          </GlassCard>
        ) : null}

        {newKey ? (
          <UserResearchPrompt />
        ) : null}

        <GlassCard className="p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="text-sm font-medium text-foreground">Key name</label>
              <Input
                className="mt-1.5"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. CI pipeline"
              />
            </div>
            <Button type="button" onClick={() => onCreate()} disabled={creating}>
              {creating ? "Creating…" : "Create API key"}
            </Button>
          </div>
        </GlassCard>

        {loading ? (
          <Skeleton className="h-48 rounded-2xl" />
        ) : keys.length === 0 ? (
          <GlassCard>
            <EmptyState
              icon={KeyRound}
              title="No API keys yet"
              description="Create a key above to call the API from curl, GitHub Actions, or your app."
              why="Keys are tied to your account; the active project is sent automatically from the dashboard."
              actionLabel="Create your first key"
              onAction={() => onCreate()}
            />
          </GlassCard>
        ) : (
          <GlassCard className="overflow-hidden">
            <ul className="divide-y divide-white/5">
              {keys.map((k) => (
                <li key={k.id} className="flex items-center justify-between px-6 py-4">
                  <div>
                    <div className="font-medium text-foreground">{k.name}</div>
                    <div className="text-xs text-neutral-500">Created {k.created_at ?? "—"}</div>
                  </div>
                  <button
                    type="button"
                    className="text-sm text-red-400 hover:underline"
                    onClick={async () => {
                      await deleteApiKey(k.id);
                      await load();
                    }}
                  >
                    Revoke
                  </button>
                </li>
              ))}
            </ul>
          </GlassCard>
        )}
      </div>
    </ProjectGate>
  );
}
