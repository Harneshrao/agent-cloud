# Phase 1 — Route parity (legacy + modular)

## Mechanism

- **`api.main:app`** remains the canonical ASGI application for all legacy paths.
- **`agent_cloud.app.api.main:app`** returns the **same** `api.main` application object (no duplicate route registration).
- **`/v1/*`** modular routes are mounted once on that app from `api/main.py` via `app.include_router(..., prefix="/v1")`.

## Parity matrix

| Entrypoint | Paths |
|------------|--------|
| `uvicorn api.main:app` | `/`, `/health`, all legacy routers, **`/v1/...`** |
| `uvicorn agent_cloud.app.api.main:app` | **Identical** ASGI graph |

## Report generation

```powershell
python scripts/openapi_route_matrix.py --json-out docs/migration/_parity_legacy.json --out NUL
python scripts/openapi_route_matrix.py --app agent_cloud.app.api.main:app --json-out docs/migration/_parity_unified.json --out NUL
```

Compare `routes` arrays in the two JSON files; counts should match when both resolve to the same app (same process).
