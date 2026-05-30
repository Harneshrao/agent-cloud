"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { fetchProjects } from "@/lib/api";
import {
  clearActiveProjectId,
  getActiveProjectId,
  setActiveProjectId,
} from "@/lib/project";
import { markOnboardingStep } from "@/lib/onboarding";
import { toPlatformError } from "@/lib/platform-errors";
import type { PlatformErrorView } from "@/lib/platform-errors";

type Project = { id: string; name: string };

type ActiveProjectContextValue = {
  projectId: string;
  projectName: string;
  projects: Project[];
  loading: boolean;
  ready: boolean;
  hasProject: boolean;
  loadError: PlatformErrorView | null;
  setProject: (id: string) => void;
  refreshProjects: () => Promise<void>;
  ensureProject: () => string | null;
};

const ActiveProjectContext = createContext<ActiveProjectContextValue | null>(null);

function readStoredProjectId(): string {
  if (typeof window === "undefined") return "";
  return getActiveProjectId();
}

export function ActiveProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(readStoredProjectId);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<PlatformErrorView | null>(null);

  const refreshProjects = useCallback(async () => {
    setLoadError(null);
    try {
      const res = await fetchProjects();
      const list = res.projects ?? [];
      setProjects(list);
      const stored = getActiveProjectId();
      const valid = list.find((p) => p.id === stored);
      if (valid) {
        setProjectId(valid.id);
        markOnboardingStep("project");
      } else if (list.length === 1) {
        setActiveProjectId(list[0].id);
        setProjectId(list[0].id);
        markOnboardingStep("project");
      } else if (list.length > 0 && !stored) {
        setActiveProjectId(list[0].id);
        setProjectId(list[0].id);
      } else if (stored && !valid) {
        clearInvalidStoredProject(stored, list);
        setProjectId("");
      } else {
        setProjectId(stored || "");
      }
    } catch (e) {
      setProjects([]);
      const stored = getActiveProjectId();
      setProjectId(stored);
      setLoadError(toPlatformError(e, "Could not load projects"));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      await refreshProjects();
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshProjects]);

  const setProject = useCallback((id: string) => {
    setActiveProjectId(id);
    setProjectId(id);
    markOnboardingStep("project");
    import("@/lib/analytics")
      .then(({ trackProductEvent }) => {
        trackProductEvent("project_selected", { properties: { project_id: id } });
      })
      .catch(() => {});
  }, []);

  const projectName = useMemo(
    () => projects.find((p) => p.id === projectId)?.name ?? "",
    [projects, projectId]
  );

  const ensureProject = useCallback(() => {
    if (projectId) return projectId;
    return null;
  }, [projectId]);

  const value: ActiveProjectContextValue = {
    projectId,
    projectName,
    projects,
    loading,
    ready: !loading,
    hasProject: Boolean(projectId),
    loadError,
    setProject,
    refreshProjects,
    ensureProject,
  };

  return (
    <ActiveProjectContext.Provider value={value}>
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  const ctx = useContext(ActiveProjectContext);
  if (!ctx) {
    throw new Error("useActiveProject must be used within ActiveProjectProvider");
  }
  return ctx;
}
