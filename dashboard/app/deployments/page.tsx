"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Rocket, Upload, Zap } from "lucide-react";
import {
  deployArtifact,
  deployOnboardingSample,
  fetchDeploymentArtifacts,
  fetchDeployments,
  fetchObservabilityTasks,
  rollbackDeployment,
  runDeployment,
  uploadDeploymentArtifact,
} from "@/lib/api";
import { markOnboardingStep } from "@/lib/onboarding";
import { toPlatformError } from "@/lib/platform-errors";
import type { DeploymentArtifact, DeploymentRecord, TaskListItem } from "@/types";
import { EmptyState } from "@/components/product/empty-state";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PlatformNotice } from "@/components/product/platform-notice";
import { OperationalFootnote } from "@/components/product/operational-footnote";
import { PageLoader } from "@/components/product/page-state";
import { PostDeployPanel } from "@/components/product/post-deploy-panel";
import { DeploymentRow } from "@/components/product/deployment-row";
import { ProjectGate } from "@/components/product/project-gate";
import { GlassCard } from "@/components/product/glass-card";
import { Button } from "@/components/ui/button";
import { usePlatformState } from "@/context/platform-state";
import { SUCCESS_MESSAGES } from "@/lib/trust-copy";
import { taskTraceHref } from "@/lib/trace-navigation";
import { useActiveProject } from "@/context/active-project";

