# Dev incident recovery playbooks

Local-only incidents that mimic product failures. Use with `py -3.11 scripts/dev_doctor.py`.

---

## Dashboard hanging

### What happened

Browser or `curl http://localhost:3000` hangs. API may still return 200. Alpha tester sees blank/spinning UI.

### Likely cause

- Stale Next.js dev server (orphaned `node.exe`)
- Many `CLOSE_WAIT` sockets on port 3000
- Partial crash without process exit

### Recovery

```bash
py -3.11 scripts/dev_doctor.py --clean
cd dashboard && npm run dev
# or full stack:
py -3.11 run_all.py
```

### Verify

```bash
curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3000/
py -3.11 scripts/dev_doctor.py
```

---

## API boot failure

### What happened

`run_all.py` stuck on “Waiting for API”, or `/health` connection refused.

### Likely cause

- Python not 3.11
- Missing deps (`pip install -r requirements.txt`)
- Port 8000 held by dead process
- `DATABASE_URL` unset

### Recovery

```bash
py -3.11 run_backend.py   # read error in terminal
# Kill stale API PID if port conflict:
py -3.11 scripts/dev_doctor.py --deep
taskkill /PID <pid> /F    # Windows
py -3.11 run_all.py
```

### Verify

```bash
curl -s http://127.0.0.1:8000/health
curl -s "http://127.0.0.1:8000/health?deep=1"
```

---

## Redis unavailable

### What happened

Doctor: `Redis — connection refused`. Tasks may not dequeue.

### Likely cause

Docker Redis not running, wrong `REDIS_URL`.

### Recovery

```bash
docker compose up -d redis
docker compose ps redis
```

### Verify

```bash
py -3.11 scripts/dev_doctor.py --deep
# components.redis == ok
```

---

## Postgres unavailable

### What happened

Doctor: `Postgres — connection refused`. API may crash on boot.

### Likely cause

Docker Postgres not running. Wrong port (local default **5433**, not 5432).

### Recovery

```bash
docker compose up -d postgres
alembic upgrade head
```

### Verify

```bash
py -3.11 scripts/dev_doctor.py
```

---

## Worker stale / no heartbeat

### What happened

Deploy works, **Run task** queues forever or 500. Doctor: `Worker heartbeat — no heartbeat in last 60s`.

### Likely cause

- Worker not started (`run_all.py` worker crashed)
- `workers` table missing
- Worker crash loop

### Recovery

```bash
py -3.11 -m workers.canonical_worker
# or restart full stack:
py -3.11 run_all.py
```

### Verify

```bash
curl -s "http://127.0.0.1:8000/health?deep=1" | findstr workers
py -3.11 scripts/dev_doctor.py --readiness
```

---

## Migrations missing

### What happened

500 on API keys, run, or deploy. Deep health: `schema — missing tables: api_keys`.

### Likely cause

DB created before Alembic migrations applied.

### Recovery

```bash
alembic upgrade head
py -3.11 scripts/dev_doctor.py --deep
```

### Verify

Readiness check passes `API key create`.

---

## False “product broken” checklist

Before debugging onboarding UX, confirm:

- [ ] `py -3.11 scripts/dev_doctor.py` → OVERALL PASS
- [ ] Dashboard curl returns in <5s
- [ ] `--readiness` → READY FOR TESTER

If doctor PASS but UI broken → likely frontend bug.  
If doctor FAIL → fix local infra first.
