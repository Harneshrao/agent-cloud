"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code,
  Key,
  BarChart3,
  Plus,
  Send,
  Copy,
  Check,
  Trash2,
  X,
} from "lucide-react";
import { PremiumCard } from "@/components/ui/premium-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils";
import {
  createApiKey,
  deleteApiKey as deleteApiKeyRequest,
  fetchApiKeys,
  fetchDeveloperAgents,
  publishDeveloperAgent,
  type ApiKeyMeta,
  type DeveloperAgent,
} from "@/lib/api";

interface ApiKeyRow {
  id: string;
  name: string;
  prefix: string;
  created: string;
  revealed?: string;
}

type ToastKind = "error" | "success";

interface ToastState {
  kind: ToastKind;
  message: string;
}

function useCopyToClipboard() {
  const [copied, setCopied] = useState(false);
  const copy = useCallback((text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, []);
  return { copied, copy };
}

export default function DeveloperConsolePage() {
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishSuccess, setPublishSuccess] = useState(false);
  const [agents, setAgents] = useState<DeveloperAgent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [publishForm, setPublishForm] = useState({
    name: "",
    description: "",
    inputSchema: "",
    outputSchema: "",
    price: "",
  });
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishLoading, setPublishLoading] = useState(false);

  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([]);
  const [apiKeysLoading, setApiKeysLoading] = useState(true);
  const [createKeyName, setCreateKeyName] = useState("");
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const { copied, copy } = useCopyToClipboard();

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setAgentsLoading(true);
        setAgentsError(null);
        const data = await fetchDeveloperAgents();
        if (!cancelled) {
          setAgents(data.agents ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : "Failed to load developer agents";
          setAgentsError(msg);
          setToast({ kind: "error", message: msg });
        }
      } finally {
        if (!cancelled) {
          setAgentsLoading(false);
        }
      }
    };

    const loadKeys = async () => {
      try {
        setApiKeysLoading(true);
        setApiKeyError(null);
        const data = await fetchApiKeys();
        if (!cancelled) {
          const rows: ApiKeyRow[] = (data.api_keys ?? []).map((k: ApiKeyMeta) => ({
            id: String(k.id),
            name: k.name,
            created: k.created_at.slice(0, 10),
            prefix: `•••• ${String(k.id).padStart(4, "0")}`,
          }));
          setApiKeys(rows);
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : "Failed to load API keys";
          setApiKeyError(msg);
          setToast({ kind: "error", message: msg });
        }
      } finally {
        if (!cancelled) {
          setApiKeysLoading(false);
        }
      }
    };

    load();
    loadKeys();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  const handlePublishSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPublishError(null);
    setToast(null);
    const name = publishForm.name.trim();
    if (!name) {
      setPublishError("Agent name is required.");
      return;
    }
    if (publishForm.inputSchema) {
      try {
        JSON.parse(publishForm.inputSchema);
      } catch {
        setPublishError("Input schema must be valid JSON.");
        return;
      }
    }
    if (publishForm.outputSchema) {
      try {
        JSON.parse(publishForm.outputSchema);
      } catch {
        setPublishError("Output schema must be valid JSON.");
        return;
      }
    }
    const price = parseFloat(publishForm.price);
    if (publishForm.price && (Number.isNaN(price) || price < 0)) {
      setPublishError("Price must be a non-negative number.");
      return;
    }
    try {
      setPublishLoading(true);
      await publishDeveloperAgent({
        name,
        description: publishForm.description.trim(),
        input_schema: publishForm.inputSchema ? JSON.parse(publishForm.inputSchema) : undefined,
        output_schema: publishForm.outputSchema ? JSON.parse(publishForm.outputSchema) : undefined,
        pricing: publishForm.price ? price : undefined,
      });
      setPublishSuccess(true);
      setToast({ kind: "success", message: "Agent published successfully." });
      setPublishOpen(false);
      setPublishForm({ name: "", description: "", inputSchema: "", outputSchema: "", price: "" });
      const data = await fetchDeveloperAgents();
      setAgents(data.agents ?? []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to publish agent";
      setPublishError(msg);
      setToast({ kind: "error", message: msg });
    } finally {
      setPublishLoading(false);
      setTimeout(() => setPublishSuccess(false), 4000);
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiKeyError(null);
    setToast(null);
    const name = createKeyName.trim() || "API Key";
    try {
      setApiKeyLoading(true);
      const created = await createApiKey(name);
      const revealed = created.key;
      setNewKeyRevealed(revealed);
      setToast({ kind: "success", message: "API key created." });
      const data = await fetchApiKeys();
      const rows: ApiKeyRow[] = (data.api_keys ?? []).map((k: ApiKeyMeta) => ({
        id: String(k.id),
        name: k.name,
        created: k.created_at.slice(0, 10),
        prefix: `•••• ${String(k.id).padStart(4, "0")}`,
      }));
      setApiKeys(rows);
      setCreateKeyName("");
      setShowCreateKey(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create API key";
      setApiKeyError(msg);
      setToast({ kind: "error", message: msg });
    } finally {
      setApiKeyLoading(false);
    }
  };

  const revokeKey = async (id: string) => {
    setApiKeyError(null);
    setToast(null);
    try {
      await deleteApiKeyRequest(Number(id));
      setApiKeys((prev) => prev.filter((k) => k.id !== id));
      if (newKeyRevealed) setNewKeyRevealed(null);
      setToast({ kind: "success", message: "API key revoked." });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to revoke API key";
      setApiKeyError(msg);
      setToast({ kind: "error", message: msg });
    }
  };

  const publishedCount = agents.length;
  const totalRevenue = agents.reduce((sum, a) => sum + (typeof (a as any).revenue_total === "number" ? (a as any).revenue_total : 0), 0);

  return (
    <div className="space-y-8">
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className={cn(
              "fixed right-6 top-20 z-40 rounded-xl border px-4 py-3 text-sm shadow-soft flex items-center gap-2 max-w-md bg-elevated/90 backdrop-blur",
              toast.kind === "error"
                ? "border-error/40 text-error bg-error/5"
                : "border-success/40 text-success bg-success/5"
            )}
          >
            {toast.kind === "error" ? <X className="h-4 w-4 shrink-0" /> : <Check className="h-4 w-4 shrink-0" />}
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => setToast(null)}
              className="ml-2 text-xs text-foreground-secondary hover:text-foreground"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="text-page-title text-foreground tracking-tight font-semibold">
          Developer Console
        </h1>
        <p className="mt-2 text-body text-foreground-secondary">
          Publish agents, manage API keys, and view analytics.
        </p>
      </motion.div>

      <AnimatePresence>
        {publishSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-xl border border-success/30 bg-success/10 px-4 py-3 text-sm text-success flex items-center gap-2"
          >
            <Check className="h-4 w-4 shrink-0" />
            Agent published successfully. It will appear in the marketplace after review.
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <PremiumCard className="bg-primary-soft/40 border border-primary/20 shadow-[0_1px_2px_rgba(0,0,0,0.03),0_14px_34px_rgba(10,102,194,0.12)]">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-section-title text-foreground flex items-center gap-2 font-semibold text-[18px]">
                  <Code className="h-5 w-5 text-primary" />
                  Publish new agent
                </h2>
                <p className="mt-0.5 text-body text-foreground-secondary">
                  Agent name, description, input/output schema, pricing per run
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => {
                  setPublishOpen((o) => !o);
                  setPublishError(null);
                }}
                className="gap-2 btn-glow shrink-0 shadow-soft"
              >
                <Plus className="h-4 w-4" />
                New agent
              </Button>
            </div>
            <AnimatePresence>
              {publishOpen && (
                <motion.form
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  onSubmit={handlePublishSubmit}
                  className="mt-6 rounded-xl border border-border bg-elevated/50 p-6 space-y-4"
                >
                  {publishError && (
                    <p className="text-sm text-error flex items-center gap-2">
                      <X className="h-4 w-4" />
                      {publishError}
                    </p>
                  )}
                  <div>
                    <label className="text-label text-foreground-secondary block mb-2">
                      Agent name <span className="text-error">*</span>
                    </label>
                    <Input
                      value={publishForm.name}
                      onChange={(e) => setPublishForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="my_agent"
                      className="bg-background border-border"
                    />
                  </div>
                  <div>
                    <label className="text-label text-foreground-secondary block mb-2">
                      Description
                    </label>
                    <Input
                      value={publishForm.description}
                      onChange={(e) => setPublishForm((f) => ({ ...f, description: e.target.value }))}
                      placeholder="Short description"
                      className="bg-background border-border"
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="text-label text-foreground-secondary block mb-2">
                        Input schema (JSON)
                      </label>
                      <textarea
                        value={publishForm.inputSchema}
                        onChange={(e) => setPublishForm((f) => ({ ...f, inputSchema: e.target.value }))}
                        placeholder='{"query": "string"}'
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-body font-mono text-foreground min-h-[80px] focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                        rows={3}
                      />
                    </div>
                    <div>
                      <label className="text-label text-foreground-secondary block mb-2">
                        Output schema (JSON)
                      </label>
                      <textarea
                        value={publishForm.outputSchema}
                        onChange={(e) => setPublishForm((f) => ({ ...f, outputSchema: e.target.value }))}
                        placeholder='{"result": "string"}'
                        className="w-full rounded-xl border border-border bg-background px-3 py-2 text-body font-mono text-foreground min-h-[80px] focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                        rows={3}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-label text-foreground-secondary block mb-2">
                      Price per run (USD)
                    </label>
                    <Input
                      type="number"
                      min={0}
                      step={0.01}
                      value={publishForm.price}
                      onChange={(e) => setPublishForm((f) => ({ ...f, price: e.target.value }))}
                      placeholder="0.00"
                      className="bg-background border-border w-32"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button type="submit" className="gap-2 btn-glow" disabled={publishLoading}>
                      <Send className="h-4 w-4" />
                      {publishLoading ? "Publishing…" : "Publish agent"}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => setPublishOpen(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </motion.form>
              )}
            </AnimatePresence>
          </PremiumCard>

          <PremiumCard className="shadow-soft">
            <h2 className="text-section-title text-foreground flex items-center gap-2 font-semibold">
              <BarChart3 className="h-5 w-5 text-primary" />
              Agent analytics
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              Runs, revenue, success rate
            </p>
            {agentsLoading ? (
              <div className="mt-6 rounded-xl border border-border bg-elevated/30 px-4 py-6 text-sm text-foreground-secondary">
                Loading agent analytics…
              </div>
            ) : agentsError ? (
              <div className="mt-6 rounded-xl border border-error/30 bg-error/5 px-4 py-3 text-sm text-error flex items-center gap-2">
                <X className="h-4 w-4" />
                {agentsError}
              </div>
            ) : publishedCount === 0 ? (
              <EmptyState
                icon={<BarChart3 className="mx-auto text-primary/60" />}
                title="No published agents"
                description="Publish your first agent to start seeing analytics."
              />
            ) : (
              <div className="mt-6 rounded-xl border border-border bg-elevated/30 overflow-hidden">
                <table className="w-full text-body text-left">
                  <thead>
                    <tr className="border-b border-border bg-elevated/50">
                      <th className="text-label text-muted font-semibold px-4 py-3">Agent</th>
                      <th className="text-label text-muted font-semibold px-4 py-3">Runs</th>
                      <th className="text-label text-muted font-semibold px-4 py-3">Revenue</th>
                      <th className="text-label text-muted font-semibold px-4 py-3">Success rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map((agent) => (
                      <tr key={agent.agent_name} className="border-b border-border last:border-0">
                        <td className="px-4 py-3 font-medium text-foreground">{agent.agent_name}</td>
                        <td className="px-4 py-3 text-foreground-secondary">
                          {(agent.runs_per_agent ?? 0).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-foreground-secondary">
                          {"revenue_total" in agent && typeof (agent as any).revenue_total === "number"
                            ? `$${(agent as any).revenue_total.toFixed(2)}`
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-foreground-secondary">
                          {"average_rating" in agent && typeof agent.average_rating === "number"
                            ? `${agent.average_rating.toFixed(2)}★`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </PremiumCard>
        </div>

        <div className="space-y-6">
          <PremiumCard className="shadow-soft">
            <h2 className="text-section-title text-foreground flex items-center gap-2 font-semibold">
              <Key className="h-5 w-5 text-primary" />
              API key management
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              Create and revoke API keys for programmatic access
            </p>
            {newKeyRevealed && (
              <div className="mt-4 rounded-xl border border-primary/30 bg-primary-soft p-4 space-y-2">
                <p className="text-label text-foreground-secondary">Copy your key now. It won’t be shown again.</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 truncate rounded-lg bg-background px-3 py-2 text-sm font-mono text-foreground">
                    {newKeyRevealed}
                  </code>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => copy(newKeyRevealed)}
                    className="gap-1.5 shrink-0"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>
            )}
            {apiKeyError && (
              <div className="mt-4 rounded-xl border border-error/30 bg-error/5 px-3 py-2 text-xs text-error flex items-center gap-2">
                <X className="h-3 w-3" />
                {apiKeyError}
              </div>
            )}
            {!showCreateKey ? (
              <Button
                className="mt-6 w-full gap-2 shadow-soft"
                onClick={() => setShowCreateKey(true)}
              >
                <Key className="h-4 w-4" />
                Create API key
              </Button>
            ) : (
              <form onSubmit={handleCreateApiKey} className="mt-6 space-y-4">
                <div>
                  <label className="text-label text-foreground-secondary block mb-2">Key name</label>
                  <Input
                    value={createKeyName}
                    onChange={(e) => setCreateKeyName(e.target.value)}
                    placeholder="e.g. Production"
                    className="bg-background border-border"
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" className="gap-2 flex-1" disabled={apiKeyLoading}>
                    {apiKeyLoading ? "Creating…" : "Create key"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowCreateKey(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
            {apiKeysLoading ? (
              <div className="mt-6 rounded-xl border border-border bg-elevated/30 px-4 py-4 text-sm text-foreground-secondary">
                Loading API keys…
              </div>
            ) : apiKeys.length > 0 ? (
              <ul className="mt-6 space-y-2">
                {apiKeys.map((k) => (
                  <li
                    key={k.id}
                    className="flex items-center justify-between rounded-lg border border-border bg-elevated/50 px-3 py-2"
                  >
                    <div>
                      <span className="text-sm font-medium text-foreground">{k.name}</span>
                      <span className="ml-2 text-xs text-muted font-mono">{k.prefix}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted hover:text-error"
                      onClick={() => revokeKey(k.id)}
                      aria-label="Revoke key"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            ) : null}
          </PremiumCard>

          <PremiumCard className="shadow-[0_1px_2px_rgba(0,0,0,0.03),0_6px_16px_rgba(0,0,0,0.06)]">
            <h2 className="text-section-title text-foreground flex items-center gap-2 font-semibold">
              <BarChart3 className="h-5 w-5 text-primary" />
              Revenue
            </h2>
            <p className="mt-0.5 text-body text-foreground-secondary">
              Earnings from your agents
            </p>
            <p
              className={cn(
                "mt-6 text-[32px] font-semibold tabular-nums",
                totalRevenue > 0 ? "text-primary" : "text-foreground"
              )}
            >
              ${totalRevenue.toFixed(2)}
            </p>
            <p className="text-label text-muted">
              {totalRevenue > 0 ? "From published agents" : "No revenue yet"}
            </p>
          </PremiumCard>
        </div>
      </div>
    </div>
  );
}
