# Local dev health check

Before every alpha test or long dev session, answer within seconds:

**Is the platform actually healthy, or is local dev lying to me?**

---

## Quick commands

| Command | Purpose |
|---------|---------|
| `py -3.11 scripts/dev_doctor.py` | Pre-flight: Postgres, Redis, API, dashboard, worker, project |
| `py -3.11 scripts/dev_doctor.py --deep` | Above + API component probes (`/health?deep=1`) |
| `py -3.11 scripts/dev_doctor.py --readiness` | **Alpha tester gate** — E2E deploy → run → trace → API keys |
| `py -3.11 scripts/dev_doctor.py --clean` | Kill **hung** dashboard Node processes on port 3000 |

Makefile equivalents (Git Bash on Windows):

```bash
make doctor
make readiness
make clean-stale
```

---

## Startup (canonical)

```bash
# 1. Infrastructure (once per machine session)
docker compose up -d postgres redis

# 2. Migrations (after pull or schema change)
alembic upgrade head

# 3. Full stack
py -3.11 run_all.py
```

`run_all.py` now:

- Warns about **stale/hung processes** before boot
- Waits for API, then worker/scheduler, then dashboard (with timeout)
- Prints a **startup health summary** (Postgres, Redis, workers, schema, dashboard)

---

## Expected curl responses

### API shallow health (fast, no DB)

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

### API deep health (component probes, ≤8s)

```bash
curl -s "http://127.0.0.1:8000/health?deep=1"
# {"status":"ok","components":{"postgres":"ok","redis":"ok","workers":"ok","schema":"ok"}}
# or status "degraded" with component detail strings
```

### Dashboard (must respond within ~5s)

```bash
curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
# 200 or 307 — NOT hang / timeout
```

---

## Interpreting doctor output

```
  [PASS] Postgres — ok
  [FAIL] Dashboard — HUNG — no response in 5s (PIDs: 25288)
         → py -3.11 scripts/dev_doctor.py --clean
```

| Result | Meaning |
|--------|---------|
| **PASS** | Component healthy |
| **FAIL** | Fix before alpha testing |
| **WARN** (stale processes) | Port occupied or hung — often **not** a product bug |

---

## Common failures

### Dashboard accepts connection but curl hangs

**Symptom:** API 200, dashboard timeout after minutes, many `CLOSE_WAIT` on :3000.

**Cause:** Stale Next.js / Node dev server.

**Fix:**

```bash
py -3.11 scripts/dev_doctor.py --clean
py -3.11 run_all.py
# or: cd dashboard && npm run dev
```

### Port 3000 already in use

**Symptom:** `EADDRINUSE` when starting dashboard.

**Fix:** Same as above — `--clean` or manually `taskkill /PID <pid> /F` (Windows).

### Port 8000 already in use

**Symptom:** API binds to 8001 or fails to start.

**Fix:** Stop old API process or use the port `run_all.py` reports. Set `NEXT_PUBLIC_API_URL` to match.

### Worker heartbeat FAIL

**Symptom:** Tasks stay `queued`; doctor shows `no heartbeat in last 60s`.

**Fix:** Ensure `run_all.py` worker started, or run `py -3.11 -m workers.canonical_worker`.

### Postgres / Redis FAIL

**Fix:**

```bash
docker compose up -d postgres redis
docker compose ps
```

Check `.env` — default local Postgres is `localhost:5433`.

### API keys FAIL on readiness

**Cause:** Missing `api_keys` table (migrations not applied).

**Fix:** `alembic upgrade head`

---

## Restart flow

1. Ctrl+C in `run_all.py` terminal (stops all child processes)
2. If dashboard still hung: `py -3.11 scripts/dev_doctor.py --clean`
3. `py -3.11 run_all.py`
4. `py -3.11 scripts/dev_doctor.py --readiness`

---

## Before every alpha tester

```bash
py -3.11 scripts/dev_doctor.py --readiness
```

Must print:

```
  READY FOR TESTER
```

If `BLOCKED`, do **not** send the invite until fixed.

---

## Related docs

- [DEV_RECOVERY.md](runbooks/DEV_RECOVERY.md) — incident playbooks
- [ALPHA_TEST_INVITE.md](ALPHA_TEST_INVITE.md) — tester script
- [ALPHA_PRIVATE.md](ALPHA_PRIVATE.md) — alpha checklist
