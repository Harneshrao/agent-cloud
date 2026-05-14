# Deployment operations — Docker & Kubernetes

This document is the operator runbook for the **Agent Execution Cloud** deployment backbone: build images, run Compose locally, roll out to Kubernetes, autoscale workers, and wire observability.

## 1. Build Docker images

From the repository root:

```bash
# Example registry (matches default image names in deploy/kubernetes/*-deployment.yaml)
REGISTRY=ghcr.io/agent-cloud
TAG=latest
docker build -f Dockerfile.api -t ${REGISTRY}/agent-cloud-api:${TAG} .
docker build -f Dockerfile.worker -t ${REGISTRY}/agent-cloud-worker:${TAG} .
docker build -f Dockerfile.scheduler -t ${REGISTRY}/agent-cloud-scheduler:${TAG} .
```

**ASGI entry:** `uvicorn` is launched from `docker/entrypoint-api.sh` (migrations + `app.api.main:app`).  
**Workers:** `python -m app.workers.worker` → full orchestrator in `workers/worker.py`.  
**Scheduler:** `python -m app.workers.scheduler` → `workers.scheduler_runner`.

## 2. Push to a registry

```bash
docker push ${REGISTRY}/agent-cloud-api:${TAG}
docker push ${REGISTRY}/agent-cloud-worker:${TAG}
docker push ${REGISTRY}/agent-cloud-scheduler:${TAG}
```

Use **ECR**, **GCR**, **ACR**, or **Docker Hub** with least-privilege CI roles.

## 3. Local development (Docker Compose)

Full stack (Postgres, Redis, API, workers, scheduler):

```bash
docker compose up --build
```

Optional UI:

```bash
docker compose --profile dashboard up --build
```

Scale workers:

```bash
docker compose up --build --scale worker=4
```

Environment variables are documented in `docker-compose.yml`. Production-style file: `docker-compose.production.yml`.

## 4. Kubernetes — apply order

1. **Namespace & config**

   ```bash
   kubectl apply -f deploy/kubernetes/namespace.yaml
   kubectl apply -f deploy/kubernetes/configmap.yaml
   ```

2. **Secrets** (never commit real values)

   ```bash
   cp deploy/kubernetes/secret.yaml.example secret-live.yaml
   # edit secret-live.yaml → apply, or use external secrets operator
   kubectl apply -f secret-live.yaml
   ```

   Required keys: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` (and any OAuth/SMTP keys your routes need).

3. **Image names** default to `ghcr.io/agent-cloud/agent-cloud-{api,worker,scheduler}:latest`. If you use another registry or tag, edit the `image:` field in each of:

   - `deploy/kubernetes/api-deployment.yaml`
   - `deploy/kubernetes/worker-deployment.yaml`
   - `deploy/kubernetes/scheduler-deployment.yaml`

4. **Workloads**

   ```bash
   kubectl apply -f deploy/kubernetes/api-deployment.yaml
   kubectl apply -f deploy/kubernetes/api-service.yaml
   kubectl apply -f deploy/kubernetes/worker-deployment.yaml
   kubectl apply -f deploy/kubernetes/scheduler-deployment.yaml
   kubectl apply -f deploy/kubernetes/pdb-api.yaml
   ```

5. **Ingress (TLS)**

   - Install **NGINX Ingress** (or cloud LB).
   - Edit `deploy/kubernetes/ingress.yaml` hosts and TLS secret.
   - **cert-manager** recommended for Let’s Encrypt.

   ```bash
   kubectl apply -f deploy/kubernetes/ingress.yaml
   ```

## 5. Autoscaling workers

### Option A — CPU HPA (built-in)

Requires **metrics-server** in the cluster.

```bash
kubectl apply -f deploy/kubernetes/hpa-worker.yaml
```

**Do not** apply `hpa-worker.yaml` and `keda-scaledobject-worker.yaml` for the same Deployment.

### Option B — Queue length (KEDA Redis)

1. Install [KEDA](https://keda.sh).
2. Ensure Redis is reachable from the **KEDA operator** (same VPC / peering / managed endpoint).
3. Edit `deploy/kubernetes/keda-scaledobject-worker.yaml`:

   - `address` — Redis host:port (e.g. `my-redis.cache.amazonaws.com:6379` or in-cluster `agent-cloud-redis.agent-cloud.svc.cluster.local:6379`).
   - `listName` — `queue:ready` (see `config/redis_keys.py`).
   - `listLength` — backlog threshold per scaling decision (tune per SLO).

4. Apply:

   ```bash
   kubectl apply -f deploy/kubernetes/keda-scaledobject-worker.yaml
   ```

Optional in-cluster Redis **only for non-prod**: `deploy/kubernetes/redis-deployment.example.yaml`.

## 6. Postgres & Redis in production

| Component | Recommendation |
|-----------|----------------|
| **Postgres** | AWS RDS, Aurora, Cloud SQL, Azure Database — HA, backups, PITR |
| **Redis** | ElastiCache, Memorystore, Azure Cache — TLS, AUTH, multi-AZ |

Point `DATABASE_URL` and `REDIS_URL` in Kubernetes Secrets at these endpoints. Avoid running single-node Postgres/Redis in production for the main control plane.

## 7. Configuration management

- **ConfigMap** (`deploy/kubernetes/configmap.yaml`): non-secret flags (`SCHEDULER_TICK_SEC`, `UVICORN_WORKERS`, `REDIS_KEY_NAMESPACE`, …).
- **Secrets**: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` — use Sealed Secrets, External Secrets Operator, or cloud secret managers.

## 8. Network & security

- **Ingress:** TLS termination at ingress; optional `nginx` annotations for body size / timeouts (`deploy/kubernetes/ingress.yaml`).
- **NetworkPolicy:** Example in `deploy/kubernetes/network-policy.yaml` — tighten CIDRs and selectors for your CNI.
- **Pods:** Deployments use `runAsNonRoot` / `65532` to match Dockerfiles.

## 9. Logging & monitoring

- **Logs:** Applications log to **stdout/stderr**; ship with Fluent Bit / Fluentd / cloud logging agent.
- **Prometheus:**

  - `deploy/kubernetes/monitoring/servicemonitor-api.yaml` — kube-prometheus-stack (enable after exposing a real `/metrics` endpoint).
  - `deploy/kubernetes/monitoring/prometheus-rules-queue.yaml` — example alert for Redis list length (requires **redis_exporter** or equivalent).

- **Grafana:** dashboards for queue depth, API latency, failure rate, worker CPU — use Prometheus as datasource.

## 10. Verification

```bash
kubectl -n agent-cloud get pods,svc,ingress,hpa
kubectl -n agent-cloud logs deploy/agent-cloud-api -f
kubectl -n agent-cloud logs deploy/agent-cloud-worker -f
```

**Smoke test:** `curl -fsS https://api.example.com/health` (after DNS + TLS).

## 11. Rollout checklist

1. Images built and scanned (Trivy, ECR scanning).
2. Migrations applied (API `entrypoint-api.sh` runs `alembic upgrade head` when `DATABASE_URL` is set).
3. Secrets rotated and not in git.
4. HPA or KEDA configured; **not both** on the same Deployment.
5. Ingress + TLS live; internal services ClusterIP only.
6. Backups and on-call runbooks for Postgres/Redis.
