#!/bin/sh
set -e
if [ "${SKIP_DB_MIGRATE:-}" != "1" ] && [ -n "${DATABASE_URL:-}" ]; then
  echo "[entrypoint-api] running alembic upgrade head"
  alembic upgrade head
fi
WORKERS="${UVICORN_WORKERS:-4}"
exec uvicorn app.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$WORKERS" \
  --proxy-headers \
  --forwarded-allow-ips "*"
