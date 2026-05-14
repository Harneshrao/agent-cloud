# Agent Cloud — Setup

**Required Python version: 3.11** (e.g. 3.11.9). Python 3.14 causes crashes with uvicorn, multiprocessing, watchfiles, and FastAPI dependencies. The project is locked to Python 3.11 via `pyproject.toml` (`requires-python = ">=3.11,<3.12"`).

## Setup

1. Install **Python 3.11** (e.g. from python.org or `pyenv install 3.11.9`).

2. Run (Windows, from project root):

   ```bat
   setup_env.bat
   ```

   This creates `.venv` with Python 3.11, activates it, upgrades pip, installs pip-tools, and installs dependencies from the locked **`requirements.txt`** (generated from `requirements.in`).

## Start the platform

**Startup command** (from project root):

```bat
py -3.11 run_all.py
```

Or use the batch script:

```bat
start_agent_cloud.bat
```

The script:

1. **Starts the API** (FastAPI on http://localhost:8000).
2. **Waits until the API is reachable** (polls `GET /health`); the dashboard is not started until the API responds.
3. **Starts the worker and scheduler** (task processing).
4. **Starts the dashboard** (Next.js on http://localhost:3000).

This order prevents the login page from showing "Server unavailable." Developers run the platform with one command.

**Backend only:**

```bat
start_backend.bat
```

## Docker development

Run the entire platform (API, Redis, worker, scheduler, dashboard) with one command—no local Python or Node setup required:

```bash
docker compose up --build
```

Then open:

- **API** → http://localhost:8000  
- **API Docs** → http://localhost:8000/docs  
- **Dashboard** → http://localhost:3000  

The dashboard starts only after the API is healthy (`GET /health` returns `{"status":"ok"}`). See `docker-compose.yml` for service definitions and `Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.scheduler`, and `dashboard/Dockerfile` for images.

## Manual / other platforms

- **Linux/macOS:** Create venv with `python3.11 -m venv .venv`, then `source .venv/bin/activate`, `pip install pip-tools`, `pip install -r requirements.txt`. Run `python run_all.py` or `python run_backend.py`.

## Dependencies (pip-tools)

Dependencies are **version-locked** for reproducible builds:

- **`requirements.in`** — top-level dependencies only (edit this to add or change a package).
- **`requirements.txt`** — full lock file with exact versions (generated; do not edit by hand).

**Install** (after activating the venv):

```bash
pip install -r requirements.txt
```

**Upgrade** dependencies and regenerate the lock file:

```bash
pip-compile --upgrade requirements.in
pip install -r requirements.txt
```
- **Without .venv (Windows):** `py -3.11 run_all.py` or `py -3.11 run_backend.py` (requires dependencies installed for that interpreter).

See `dashboard/README_RUN.md` for dashboard and run options.
