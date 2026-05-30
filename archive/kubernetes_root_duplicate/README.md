# Kubernetes Worker Fleet

Run agent-cloud workers as Kubernetes pods with optional auto-scaling.

## Step 1 — Worker deployment

- **worker-configmap.yaml** — ConfigMap with env: `WORKER_REGION`, `WORKER_CAPABILITIES`, `SCHEDULER_URL`, `REDIS_URL`.
- **worker-deployment.yaml** — Deployment that runs `python -m workers.worker` with env from the ConfigMap.
- **Dockerfile.worker** (repo root) — Build worker image:  
  `docker build -f Dockerfile.worker -t agent-cloud-worker:latest .`

Apply:

```bash
kubectl apply -f worker-configmap.yaml
kubectl apply -f worker-deployment.yaml
```

Override per region by creating another ConfigMap (e.g. `worker-config-eu` with `WORKER_REGION=eu`) and setting `envFrom.configMapRef.name` in the deployment or using a separate Deployment per region.

## Step 2 — Auto scaling

- **worker-hpa.yaml** — HorizontalPodAutoscaler (HPA) on the worker Deployment:
  - **CPU**: target 70% average utilization; scale up/down between 2–20 replicas.
  - **Memory**: target 80% (optional).
  - **Behavior**: scale up quickly (up to +100% or +2 pods per 30s), scale down gradually (stabilization 120s, up to 25% per 60s).

Apply:

```bash
kubectl apply -f worker-hpa.yaml
```

### Queue / backlog based scaling

HPA above uses resource (CPU/memory) metrics. To scale on **queue length** or **task backlog**:

1. **Custom metrics API**  
   Expose queue length (e.g. from platform `GET /system/metrics` or Redis `LLEN tasks_queue`) as a custom metric and configure HPA v2 to use it, e.g.:

   ```yaml
   metrics:
     - type: External
       external:
         metric:
           name: queue_length
           selector: { queue: tasks_queue }
         target:
           type: AverageValue
           averageValue: "5"
   ```

2. **CronJob / script**  
   Use the provided script or CronJob:
   - **scale-by-queue.py** — Fetches `GET /system/metrics`, computes `replicas = clamp(ceil(queue_length / TASKS_PER_WORKER), MIN_REPLICAS, MAX_REPLICAS)`, and runs `kubectl scale deployment/agent-cloud-worker --replicas=N`. Set `PLATFORM_URL`, `MIN_REPLICAS`, `MAX_REPLICAS`, `TASKS_PER_WORKER` (defaults: 2, 20, 5). Run from a pod with `kubectl` and network to the platform, or from CI.
   - **queue-scaler-cronjob.yaml** — Example CronJob that calls the platform metrics endpoint; for production, use an image that includes both `curl` and `kubectl` and add the scale command, or run `scale-by-queue.py` in the job.

Worker utilization is reflected in CPU/memory usage that HPA uses; for backlog-driven scaling, queue length is the main input.

## Step 3 — Cluster registration

Workers **register with the platform on startup** using the existing worker registry:

- On pod start, the worker process runs `register_worker(worker_id, region=worker_region)` and, if set, `set_capabilities(worker_id, worker_capabilities)`.
- `WORKER_REGION` and `WORKER_CAPABILITIES` from the ConfigMap are read from the environment and used for registration and for task requests to the scheduler.
- Heartbeats are sent periodically so the platform sees workers as active; no extra “cluster registration” step is required.

Ensure the platform API (and Redis/DB) are reachable from the cluster (e.g. `SCHEDULER_URL` and `REDIS_URL` point to in-cluster or ingress URLs).

## Summary

| Item              | Purpose |
|-------------------|--------|
| Worker Deployment | Runs workers with `WORKER_REGION`, `WORKER_CAPABILITIES`, `SCHEDULER_URL` (and optional `REDIS_URL`) from ConfigMap. |
| HPA               | Scales 2–20 replicas by CPU (and optionally memory). |
| Queue-based scale | Use custom metrics or a scaling job that calls the platform and runs `kubectl scale`. |
| Registration      | Handled by the worker process on startup via the existing registry. |
