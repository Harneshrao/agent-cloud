# Observability — canonical operational visibility

## Architecture

| Layer | Canonical | Purpose |
|-------|-----------|---------|
| **Trace events** | `task_events` (Postgres) | Ordered lifecycle: enqueued → dequeued → claimed → execute_* → retry/dlq |
| **Durable logs** | `task_logs` (Postgres JSON rows) | Machine-queryable operational records |
| **Stdout** | `operational_log` / `JsonFormatter` | Process logs with full correlation fields |
| **Live stream** | `engine/stream_store` | In-memory agent progress (ephemeral) |
| **Metrics** | `agent_cloud.infra.observability.metrics` | Counters/gauges (Prometheus-ready) |
| **Queue** | `database/task_observability.queue_snapshot` | Redis depths + stale visibility |
| **DLQ** | `dead_letter_tasks` + `/observability/dlq` | Project-filtered failures |
| **Deployments** | `deployment_events` + `/observability/deployments/{id}/timeline` | Rollout history |
| **Incidents** | `/observability/incidents` | Rule-based hints (backlog, failure rate, alerts) |

## Canonical log / event fields

When known, every operational record includes:

`timestamp`, `trace_id`, `execution_id`, `task_id`, `project_id`, `deployment_id`, `worker_id`, `queue_name`, `retry_count`, `runtime_version`, `severity`, `event_type`, `message`

## HTTP API (project-scoped, no admin)

Prefix: `/observability`

| Path | Description |
|------|-------------|
| `GET /health` | Platform + project stats + queue |
| `GET /queue` | Queue depths |
| `GET /workers` | Worker registry |
| `GET /tasks` | Recent tasks |
| `GET /tasks/{id}/trace` | Full lifecycle |
| `GET /tasks/{id}/logs` | Durable logs |
| `GET /dlq` | Project DLQ |
| `GET /incidents` | Active incident hints |
| `GET /deployments/{id}/timeline` | Deployment + events + related tasks |

Admin-only detail remains under `/system/*`.

## Dashboard

- `/tasks/{taskId}` — Task trace
- `/dlq` — Dead letters
- `/workers` — Workers + queue cards
- `/runs` — Links to task traces
- `/system` — Legacy system view (uses observability where possible)

## Retention (recommended)

| Store | P0 | At scale |
|-------|-----|----------|
| `task_events` | 30 days | Partition by month; archive to cold storage |
| `task_logs` | 14 days | Aggregate older to object storage |
| `stream_store` | Process lifetime | Not durable |

At **10M events/day**, index `(task_id, created_at)` and avoid full table scans on dashboard home.
