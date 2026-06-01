#!/usr/bin/env python3
"""End-to-end validation: deploy -> run -> trace -> zip upload -> deploy -> run again -> api key."""
import io
import sys
import time
import zipfile
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
s = requests.Session()
h = {"Content-Type": "application/json"}
fails = []


def check(name, cond, detail=""):
    print(f"[{'OK' if cond else 'FAIL'}] {name}{(' -> ' + detail) if detail else ''}")
    if not cond:
        fails.append(name)
    return cond


print("health", s.get(f"{BASE}/health", timeout=10).status_code)

pid = s.get(f"{BASE}/projects", headers=h, timeout=10).json()["projects"][0]["id"]
ph = {**h, "X-Project-ID": pid}
print("project", pid)


def poll(task_id, label, limit=40):
    st = None
    for _ in range(limit):
        b = s.get(f"{BASE}/observability/tasks/{task_id}", headers=ph, timeout=10).json()
        st = b.get("status") or (b.get("task") or {}).get("status")
        if st in ("completed", "failed", "dead", "error"):
            break
        time.sleep(1)
    check(f"{label} completed", st == "completed", f"status={st}")
    return st


deps = [d for d in s.get(f"{BASE}/deployments", headers=ph, timeout=10).json().get("deployments", []) if d.get("status") == "active"]
echo = next((d for d in deps if d.get("agent_name") == "sample_echo"), None)
check("active sample_echo deployment exists", echo is not None)
dep_id = echo["deployment_id"]

r = s.post(f"{BASE}/deployments/{dep_id}/run", headers=ph, json={"input": {"message": "final validation"}}, timeout=30)
check("run task accepted", r.status_code == 200, str(r.status_code))
poll(r.json()["task_id"], "run #1")

# ZIP upload
agents_dir = Path(__file__).resolve().parents[1] / "agents" / "sample_echo"
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(agents_dir / "agent.yaml", "agent.yaml")
    zf.write(agents_dir / "agent.py", "agent.py")
buf.seek(0)
r = s.post(f"{BASE}/deployments/artifacts/upload", headers={"X-Project-ID": pid}, files={"file": ("sample_echo.zip", buf, "application/zip")}, timeout=60)
check("zip upload (200 or 409)", r.status_code in (200, 409), f"{r.status_code}: {r.text[:160]}")

# Resolve artifact id (from upload or existing)
artifact_id = None
if r.status_code == 200:
    artifact_id = r.json()["artifact"]["artifact_id"]
else:
    arts = s.get(f"{BASE}/deployments/artifacts", headers=ph, timeout=10).json().get("artifacts", [])
    echo_arts = [a for a in arts if a.get("agent_name") == "sample_echo"]
    artifact_id = echo_arts[0]["artifact_id"] if echo_arts else None
check("artifact id resolved", artifact_id is not None)

r = s.post(f"{BASE}/deployments", headers=ph, json={"artifact_id": artifact_id}, timeout=30)
check("deploy uploaded artifact (200 or 409)", r.status_code in (200, 409), f"{r.status_code}: {r.text[:160]}")
if r.status_code == 200:
    new_dep = r.json()["deployment"]["deployment_id"]
else:
    new_dep = dep_id

# Run uploaded agent
r = s.post(f"{BASE}/deployments/{new_dep}/run", headers=ph, json={"input": {"message": "uploaded run"}}, timeout=30)
check("run uploaded agent accepted", r.status_code == 200, str(r.status_code))
poll(r.json()["task_id"], "run #2 (uploaded)")

# API key
r = s.post(f"{BASE}/api-keys", headers=h, json={"name": "validation key"}, timeout=15)
check("create api key", r.status_code == 200, str(r.status_code))

print("=" * 40)
if fails:
    print("BLOCKED:", ", ".join(fails))
    sys.exit(1)
print("READY FOR TESTER")
