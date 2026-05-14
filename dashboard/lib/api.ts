import { refreshAccessToken, clearTokens, getAccessToken } from "@/lib/auth";

const PROJECT_ID = process.env.NEXT_PUBLIC_PROJECT_ID || "1";

/** Environment-driven API base URL (no proxy). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL;
export const API_BASE = API_URL || "http://127.0.0.1:8000";

const HEALTH_CHECK_TIMEOUT_MS = 8000;

/** Check if backend is reachable (GET /health). Uses a timeout to fail fast. */
export async function checkApiHealth(): Promise<boolean> {
  const url = `${API_BASE}/health`;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), HEALTH_CHECK_TIMEOUT_MS);
    const res = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      mode: "cors",
    });
    clearTimeout(timeoutId);
    return res.ok;
  } catch {
    return false;
  }
}

/** Return the API base URL used for health checks (for display in UI). */
export function getApiBaseUrl(): string {
  return API_BASE;
}

function projectHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "X-Project-ID": PROJECT_ID,
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function authHeaders(): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function apiBase(): string {
  return API_BASE;
}

export async function apiFetch<T = unknown>(path: string): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-Project-ID": PROJECT_ID,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error("API error");
  }

  return res.json() as Promise<T>;
}

/** Retry fetch up to 5 times with 2s delay when API is temporarily unavailable (network errors). */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retries = 5
): Promise<Response> {
  try {
    return await fetch(url, options);
  } catch (err) {
    if (retries === 0) throw err;
    await new Promise((r) => setTimeout(r, 2000));
    return fetchWithRetry(url, options, retries - 1);
  }
}

export const SERVER_UNAVAILABLE_MESSAGE =
  "API not reachable.\n\nMake sure backend is running:\n\npy -3.11 run_all.py";

