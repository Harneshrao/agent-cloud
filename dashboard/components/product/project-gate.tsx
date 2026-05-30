"use client";

import { FolderKanban } from "lucide-react";
import { useActiveProject } from "@/context/active-project";
import { EmptyState } from "@/components/product/empty-state";
import { PlatformAlert } from "@/components/product/platform-alert";
import { PageLoader } from "@/components/product/page-state";

/**
 * Blocks product pages until an active project is selected.
 */
export function ProjectGate({
  children,
  title = "Pick a project to continue",
}: {
  children: React.ReactNode;
  title?: string;
}) {
  const { hasProject, loading, ready, loadError, refreshProjects } = useActiveProject();

  if (loading || !ready) {
    return <PageLoader />;
  }

  if (loadError && !hasProject) {
    return (
      <div className="space-y-4">
        <PlatformAlert error={loadError} onRetry={() => refreshProjects()} />
        <EmptyState
          icon={FolderKanban}
          title={title}
          description="We couldn't confirm your projects while the API was unavailable. Retry above or create a project once the API is back."
          actionLabel="Go to Projects"
          actionHref="/projects"
        />
      </div>
    );
  }

  if (!hasProject) {
    return (
      <EmptyState
        icon={FolderKanban}
        title={title}
        description="Everything you deploy and run lives inside a project. Create one in under a minute — we'll remember it for you."
        why="You won't need to set headers or IDs manually. The dashboard sends project context automatically."
        actionLabel="Create your first project"
        actionHref="/projects"
        secondaryLabel="I already have a project"
        secondaryHref="/projects"
      />
    );
  }

  return <>{children}</>;
}