export default function DeploymentsPage() {
  const { projectId } = useActiveProject();
  const { apiReady, checkHealth } = usePlatformState();
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [artifacts, setArtifacts] = useState<DeploymentArtifact[]>([]);
  const [recentTasks, setRecentTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [uploading, setUploading] = useState(false);
  const [sampleLoading, setSampleLoading] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [showPackages, setShowPackages] = useState(false);
  const [rollbackOk, setRollbackOk] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async (bustCache = false) => {
    setError(null);
    try {
      const [d, a, tasks] = await Promise.all([
        fetchDeployments(bustCache),
        fetchDeploymentArtifacts(),
        fetchObservabilityTasks(8).catch(() => ({ tasks: [] as TaskListItem[] })),
      ]);
      setDeployments(d.deployments ?? []);
      setArtifacts(a.artifacts ?? []);
      setRecentTasks(tasks.tasks ?? []);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const sortByRecency = (a: DeploymentRecord, b: DeploymentRecord) =>
    (b.activated_at ?? b.updated_at ?? "").localeCompare(
      a.activated_at ?? a.updated_at ?? ""
    );

  const primaryDeployment = useMemo(() => {
    const active = deployments
      .filter((d) => d.status === "active")
      .sort(sortByRecency);
    if (highlightId) {
      const highlighted = active.find((d) => d.deployment_id === highlightId);
      if (highlighted) return highlighted;
    }
    return active[0] ?? null;
  }, [deployments, highlightId]);

  const otherDeployments = useMemo(() => {
    const primaryId = primaryDeployment?.deployment_id;
    return deployments
      .filter((d) => d.deployment_id !== primaryId)
      .sort((a, b) => {
        const rank = (s: string) => (s === "active" ? 0 : s === "failed" ? 1 : 2);
        const diff = rank(a.status) - rank(b.status);
        if (diff !== 0) return diff;
        return sortByRecency(a, b);
      });
  }, [deployments, primaryDeployment]);

  const hasLiveAgent = deployments.some((d) => d.status === "active");
  const errorView = error ? toPlatformError(error) : null;
  const blockingError = errorView && deployments.length === 0;
  const showConnectivityFootnote = !apiReady && hasLiveAgent;
  const showSoftErrorFootnote =
    errorView && deployments.length > 0 && errorView.kind !== "degraded";

  async function onUpload(file: File) {
    setUploading(true);
    setError(null);
    setRollbackOk(false);
    try {
      const res = await uploadDeploymentArtifact(file);
      const dep = await deployArtifact(res.artifact.artifact_id);
      markOnboardingStep("deployed");
      setHighlightId(dep.deployment?.deployment_id ?? null);
      await load(true);
    } catch (e) {
      setError(e);
    } finally {
      setUploading(false);
    }
  }

  async function onDeploySample(name: "sample_echo" | "sample_fail" | "sample_slow") {
    setSampleLoading(name);
    setError(null);
    setRollbackOk(false);
    try {
      const res = await deployOnboardingSample(name);
      markOnboardingStep("deployed");
      setHighlightId(res.deployment.deployment_id);
      await load(true);
    } catch (e) {
      setError(e);
    } finally {
      setSampleLoading(null);
    }
  }

  async function onRun(depId: string) {
    setActionId(depId);
    setError(null);
    try {
      const res = await runDeployment(depId, { message: "hello from Agent Cloud" });
      markOnboardingStep("ran");
      if (res.task_id) {
        window.location.href = taskTraceHref(res.task_id, projectId);
        return;
      }
      await load();
    } catch (e) {
      setError(e);
      setActionId(null);
    }
  }

  async function onRollback(depId: string) {
    setActionId(depId);
    try {
      await rollbackDeployment(depId);
      setRollbackOk(true);
      await load(true);
    } catch (e) {
      setError(e);
    } finally {
      setActionId(null);
    }
  }

  return (
    <ProjectGate title="Choose a project before deploying">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Deployments</h1>
          <p className="mt-1 max-w-xl text-sm text-neutral-400">
            Ship your agent, run tasks, and follow logs in real time.
          </p>
        </div>

        {blockingError ? (
          <PlatformAlert error={error} onRetry={() => load()} />
        ) : null}

        {loading ? (
          <PageLoader />
        ) : deployments.length === 0 ? (
          <>
            {!apiReady ? (
              <OperationalFootnote onRetry={() => checkHealth().then(() => load())} />
            ) : null}
            <GlassCard className="overflow-hidden">
              <EmptyState
                icon={Rocket}
                title="Deploy your first agent"
                description="Start with our echo sample — one click and your agent goes live. No ZIP required."
                why="Next you'll run a task and see logs in real time."
                actionLabel={
                  sampleLoading === "sample_echo" ? "Deploying…" : "Deploy sample echo agent"
                }
                onAction={() => onDeploySample("sample_echo")}
                secondaryLabel="Upload your own ZIP"
                secondaryHref="#upload"
              />
              <div id="upload" className="border-t border-white/5 px-8 pb-8 pt-4">
                <p className="mb-3 text-center text-sm text-neutral-500">
                  Or package agent.yaml + agent.py as a ZIP
                </p>
                <div className="flex justify-center gap-3">
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".zip"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) onUpload(f);
                      e.target.value = "";
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={uploading}
                    onClick={() => fileRef.current?.click()}
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    {uploading ? "Uploading…" : "Upload ZIP"}
                  </Button>
                </div>
              </div>
            </GlassCard>
          </>
        ) : (
          <>
            {rollbackOk ? (
              <p className="text-xs text-emerald-400/90">{SUCCESS_MESSAGES.rollbackOk}</p>
            ) : null}

            {primaryDeployment ? (
              <PostDeployPanel
                deployment={primaryDeployment}
                recentTasks={recentTasks}
                running={actionId === primaryDeployment.deployment_id}
                onRunFirst={() => onRun(primaryDeployment.deployment_id)}
              />
            ) : null}

            {otherDeployments.length > 0 ? (
              <GlassCard className="overflow-hidden">
                <div className="border-b border-white/5 px-6 py-3">
                  <h3 className="text-sm font-medium text-neutral-300">Previous versions</h3>
                  <p className="text-xs text-neutral-500">Older deployments for this project</p>
                </div>
                <ul className="divide-y divide-white/5">
                  {otherDeployments.map((d) => (
                    <DeploymentRow
                      key={d.deployment_id}
                      deployment={d}
                      allDeployments={deployments}
                      highlighted={d.deployment_id === highlightId}
                      running={actionId === d.deployment_id}
                      onRun={() => onRun(d.deployment_id)}
                      onRollback={() => onRollback(d.deployment_id)}
                    />
                  ))}
                </ul>
              </GlassCard>
            ) : null}

            <details className="group">
              <summary className="flex cursor-pointer list-none items-center gap-2 text-sm text-neutral-500 hover:text-neutral-400">
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                Deploy another version
              </summary>
              <div className="mt-3 flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!!sampleLoading}
                  onClick={() => onDeploySample("sample_echo")}
                >
                  <Zap className="mr-2 h-4 w-4" />
                  {sampleLoading === "sample_echo" ? "Deploying…" : "Deploy sample"}
                </Button>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".zip"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) onUpload(f);
                    e.target.value = "";
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={uploading}
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {uploading ? "Uploading…" : "Upload ZIP"}
                </Button>
              </div>
            </details>

            {artifacts.length > 0 ? (
              <div>
                <button
                  type="button"
                  className="flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-400"
                  onClick={() => setShowPackages((v) => !v)}
                >
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${showPackages ? "rotate-180" : ""}`}
                  />
                  Previous packages ({artifacts.length})
                </button>
                {showPackages ? (
                  <GlassCard className="mt-2 overflow-hidden">
                    <ul className="divide-y divide-white/5">
                      {artifacts.map((a) => (
                        <li key={a.artifact_id} className="px-6 py-3 text-sm text-neutral-400">
                          <span className="text-foreground">{a.agent_name}</span> v{a.version}
                          <span className="ml-2 text-neutral-600">
                            · {a.status === "validated" ? "Ready to deploy" : a.status}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </GlassCard>
                ) : null}
              </div>
            ) : null}

            {showSoftErrorFootnote ? (
              <PlatformNotice error={error} onRetry={() => load()} variant="whisper" />
            ) : null}

            {showConnectivityFootnote ? (
              <OperationalFootnote
                onRetry={() => checkHealth().then(() => load())}
                diagnostic={
                  process.env.NEXT_PUBLIC_DEV_HINTS === "1"
                    ? "API URL should point to port 8000, not the dashboard port."
                    : undefined
                }
              />
            ) : null}
          </>
        )}
      </div>
    </ProjectGate>
  );
}
