# Agent Cloud Dashboard — How to Run

**Required Python version: 3.11** (3.14 causes crashes with uvicorn/multiprocessing/FastAPI). Use `py -3.11` on Windows.

**Quick start:** From the **project root** run:

```powershell
py -3.11 run_all.py
```

The script:

1. **Starts the API** → http://localhost:8000 (or 8001 if 8000 is in use)  
2. **Waits until the API is reachable** (tries 8000 then 8001)  
3. **Starts the worker and scheduler**  
4. **Starts the dashboard** → http://localhost:3000

Then open **http://localhost:3000** in your browser (Chrome or Edge recommended). Sign-in uses the API via the same-origin proxy; backend error messages (e.g. "Invalid email or password", "Account inactive") are shown correctly.

**Backend only (e.g. for login):**

```powershell
py -3.11 run_backend.py
```

On Windows, reload is disabled by default so the server stays stable when files change. If port 8000 is in use, the API automatically uses **8001** and prints the URLs: **API** `http://127.0.0.1:8001`, **Swagger docs** `http://127.0.0.1:8001/docs`, and the dashboard command. Open the docs on the **same port** the API is running on (8000 or 8001). Or double-click `start_agent_cloud.bat` to run the full stack.

---

## One-time setup

1. **Python 3.11** — Create and use a virtual environment (recommended):
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   Then you can run `python run_all.py` or `python run_backend.py` from the activated venv.

2. **Install frontend dependencies** (from project root):
   ```powershell
   cd dashboard
   npm install
   cd ..
   ```

2. **Environment** — `dashboard/.env.local` is already set with:
   - `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - `NEXT_PUBLIC_PROJECT_ID=1`

3. **Backend (API) must be running** for login and signup to work. If you see "Server unavailable" or "Failed to fetch" on the login/signup page, start the API first (e.g. `python run_all.py` from project root, or `uvicorn api.main:app --reload` in a separate terminal).

4. **Backend (API) must allow anonymous dev** so the dashboard can load without login (when applicable):
   - When you start the API with `py -3.11 run_backend.py` or `py -3.11 run_all.py`, `ALLOW_ANONYMOUS_DEV=1` is set automatically.
   - If you start the API with `py -3.11 -m uvicorn api.main:app --reload`, set it first:
     ```powershell
     $env:ALLOW_ANONYMOUS_DEV="1"
     uvicorn api.main:app --reload
     ```

## Option A: Run everything with one command (recommended)

From the **project root** (`agent-cloud`):

```powershell
py -3.11 run_all.py
```

This starts (in order):

- **API** → http://localhost:8000 (script waits until the API responds at `/health` before continuing)
- **Worker** → task execution  
- **Scheduler** → task assignment  
- **Dashboard** → http://localhost:3000  

Press **Ctrl+C** once to stop all. The dashboard also retries API requests up to 5 times (2 seconds apart) if the API is temporarily unavailable.

---

## Option B: Run each part in its own terminal

### Terminal 1 — API
```powershell
py -3.11 run_backend.py
```
→ http://localhost:8000 | Docs: http://localhost:8000/docs

### Terminal 2 — Worker
```powershell
py -3.11 -m workers.worker
```

### Terminal 3 — Scheduler
```powershell
py -3.11 start_scheduler.py
```

### Terminal 4 — Dashboard
```powershell
cd dashboard
npm run dev
```
→ http://localhost:3000

---

## URLs

| Service   | URL                      |
|----------|---------------------------|
| API      | http://localhost:8000     |
| API Docs | http://localhost:8000/docs |
| Dashboard| http://localhost:3000     |
| Metrics  | http://localhost:8000/system/metrics |
