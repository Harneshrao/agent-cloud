# Agent Cloud — Run & Troubleshooting

## Quick start (one command)

From project root:

```powershell
python run_all.py
```

Starts: API (8000), Worker, Scheduler, Dashboard (3000).  
**First time:** run `cd dashboard && npm install && cd ..` once.

---

## If the dashboard shows "Couldn't connect to the server"

1. **API must be running** at http://localhost:8000  
   - Start with: `python run_backend.py` (or `python run_all.py`)  
   - Do **not** start with plain `uvicorn` unless you set:  
     `$env:ALLOW_ANONYMOUS_DEV="1"` then `uvicorn api.main:app --reload`

2. **Anonymous dev must be allowed** (no login for local dashboard)  
   - `run_backend.py` and `run_all.py` set `ALLOW_ANONYMOUS_DEV=1` automatically.  
   - If you start uvicorn yourself, set it first:  
     ```powershell
     $env:ALLOW_ANONYMOUS_DEV="1"
     uvicorn api.main:app --reload
     ```

3. **Dashboard env**  
   - `dashboard/.env.local` should have:  
     `NEXT_PUBLIC_API_URL=http://localhost:8000` and `NEXT_PUBLIC_PROJECT_ID=1`  
   - Restart the dashboard after changing `.env.local`: `cd dashboard && npm run dev`

4. **CORS**  
   - API allows `http://localhost:3000` and `http://127.0.0.1:3000`.  
   - Open the dashboard at one of those URLs.

---

## If marketplace / workflows / tasks fail to load

- Same as above: API running + `ALLOW_ANONYMOUS_DEV=1` + correct `NEXT_PUBLIC_API_URL`.  
- Tasks and dashboard use **product API** (X-Project-ID). Marketplace and dashboard return empty data if the API is down; the UI still loads with fallback data and a Retry button.

---

## URLs

| What       | URL                        |
|-----------|----------------------------|
| API       | http://localhost:8000      |
| API docs  | http://localhost:8000/docs (Swagger) or /redoc (ReDoc) |
| Dashboard | http://localhost:3000      |

---

## Run individual services

| Service   | Command (from project root)        |
|----------|-------------------------------------|
| API      | `python run_backend.py`             |
| Worker   | `python -m workers.worker`          |
| Scheduler| `python start_scheduler.py`         |
| Dashboard| `cd dashboard && npm run dev`      |

---

## Platform stabilization (production readiness)

- **Auth:** Email + password only (no Google OAuth). Tokens in `localStorage`; refresh on 401.
- **Frontend:** Next.js 16 App Router; `"use client"` and `next/navigation` hooks on all client pages.
- **API:** Single base URL via `getApiBase()` / `NEXT_PUBLIC_API_URL`; proxy used on localhost.
- **One command:** `py -3.11 run_all.py` starts API → Worker → Scheduler → Dashboard; API may bind to 8001 if 8000 is in use.
- **Env:** Copy `dashboard/.env.local.example` to `dashboard/.env.local`; copy `.env.example` to `.env` for backend `JWT_SECRET` in production.

---

## Reset authentication (development only)

Old users may have invalid password hashes. To get a **clean database** (no sqlite3 CLI needed, works on Windows):

1. **Stop the platform** (Ctrl+C on `run_all.py`).
2. **Delete the DB** so it is recreated on next start:
   ```powershell
   py -3.11 scripts/reset_dev_db.py
   ```
3. **Start again:** `py -3.11 run_all.py`  
   The backend recreates `agent_cloud.db` in the project root and runs migrations automatically.
4. Open http://localhost:3000/signup, create a new user, then log in.

Database file location: **project root** → `agent_cloud.db` (and `agent_cloud.db-wal`, `agent_cloud.db-shm` when in use).

---

## Deployment

- **Docker:** `docker-compose up --build` starts Redis, API, Worker, Scheduler, Dashboard. Set `JWT_SECRET` (and optional SMTP) via env or `.env`.
- **Build dashboard:** `cd dashboard && npm run build`. Serve with `npm start` or use the dashboard Dockerfile.
- **Ports:** API 8000, Dashboard 3000. If 8000 is in use, run_backend uses 8001 and prints the docs URL; set `API_UPSTREAM` for the dashboard when using 8001.