async function fetchApi<T>(path: string, options?: RequestInit, retried = false): Promise<T> {
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string>),
    };
    if (typeof window !== "undefined") {
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetchWithRetry(`${apiBase()}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && !retried && typeof window !== "undefined") {
      try {
        const newToken = await refreshAccessToken();
        const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
        const retryRes = await fetchWithRetry(`${apiBase()}${path}`, { ...options, headers: retryHeaders });
        if (!retryRes.ok) {
          const err = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
          throw new Error((err as { detail?: string }).detail || retryRes.statusText);
        }
        return retryRes.json() as Promise<T>;
      } catch (refreshErr) {
        clearTokens();
        window.location.href = "/login";
        throw refreshErr instanceof Error ? refreshErr : new Error("Session expired");
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((err as { detail?: string }).detail || res.statusText);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    if (e instanceof Error && (e.message === "Failed to fetch" || e.message === "Load failed")) {
      throw new Error(SERVER_UNAVAILABLE_MESSAGE);
    }
    throw e;
  }
}

async function fetchProductApi<T>(path: string, options?: RequestInit, retried = false): Promise<T> {
  try {
    const headers: Record<string, string> = {
      ...(projectHeaders() as Record<string, string>),
      ...(options?.headers as Record<string, string>),
    };
    const res = await fetchWithRetry(`${apiBase()}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && !retried && typeof window !== "undefined") {
      try {
        const newToken = await refreshAccessToken();
        const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
        const retryRes = await fetchWithRetry(`${apiBase()}${path}`, { ...options, headers: retryHeaders });
        if (!retryRes.ok) {
          const err = await retryRes.json().catch(() => ({ detail: retryRes.statusText }));
          throw new Error((err as { detail?: string }).detail || retryRes.statusText);
        }
        return retryRes.json() as Promise<T>;
      } catch (refreshErr) {
        clearTokens();
        window.location.href = "/login";
        throw refreshErr instanceof Error ? refreshErr : new Error("Session expired");
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error((err as { detail?: string }).detail || res.statusText);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    if (e instanceof Error && (e.message === "Failed to fetch" || e.message === "Load failed")) {
      throw new Error(SERVER_UNAVAILABLE_MESSAGE);
    }
    throw e;
  }
}

// System
export async function fetchSystemMetrics() {
  return fetchApi<import("@/types").SystemMetrics>("/system/metrics");
}

export async function fetchSystemWorkers() {
  return fetchApi<{ workers: import("@/types").WorkerInfo[]; count: number }>("/system/workers");
}

export async function fetchSystemQueue() {
  return fetchApi<import("@/types").QueueInfo>("/system/queue");
}

export async function fetchSystemContainers() {
  return fetchApi<import("@/types").ContainerInfo>("/system/containers");
}

// Workflows
export async function fetchWorkflow(taskId: number) {
  return fetchApi<import("@/types").WorkflowView>(`/workflows/${taskId}`);
}

export interface DemoWorkflowResponse {
  workflow_id: number;
}

export async function runDemoWorkflow(): Promise<DemoWorkflowResponse> {
  // Project-scoped endpoint: must include X-Project-ID.
  return fetchProductApi<DemoWorkflowResponse>("/demo/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

// Growth War Room (isolated system)
export interface WarRoomResponse {
  free_layer: {
    opportunities: Array<{ title: string; why_it_matters: string; expected_impact: string }>;
    note: string;
  };
  premium_layer: {
    opportunities: Array<{ title: string; why_it_matters: string; expected_impact: string }>;
    actions: string[];
    weaknesses: string[];
    quick_wins: string[];
  };
}

export async function analyzeWarRoom(input: string): Promise<WarRoomResponse> {
  return fetchApi<WarRoomResponse>("/war-room/analyze", {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

export interface TaskResultResponse {
  task: {
    id: number;
    task_text: string;
    created_at?: string;
  };
  result: unknown;
}

export async function fetchTaskResult(taskId: number): Promise<TaskResultResponse> {
  // Requires project context (Authorization + X-Project-ID)
  return fetchProductApi<TaskResultResponse>(`/task/${taskId}`);
}

export async function fetchTaskStream(taskId: number): Promise<{ events: Array<Record<string, unknown>> }> {
  // Requires project context (Authorization + X-Project-ID)
  return fetchProductApi<{ events: Array<Record<string, unknown>> }>(`/tasks/${taskId}/stream`);
}

// Tasks list (for workflows list) — requires project context
export async function fetchTasks() {
  const data = await fetchProductApi<{
    tasks: import("@/types").TaskListItem[];
    project_id: number;
  }>("/tasks");
  return data.tasks ?? [];
}

// Agents
export async function fetchAgentsStore() {
  return fetchApi<{ agents: import("@/types").AgentStoreItem[] }>("/agents/store");
}

export async function runAgent(body: import("@/types").RunAgentRequest) {
  return fetchApi<import("@/types").RunAgentResponse>("/agents/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Developer console: published agents (per-developer analytics)
export interface DeveloperAgent {
  agent_name: string;
  runs_per_agent: number;
  average_rating?: number | null;
  projects_using_agent?: number | null;
  avg_execution_time_ms?: number | null;
  last_used_at?: string | null;
}

export async function fetchDeveloperAgents(): Promise<{ agents: DeveloperAgent[] }> {
  return fetchApi<{ agents: DeveloperAgent[] }>("/developers/agents");
}

// Developer console: publish agent (metadata only)
export interface PublishDeveloperAgentBody {
  name: string;
  description: string;
  input_schema?: unknown;
  output_schema?: unknown;
  pricing?: number;
}

export async function publishDeveloperAgent(body: PublishDeveloperAgentBody) {
  const price = typeof body.pricing === "number" && body.pricing >= 0 ? body.pricing : 0;
  return fetchApi<{ message: string; agent: unknown }>("/developers/agents", {
    method: "POST",
    body: JSON.stringify({
      agent_name: body.name,
      description: body.description ?? "",
      category: "",
      price_per_run: price,
      currency: "USD",
    }),
  });
}

// Schedules
export async function fetchSchedules() {
  return fetchApi<{ schedules: import("@/types").ScheduleItem[] }>("/schedule");
}

export async function createSchedule(data: {
  agent?: string | null;
  task_text: string;
  cron_expression: string;
  enabled?: boolean;
}) {
  return fetchApi<{ status: string; schedule: import("@/types").ScheduleItem }>("/schedule", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// API keys
export interface ApiKeyMeta {
  id: number;
  name: string;
  created_at: string;
  last_used_at?: string | null;
}

export interface ApiKeysResponse {
  api_keys: ApiKeyMeta[];
  count: number;
}

export async function fetchApiKeys(): Promise<ApiKeysResponse> {
  return fetchApi<ApiKeysResponse>("/api-keys");
}

export async function createApiKey(name: string) {
  return fetchApi<{
    id: number;
    key: string;
    name: string;
    created_at: string;
    message: string;
  }>("/api-keys", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function deleteApiKey(id: number) {
  return fetchApi<{ status: string; id: number }>(`/api-keys/${id}`, {
    method: "DELETE",
  });
}

export async function disableSchedule(scheduleId: number) {
  return fetchApi<{ status: string; id: number }>(`/schedule/${scheduleId}`, {
    method: "DELETE",
  });
}

// Events (optional)
export async function postEvent(body: Record<string, unknown>) {
  return fetchApi<unknown>("/events", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ——— Product layer ———

export async function fetchMarketplaceAgents(params?: {
  category?: string;
  sort?: string;
  min_rating?: number;
  max_price?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.category) sp.set("category", params.category);
  if (params?.sort) sp.set("sort", params.sort);
  if (params?.min_rating != null) sp.set("min_rating", String(params.min_rating));
  if (params?.max_price != null) sp.set("max_price", String(params.max_price));
  const q = sp.toString();
  return fetchProductApi<{ agents: import("@/types").MarketplaceAgent[] }>(
    `/marketplace/agents${q ? `?${q}` : ""}`
  );
}

export async function fetchDashboard() {
  return fetchProductApi<import("@/types").DashboardData>("/dashboard");
}

export async function fetchInstallations() {
  return fetchProductApi<{ installations: import("@/types").Installation[] }>("/agents/installations");
}

export async function installAgent(agentName: string) {
  return fetchProductApi<{ installation: import("@/types").Installation; message: string }>(
    "/agents/installations",
    { method: "POST", body: JSON.stringify({ agent_name: agentName }) }
  );
}

export async function fetchInstallation(installationId: number) {
  return fetchProductApi<import("@/types").Installation>(
    `/agents/installations/${installationId}`
  );
}

export async function updateConfiguration(installationId: number, configuration: Record<string, unknown>) {
  return fetchProductApi<{ installation: import("@/types").Installation; message: string }>(
    `/agents/installations/${installationId}/configuration`,
    { method: "PATCH", body: JSON.stringify({ configuration }) }
  );
}

export async function runInstallation(installationId: number) {
  return fetchProductApi<{ message: string; task_id: number; installation_id: number; agent_name: string }>(
    `/agents/installations/${installationId}/run`,
    { method: "POST" }
  );
}

export async function fetchInstallationRuns(installationId: number, limit = 50, offset = 0) {
  return fetchProductApi<{ runs: import("@/types").AgentRun[] }>(
    `/agents/installations/${installationId}/runs?limit=${limit}&offset=${offset}`
  );
}

export async function fetchInstallationSchedules(installationId: number) {
  return fetchProductApi<{ schedules: import("@/types").AgentSchedule[] }>(
    `/agents/installations/${installationId}/schedules`
  );
}

export async function createInstallationSchedule(
  installationId: number,
  cron_expression: string,
  status = "active"
) {
  return fetchProductApi<{ schedule: import("@/types").AgentSchedule; message: string }>(
    `/agents/installations/${installationId}/schedules`,
    { method: "POST", body: JSON.stringify({ cron_expression, status }) }
  );
}

export async function updateScheduleStatus(scheduleId: number, status: string) {
  return fetchProductApi<{ schedule: import("@/types").AgentSchedule; message: string }>(
    `/agents/installations/schedules/${scheduleId}`,
    { method: "PATCH", body: JSON.stringify({ status }) }
  );
}

// Workflow templates (create = auth, run = project)
export async function createTemplate(body: import("@/types").CreateTemplateRequest) {
  return fetchApi<import("@/types").CreateTemplateResponse>("/templates", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function runTemplate(
  templateId: number,
  body?: import("@/types").RunTemplateRequest
) {
  return fetchProductApi<import("@/types").RunTemplateResponse>(
    `/templates/${templateId}/run`,
    { method: "POST", body: JSON.stringify(body ?? { distributed: true }) }
  );
}

// ——— Auth ———

export interface LoginResponse {
  user: { id: number; email: string; name?: string; created_at?: string; is_admin?: boolean; status?: string };
  access_token?: string;
  token?: string;
  refresh_token?: string;
  token_type?: string;
  expires_in_minutes?: number;
}

export interface RegisterResponse {
  user: { id: number; email: string; name?: string };
  message: string;
}

function isNetworkError(e: unknown): boolean {
  if (e instanceof TypeError && e.message === "Failed to fetch") return true;
  return e instanceof Error && (e.message === "Failed to fetch" || e.message === "Load failed");
}

function normalizeApiDetail(detail: unknown): string {
  if (detail == null) return "Invalid email or password";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    const msg = typeof first === "object" && first && "msg" in first ? (first as { msg: string }).msg : String(first);
    return msg || "Invalid email or password";
  }
  return "Invalid email or password";
}

async function loginWithBase(base: string, email: string, password: string): Promise<LoginResponse> {
  const url = `${base}/auth/login`;
  const res = await fetchWithRetry(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many attempts. Please wait a minute and try again.");
    }
    const detail = (data as { detail?: unknown }).detail;
    throw new Error(normalizeApiDetail(detail));
  }
  return data as LoginResponse;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  try {
    return await loginWithBase(apiBase(), email, password);
  } catch (e) {
    if (isNetworkError(e)) {
      throw new Error(SERVER_UNAVAILABLE_MESSAGE);
    }
    throw e;
  }
}

async function registerWithBase(
  base: string,
  name: string,
  email: string,
  password: string
): Promise<RegisterResponse> {
  const res = await fetchWithRetry(`${base}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Registration failed") as string);
  }
  return data as RegisterResponse;
}

export async function register(name: string, email: string, password: string): Promise<RegisterResponse> {
  try {
    return await registerWithBase(apiBase(), name, email, password);
  } catch (e) {
    if (isNetworkError(e)) {
      throw new Error(SERVER_UNAVAILABLE_MESSAGE);
    }
    throw e;
  }
}

export async function refreshToken(refreshToken: string): Promise<LoginResponse> {
  const res = await fetchWithRetry(`${apiBase()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Session expired") as string);
  }
  return data as LoginResponse;
}

export async function logoutApi(refreshToken: string | null): Promise<void> {
  if (!refreshToken) return;
  await fetchWithRetry(`${apiBase()}/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const res = await fetchWithRetry(`${apiBase()}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Request failed") as string);
  }
  return data as { message: string };
}

export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const res = await fetchWithRetry(`${apiBase()}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: token.trim(), new_password: newPassword }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Reset failed") as string);
  }
  return data as { message: string };
}

export async function sendVerificationEmail(email: string): Promise<{ message: string }> {
  const res = await fetchWithRetry(`${apiBase()}/auth/send-verification-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Request failed") as string);
  }
  return data as { message: string };
}

export async function verifyEmail(token: string): Promise<{ message: string }> {
  const res = await fetchWithRetry(`${apiBase()}/auth/verify-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: token.trim() }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data.detail ?? "Verification failed") as string);
  }
  return data as { message: string };
}
