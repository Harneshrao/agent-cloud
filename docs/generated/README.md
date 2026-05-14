# Generated CTO intelligence artifacts

These files are produced by repository scripts (see root `Makefile`):

| File | Command |
|------|---------|
| `repo_inventory.txt` | `make inventory` or `python scripts/repo_inventory.py --out ...` |
| `route_matrix.md` | `make openapi-routes` — requires `DATABASE_URL` + `SKIP_MIGRATION_CHECK=1` for offline import |
| `schema_drift_audit.md` | `make schema-audit` |

Regenerate after major refactors:

```bash
make intelligence
```

On Windows without Make, run the three `python scripts/...` commands from the repo root (PowerShell example):

```powershell
$env:SKIP_MIGRATION_CHECK='1'
$env:DATABASE_URL='postgresql://user:pass@localhost:5432/agent_cloud'
python scripts/repo_inventory.py --out docs/generated/repo_inventory.txt
python scripts/openapi_route_matrix.py --out docs/generated/route_matrix.md
python scripts/schema_drift_audit.py --out docs/generated/schema_drift_audit.md
```
