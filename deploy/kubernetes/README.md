# Kubernetes manifests

| File | Purpose |
|------|---------|
| `namespace.yaml` | Namespace `agent-cloud` |
| `configmap.yaml` | Non-secret config (`UVICORN_WORKERS`, `SCHEDULER_TICK_SEC`, …) |
| `secret.yaml.example` | Template for `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` |
| `api-deployment.yaml` | API pods (2+ replicas) |
| `api-service.yaml` | ClusterIP → port 80 → pod 8000 |
| `worker-deployment.yaml` | Stateless workers |
| `scheduler-deployment.yaml` | Single scheduler replica |
| `ingress.yaml` | NGINX ingress + TLS placeholder |
| `hpa-worker.yaml` | **CPU** autoscaling (requires metrics-server) |
| `keda-scaledobject-worker.yaml` | **Redis queue:ready + CPU** (requires KEDA; **disable** `hpa-worker` when used) |
| `pdb-api.yaml` | Min availability during node drains |
| `network-policy.yaml` | Example API egress/ingress lockdown |
| `redis-deployment.example.yaml` | Optional dev Redis (not for prod) |
| `monitoring/servicemonitor-api.yaml` | Prometheus Operator scrape (needs `/metrics`) |
| `monitoring/prometheus-rules-queue.yaml` | Example queue backlog alert |

Default image registry in the Deployments is **`ghcr.io/agent-cloud/`** (GitHub Container Registry). Override the three `image:` lines if you use ECR, GCR, Docker Hub, or a private registry.

Full procedure: **`docs/DEPLOYMENT_OPERATIONS.md`**.
