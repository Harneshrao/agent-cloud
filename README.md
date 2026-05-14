# Agent Cloud

Production agent execution platform (FastAPI · PostgreSQL · Redis · workers).

## Modular layout (`agent_cloud` package)

Canonical layered structure lives under **`agent_cloud/`** — see **[ARCHITECTURE.md](ARCHITECTURE.md)** for dependency rules, diagrams, and the onboarding checklist.

```bash
# Editable install (recommended for imports)
pip install -e .

# API (modular app factory)
uvicorn agent_cloud.app.api.main:app --reload

# Legacy API (unchanged during migration)
uvicorn api.main:app --reload
```

## Docs

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers, import rules, Mermaid diagram |
| [agent_cloud/README.md](agent_cloud/README.md) | Package overview |
| [docs/EXECUTION_PLATFORM.md](docs/EXECUTION_PLATFORM.md) | Queue / Postgres execution model |

## CTO intelligence (inventory, routes, schema drift)

From repo root (requires Python env with project deps):

```bash
make intelligence
```

Or individually: `make inventory`, `make openapi-routes`, `make schema-audit`.  
Artifacts land in [`docs/generated/`](docs/generated/) (see [`docs/generated/README.md`](docs/generated/README.md)).

## Tests

```bash
set PYTHONPATH=%CD%   # Windows
python tests/unit/test_task_service.py
```

## Database

```bash
python scripts/init_db.py
```
