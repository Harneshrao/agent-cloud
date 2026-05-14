# Docker

Production Dockerfiles live at the **repository root** for historical CI paths:

| File | Service |
|------|---------|
| `Dockerfile.api` | FastAPI (`uvicorn api.main:app` or `uvicorn agent_cloud.app.api.main:app`) |
| `Dockerfile.worker` | Worker process |
| `Dockerfile.scheduler` | Promoter / scheduler |
| `docker-compose.yml` | Local stack |

When switching the API image to the modular app:

```dockerfile
CMD ["uvicorn", "agent_cloud.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
