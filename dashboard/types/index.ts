export interface SystemMetrics {
  queue_length: number;
  workers_active: number;
  containers_idle: number;
  containers_busy: number;
  tasks_running: number;
  tasks_failed_last_hour: number;
}

export interface WorkerInfo {
  worker_id: string;
  last_seen: string | null;
  tasks_running: number;
  status: string;
}

export interface QueueInfo {
  queue_key: string;
  queue_length: number;
}

export interface ContainerInfo {
  containers_idle: number;
  containers_busy: number;
  idle_ids: string[];
  busy_ids: string[];
}

export interface WorkflowView {
  task_id: number;
  task_text: string | null;
  status: string;
  parent_task_id: number | null;
  retry_count: number;
  child_tasks: Array<{
    task_id: number;
    task_text: string | null;
    status: string;
    retry_count: number;
    node_id?: string;
    output?: unknown;
    logs?: Array<Record<string, unknown>>;
  }>;
}

export interface TaskListItem {
  task_id: string;
  status?: string;
  retry_count?: number;
  worker_id?: string | null;
  created_at?: string;
  agent?: string;
  deployment_id?: string;
}

export interface TaskTrace {
  task: Record<string, unknown>;
  events: Array<{
    event_id: string;
    event_type: string;
    payload: Record<string, unknown>;
    created_at?: string;
  }>;
  logs: Array<Record<string, unknown>>;
  lifecycle_complete?: boolean;
  expected_phases?: string[];
}

export interface DlqItem {
  task_id: string;
  error?: string;
  retry_count?: number;
  agent_name?: string;
  created_at?: string;
  task_payload?: string;
}

export interface IncidentItem {
  severity: string;
  code: string;
  message: string;
}

export interface AgentStoreItem {
  id: number;
  name: string;
  description: string;
  version: string;
  capabilities: string[];
  author?: string;
  price?: number;
  created_at?: string;
}

export interface ScheduleItem {
  id: number;
  agent: string | null;
  task_text: string;
  cron_expression: string;
  enabled: boolean;
  created_at?: string;
  last_run_at?: string | null;
}

export interface RunAgentRequest {
  agent: string;
  task: string;
}

export interface RunAgentResponse {
  status: string;
  task_id?: number;
  agent?: string;
  task?: string;
}

// ——— Product layer (marketplace, installations, runs) ———

export interface MarketplaceAgent {
  agent_name: string;
  description: string;
  developer: string;
  developer_verified?: boolean;
  version?: string;
  rating: number | null;
  price_per_run: number;
  currency: string;
  input_schema: Record<string, { type?: string; default?: unknown; required?: boolean }>;
  example_output: unknown;
  capabilities: string[];
  popularity?: number;
  install_count?: number;
}

export interface DeploymentArtifact {
  artifact_id: string;
  project_id: string;
  agent_name: string;
  version: string;
  status: string;
  checksum_sha256: string;
  created_at?: string;
}

export interface DeploymentRecord {
  deployment_id: string;
  project_id: string;
  artifact_id: string;
  agent_name: string;
  version: string;
  status: string;
  configuration?: Record<string, unknown>;
  activated_at?: string | null;
  updated_at?: string;
}

export interface Installation {
  installation_id: number;
  project_id: number;
  agent_name: string;
  configuration: Record<string, unknown>;
  installed_at: string;
  status: string;
  input_schema?: Record<string, unknown>;
  price_per_run?: number;
  currency?: string;
}

export interface AgentRun {
  run_id: number;
  installation_id: number;
  task_id: number;
  status: string;
  output: unknown;
  execution_time_ms: number;
  created_at: string;
}

export interface AgentSchedule {
  schedule_id: number;
  installation_id: number;
  cron_expression: string;
  status: string;
  created_at: string;
  last_run_at: string | null;
}

/** DAG node for workflow templates: id, agent, task, optional deps (prerequisite node ids). */
export interface DagNode {
  id: string;
  agent: string;
  task: string;
  deps?: string[];
}

export interface DagDefinition {
  nodes: DagNode[];
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  dag_definition: DagDefinition;
  input_schema?: Record<string, unknown>;
  visibility?: string;
}

export interface CreateTemplateResponse {
  status: string;
  template: { id: number; name: string; dag_definition: DagDefinition; [key: string]: unknown };
}

export interface RunTemplateRequest {
  task_override?: string | null;
  version?: string | null;
  inputs?: Record<string, unknown>;
  distributed?: boolean;
}

export interface RunTemplateResponse {
  status: string;
  template_id: number;
  project_id: number;
  workflow_id?: number;
  root_task_ids?: number[];
  task_ids?: number[];
}

export interface DashboardData {
  project_id: number;
  installations: Installation[];
  recent_runs: Array<{
    installation_id: number;
    agent_name: string;
    run_id: number;
    task_id: number;
    status: string;
    execution_time_ms: number;
    created_at: string;
  }>;
  runs_today: number;
  cost_today: number;
  monthly_usage: { runs_this_month: number; execution_time_this_month_ms: number };
  total_runs: number;
  total_agent_cost: number;
  runs_per_agent: Array<{
    agent_name: string;
    runs: number;
    total_agent_cost: number;
    cost_per_run?: number;
    currency?: string;
  }>;
}
