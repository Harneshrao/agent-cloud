/**
 * API service layer — re-exports and typed wrappers for backend.
 * Use from components via hooks for loading/error state.
 */

export {
  fetchSystemMetrics,
  fetchSystemWorkers,
  fetchSystemQueue,
  fetchSystemContainers,
  fetchWorkflow,
  fetchTasks,
  fetchAgentsStore,
  runAgent,
  fetchSchedules,
  createSchedule,
  disableSchedule,
  postEvent,
  fetchMarketplaceAgents,
  fetchDashboard,
  fetchInstallations,
  installAgent,
  fetchInstallation,
  updateConfiguration,
  runInstallation,
  fetchInstallationRuns,
  fetchInstallationSchedules,
  createInstallationSchedule,
  updateScheduleStatus,
} from "@/lib/api";
