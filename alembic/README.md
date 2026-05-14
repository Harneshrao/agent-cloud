# Alembic

- Set `DATABASE_URL` (see `.env.example` or `config.settings`).
- Revisions live in `alembic/versions/`.
- **Schema is owned by Alembic** — run `alembic upgrade head` before starting API/workers. The app does not create tables at runtime.
- Autogenerate: `alembic revision --autogenerate -m "message"` (requires PostgreSQL reachable; metadata from `database.models.Base`).
- Baseline migration `a967d0437c53` creates UUID tables, enums, and seeds the default user/project rows used by `DEFAULT_USER_UUID` / `DEFAULT_PROJECT_UUID`.
