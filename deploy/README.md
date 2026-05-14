# Deploy

## Docker Compose

```bash
cp .env.example .env
# Edit POSTGRES_* and secrets
docker compose -f docker-compose.production.yml up --build
```

Scale workers:

```bash
docker compose -f docker-compose.production.yml up --scale worker=4
```

## Kubernetes

```bash
kubectl apply -f deploy/k8s/
```

Edit `02-secret.yaml` and image names in `20-api.yaml`, `21-worker.yaml`, `23-scheduler.yaml` before production.

Recommended for production DB/cache: **managed** PostgreSQL and Redis; keep manifests as reference or use Helm charts.
