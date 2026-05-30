#!/usr/bin/env python3
"""Walk through the alpha invite flow via API (simulates dashboard actions)."""
import json
import sys
import time

import requests

BASE = "http://127.0.0.1:8000"
s = requests.Session()
headers = {"Content-Type": "application/json"}


def step(name, fn):
    t0 = time.time()
    try:
        r = fn()
        dt = time.time() - t0
        ok = r.status_code < 400
        tag = "OK" if ok else "FAIL"
        print(f"[{tag}] {name} ({dt:.1f}s) -> {r.status_code}")
        if not ok:
            print("   ", r.text[:400])
        return r
    except Exception as e:
        print(f"[ERR] {name}: {e}")
        return None


def main():
    step("health", lambda: s.get(f"{BASE}/health"))

    r = step("list projects", lambda: s.get(f"{BASE}/projects", headers=headers))
    projects = r.json().get("projects", []) if r and r.ok else []

    if not projects:
        r = step(
            "create project",
            lambda: s.post(
                f"{BASE}/projects", headers=headers, json={"name": "Alpha test project"}
            ),
        )
        pid = r.json()["project"]["id"] if r and r.ok else None
    else:
        pid = projects[0]["id"]
        print(f"  using existing project {pid}")

    if not pid:
        sys.exit(1)

    h = {**headers, "X-Project-ID": pid}

    r = step(
        "deploy sample_echo",
        lambda: s.post(f"{BASE}/deployments/onboarding/sample/sample_echo", headers=h),
    )
    dep_id = r.json()["deployment"]["deployment_id"] if r and r.ok else None
    if dep_id:
        print(f"  deployment_id={dep_id}")

    task_id = None
    if dep_id:
        r = step(
            "run deployment",
            lambda: s.post(
                f"{BASE}/deployments/{dep_id}/run",
                headers=h,
                json={"input": {"message": "hello from alpha test"}},
            ),
        )
        if r and r.ok:
            task_id = r.json().get("task_id")
            print(f"  task_id={task_id}")

    if task_id:
        for i in range(30):
            r = s.get(f"{BASE}/observability/tasks/{task_id}", headers=h)
            if r.ok:
                body = r.json()
                st = body.get("status") or (body.get("task") or {}).get("status")
                print(f"  poll {i}: status={st}")
                if st in ("completed", "failed", "error", "dead"):
                    break
            time.sleep(1)
        step("task logs", lambda: s.get(f"{BASE}/observability/tasks/{task_id}/logs", headers=h))

    step(
        "create api key",
        lambda: s.post(f"{BASE}/api-keys", headers=headers, json={"name": "alpha test key"}),
    )

    r = step(
        "deploy sample_fail",
        lambda: s.post(f"{BASE}/deployments/onboarding/sample/sample_fail", headers=h),
    )
    fail_dep = r.json()["deployment"]["deployment_id"] if r and r.ok else None
    if fail_dep:
        r = step(
            "run sample_fail",
            lambda: s.post(
                f"{BASE}/deployments/{fail_dep}/run", headers=h, json={"input": {}}
            ),
        )
        fail_task = r.json().get("task_id") if r and r.ok else None
        if fail_task:
            for i in range(25):
                r = s.get(f"{BASE}/observability/tasks/{fail_task}", headers=h)
                if r.ok:
                    body = r.json()
                    st = body.get("status") or (body.get("task") or {}).get("status")
                    if st in ("completed", "failed", "error", "dead"):
                        print(f"  fail task status={st}")
                        break
                time.sleep(1)
        step("dlq list", lambda: s.get(f"{BASE}/observability/dlq", headers=h))

    print("DONE")


if __name__ == "__main__":
    main()
