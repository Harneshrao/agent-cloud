# Schema drift audit (heuristic)

## Summary counts

| Source | Count |
|--------|------:|
| Alembic-inferred table names | 19 |
| SQLAlchemy `__tablename__` in models.py | 18 |
| `database/*.py` with `_ensure_schema` | 44 |
| Same files containing `CREATE TABLE` string | 0 |

## Alembic vs ORM model names (symmetric difference)

### In Alembic scripts but not in `database/models.py` `__tablename__`

- `task_idempotency`

### In `database/models.py` but not matched in Alembic text scan

_None (under this heuristic)._

## Runtime DDL risk (`CREATE TABLE` string still present)

These `database/*.py` files still contain a `CREATE TABLE` substring. Prefer schema changes via Alembic only; see `tools/strip_runtime_ddl.py`.

_None._

## All `database/*.py` defining `_ensure_schema`

_Total: 44 files._

- `agent_execution_metrics.py`
- `agent_installations.py`
- `agent_installs.py`
- `agent_instances.py`
- `agent_memory.py`
- `agent_messages.py`
- `agent_pricing.py`
- `agent_production_hardening.py`
- `agent_ratings.py`
- `agent_revenue.py`
- `agent_run_results.py`
- `agent_schedules.py`
- `agent_store.py`
- `agent_usage_stats.py`
- `api_keys.py`
- `auth_sessions.py`
- `automation_packages_db.py`
- `autonomous_policies.py`
- `dead_letter.py`
- `developer_accounts.py`
- `developer_economy.py`
- `event_triggers.py`
- `knowledge_graph.py`
- `package_stats.py`
- `plans.py`
- `project_plans.py`
- `prompts_db.py`
- `refresh_tokens.py`
- `regions.py`
- `scheduled_tasks.py`
- `simulation.py`
- `task_graph.py`
- `task_idempotency.py`
- `teams.py`
- `template_installs.py`
- `template_publications.py`
- `template_versions.py`
- `usage_records.py`
- `worker_capabilities.py`
- `workers.py`
- `workflow_analytics.py`
- `workflow_checkpoints.py`
- `workflow_nodes.py`
- `workflow_templates.py`

## Limitations

- Alembic table extraction misses dynamic names and `op.rename` / raw SQL edge cases.
- Many tables exist only in raw `database/*.py` SQL strings; compare to `infra/postgres/schema.sql` manually.
- This script does not connect to a live database.

