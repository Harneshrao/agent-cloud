# Billing + usage economics

## Canonical billable units

| Unit | Event type | When recorded |
|------|------------|---------------|
| Task run | `task_enqueued` | After successful enqueue |
| Success | `task_completed` | Worker success |
| Failure | `task_failed` | Worker failure |
| Retry | `task_retry` | Retry scheduled |
| DLQ | `task_dlq` | Max retries exceeded |
| Compute | `execution_ms` | quantity in ms on complete |
| Deployment | `deployment_created` | Deploy activated |
| Storage | `artifact_uploaded` | bytes on upload |
| API | `api_request` | Mutating request (project rate limit middleware) |

Legacy `usage_records` rows still written on complete for backward compatibility.

## Quota enforcement points

| Gate | Function | HTTP |
|------|----------|------|
| Enqueue | `check_enqueue_quota` | 429 `usage_quota_exceeded` |
| Artifact upload | `check_artifact_upload` | 429 |
| New deployment | `check_deployment_quota` | 429 |
| Retry storm | `check_retry_allowed` | Forces DLQ |
| API flood | `ProjectRateLimitMiddleware` | 429 |
| User JWT | `TokenBucketRateLimitMiddleware` | 429 |

## Plans

| Plan | Runs/mo | Exec time | Deployments | Storage | Concurrent |
|------|---------|-----------|-------------|---------|------------|
| Free | 1,000 | 10 min | 5 | 100 MB | 3 |
| Starter | 10,000 | 60 min | 25 | 1 GB | 10 |
| Growth | 100,000 | 600 min | 100 | 10 GB | 50 |

## HTTP

- `GET /billing/summary` — usage + limits + warnings
- `GET /billing/limits`
- `GET /billing/events`
- `GET /billing/usage` — includes legacy aggregates
- `GET /usage` — unchanged compat

## Migration

```bash
alembic upgrade head   # includes h8i9j0k2l3 usage_events
```
