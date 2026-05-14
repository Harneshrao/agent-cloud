-- Reference DDL: Agent Execution Platform (PostgreSQL = source of truth)
-- Production: use Alembic migrations (`alembic upgrade head`). This file mirrors the design spec.
-- The `task_status` enum and `tasks` table evolve via migrations; column names in the live DB
-- may still use `input_json` / `output_json` / `retry_count` until a rename migration is added.
--
-- Notes:
-- * `projects` may include extra columns (e.g. user_id) for ownership; core fields below.
-- * `tasks` maps to ORM column names input_json / output_json / retry_count until renamed;
--   reference uses payload/result/retries naming for documentation parity with the spec.

-- ---------------------------------------------------------------------------
-- ENUM: task lifecycle (authoritative in Postgres)
-- ---------------------------------------------------------------------------
-- pending   — created, not yet admitted to a queue
-- queued    — admitted to Redis queue:ready (or waiting promotion)
-- running   — worker claimed (visibility timeout applies in Redis)
-- completed — terminal success
-- failed    — terminal failure (before DLQ)
-- retry     — scheduled for retry (also in Redis queue:retry)
-- dead      — terminal; mirrored in dead_letter_queue
-- workflow_root — DAG root placeholder (not executed as a unit of work)

-- ---------------------------------------------------------------------------
-- TABLE: projects (minimal spec; FK user_id optional in real schema)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- TABLE: tasks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    status            task_status NOT NULL DEFAULT 'pending',
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    result            JSONB,
    retries           INTEGER NOT NULL DEFAULT 0,
    max_retries       INTEGER NOT NULL DEFAULT 3,
    scheduled_at      TIMESTAMPTZ,
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    worker_id         TEXT,
    idempotency_key   TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled ON tasks (scheduled_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency
    ON tasks (idempotency_key) WHERE idempotency_key IS NOT NULL;

-- ---------------------------------------------------------------------------
-- TABLE: task_events (observability / audit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id    UUID NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events (task_id);

-- ---------------------------------------------------------------------------
-- TABLE: dead_letter_queue
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id   UUID NOT NULL REFERENCES tasks (id) ON DELETE CASCADE,
    reason    TEXT NOT NULL,
    payload   JSONB NOT NULL DEFAULT '{}'::jsonb,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dlq_task ON dead_letter_queue (task_id);

-- ---------------------------------------------------------------------------
-- TABLE: rate_limits (optional durable token state; hot path may stay Redis-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rate_limits (
    key         TEXT PRIMARY KEY,
    tokens      INTEGER NOT NULL DEFAULT 0,
    last_refill TIMESTAMPTZ NOT NULL DEFAULT now()
);
