# Database migrations

Alembic lives at the **repository root** in `alembic/` (historical path).

**Target:** move to `agent_cloud/infra/db/migrations/` by setting `script_location` in `alembic.ini` after coordinating CI/CD.

```bash
alembic upgrade head
```
