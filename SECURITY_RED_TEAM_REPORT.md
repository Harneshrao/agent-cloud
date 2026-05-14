# Red Team Penetration Test Report  
## AI Agent Automation Infrastructure

**Classification:** Internal use — simulated attack analysis  
**Scope:** API, database, workers, agent runtime, autonomous features, knowledge graph, memory, dashboard, DoS  
**Date:** March 2025

---

## Executive Summary

This report documents vulnerabilities discovered during a simulated red-team analysis of the Agent Cloud platform. Findings range from **critical** (unauthenticated task enqueue, agent tool filesystem/SSRF escape) to **low** (missing rate limits, CORS too permissive). The platform has solid multi-tenant and parameterized SQL in most modules, but several API endpoints lack authentication, and the agent tool layer allows filesystem and network abuse. Recommendations are ordered by severity with concrete remediation steps.

---

## 1. API Attack Surface

### 1.1 Unauthenticated task enqueue — **CRITICAL**

**Location:** `api/main.py` — `GET /agent/run`

**Finding:** The endpoint has no authentication or project context. Any client can call:

```
GET /agent/run?agent=research_agent&task=any+task+text
```

and enqueue tasks into the global queue. Tasks are created with `project_id=None` (see `enqueue_task` in `main.py`), so they are not scoped to any project.

**Attack scenario:** An attacker scripts repeated requests to `/agent/run` to flood the queue, consume worker capacity, and cause denial of service or resource exhaustion.

**Recommendation:**

- Require authentication (e.g. `Depends(get_current_user)`) and project context (e.g. `Depends(require_project_context)`).
- Always pass `project_id` from context to `enqueue_task()` so tasks are project-scoped and subject to quota.
- Consider deprecating this endpoint in favor of project-scoped alternatives (e.g. `/agent-instances/{id}/run` or workflow APIs).

---

### 1.2 Unauthenticated read of task and runs — **HIGH**

**Location:** `api/main.py`

**Findings:**

- `GET /task/{task_id}` — returns task details and result by numeric ID; no auth.
- `GET /tasks/{task_id}/stream` — returns stream events for a task; no auth.
- `GET /task/{task_id}/runs` — returns agent runs for a task; no auth.

**Attack scenario:** An attacker iterates over `task_id` (e.g. 1–10000) and harvests task text, results, and agent outputs, leading to information disclosure across tenants.

**Recommendation:**

- Add `Depends(require_project_context)` and resolve `task_id` to `project_id` via `db.get_task_project_id(task_id)`; return 403 if the task’s project does not match the caller’s project.
- Apply the same pattern to stream and runs endpoints.

---

### 1.3 Unauthenticated system and observability APIs — **HIGH**

**Location:** `api/system_api.py`

**Finding:** All endpoints are unauthenticated:

- `GET /system/metrics`, `/system/workers`, `/system/queue`, `/system/containers`, `/system/recovery`, `/system/autoscaler`, `/system/dead_letters`, `/system/alerts`, `/system/health`

**Attack scenario:** Attackers can map infrastructure (workers, queue length, containers, dead letters, alerts), enabling targeted DoS and reconnaissance.

**Recommendation:**

- Protect system routes with authentication (e.g. API key or `get_current_user`) and restrict to admin/operator roles if applicable.
- Alternatively, expose these only on an internal network or separate admin port.

---

### 1.4 Unauthenticated webhook ingestion — **HIGH**

**Location:** `api/webhook_api.py` — `POST /webhooks/{source}`

**Finding:** No authentication. Any client can POST with `event_type` and `payload`. `process_webhook` calls `process_event(event_type, normalized)` with **no project_id**, so triggers with `project_id IS NULL` match and tasks are enqueued globally.

**Attack scenario:** Attacker sends `POST /webhooks/github` with arbitrary `event_type` and large `payload` to trigger event-driven tasks and queue flooding.

**Recommendation:**

- Require authentication or a shared secret (e.g. HMAC per source) for webhooks.
- Require a project-scoping mechanism (e.g. header or path) and pass `project_id` into `process_webhook` / `process_event` so only project-scoped triggers fire.
- Optionally validate webhook payload size and rate-limit per source.

---

### 1.5 Unauthenticated event trigger disable — **MEDIUM**

**Location:** `api/event_api.py` — `DELETE /events/triggers/{trigger_id}`

**Finding:** No dependency on `require_project_context` or `get_current_user`. Any client can disable any trigger by ID.

**Attack scenario:** Attacker disables critical triggers (e.g. CI/CD or alerting) by enumerating trigger IDs.

**Recommendation:**

- Add `Depends(require_project_context)` and verify the trigger’s `project_id` matches the caller’s project (or that the user is allowed to manage that project) before disabling.

---

### 1.6 Workflow analytics/optimization without project context — **MEDIUM**

**Location:** `api/workflow_api.py`

**Finding:** These endpoints do not use `require_project_context`:

- `GET /workflows/analytics/aggregate`
- `GET /workflows/optimization/slow-nodes`
- `GET /workflows/optimization/recommendations`
- `GET /workflows/optimization/summary`
- `POST /workflows/optimization/apply`

**Attack scenario:** Unauthenticated access to workflow analytics and the ability to apply optimization (e.g. change template DAG) if `dry_run=False` is used.

**Recommendation:**

- Add `Depends(require_project_context)` and scope all queries and mutations by `project_id` (and template ownership) so tenants only see and modify their own data.

---

### 1.7 Dev bypass and CORS — **LOW / MEDIUM**

**Location:** `api/main.py`, `api/auth_api.py`

**Findings:**

- `ALLOW_ANONYMOUS_DEV=1` (default in `main.py`) makes `get_current_user` return a synthetic user without a token, effectively disabling auth for all project-scoped endpoints when enabled.
- CORS is configured with `allow_origins=["*"]` and `allow_credentials=False`, which is acceptable for non-credentialed requests but allows any site to call the API.

**Recommendation:**

- Default `ALLOW_ANONYMOUS_DEV` to `0` in production; use env-only for local dev.
- In production, restrict CORS to known dashboard origins (e.g. `https://app.yourdomain.com`). If credentials are added later, set `allow_credentials=True` and avoid `*` for origins.

---

## 2. SQL Injection

### 2.1 Placeholder mismatch in main.py — **MEDIUM** (bug / future injection risk)

**Location:** `api/main.py` — `get_task`, `get_runs`

**Finding:** Queries use `%s` placeholders:

```python
cur.execute("SELECT ... WHERE id = %s", (task_id,))
```

The codebase uses SQLite (`database/db.py`), which expects `?` placeholders. With `%s`, SQLite does not substitute parameters; the literal `%s` may cause errors or unexpected behavior. If the app is ever switched to a driver that interprets `%s` as format specifiers, concatenation or misuse could lead to SQL injection.

**Recommendation:**

- Use `?` for all SQLite queries and pass parameters as a tuple. Replace every `%s` in `main.py` with `?` and keep using the same tuple arguments.
- Standardize on a single placeholder style (e.g. `?` for SQLite) across the codebase.

---

### 2.2 Rest of database layer — **SECURE**

**Finding:** Reviewed modules (`database/db.py`, `database/agent_memory.py`, `database/knowledge_graph.py`, `database/event_triggers.py`, `database/autonomous_policies.py`, `task_queue/task_queue.py`, `database/simulation.py`, and others) use parameterized queries with `?` and no string formatting of SQL. No classic SQL injection was found there.

**Recommendation:** Keep using parameterized queries only; avoid building SQL with `.format()` or `%` on user input.

---

## 3. Worker Execution

### 3.1 No cap on task payload size — **MEDIUM**

**Location:** `task_queue/task_queue.py` — `enqueue_task` → `db.create_task(task_text=task_text, ...)`

**Finding:** `task_text` is the full JSON-serialized payload. There is no maximum length check. Extremely large payloads can bloat the DB and memory when workers parse them.

**Attack scenario:** Attacker enqueues tasks with huge `task` or nested structures to increase storage and parsing cost.

**Recommendation:**

- Enforce a maximum length for `task_text` (e.g. 64 KB or 256 KB) before `create_task`. Reject with 413 or 400 if exceeded.
- Optionally limit depth and size of JSON (e.g. max keys, array length) to prevent parser abuse.

---

### 3.2 No per-project or global enqueue rate limit — **MEDIUM**

**Location:** `task_queue/task_queue.py`, `api/main.py`, `api/webhook_api.py`, `api/event_api.py`

**Finding:** Quota is checked only in `event_api.ingest_event` (project-scoped). `/agent/run`, webhooks, and other enqueue paths do not apply rate limits. Queue flooding is possible.

**Recommendation:**

- Add rate limiting (e.g. per IP and per project) on all endpoints that enqueue tasks (e.g. `/agent/run`, webhooks, event ingest, agent-instance run).
- Enforce a global or per-project cap on pending tasks if needed (e.g. reject enqueue when pending count exceeds a threshold).

---

### 3.3 Task execution and idempotency — **SECURE**

**Finding:** Workers use `database.task_idempotency` (`try_claim`, `set_completed`, `get_result`) and idempotency keys derived from `workflow_id:node_id` or task id. Duplicate execution of the same logical task is prevented. Task payload is parsed as JSON and passed as state; there is no execution of user-provided code from the payload (agents are registered server-side). No arbitrary code execution via task content was found.

**Recommendation:** Keep idempotency; consider documenting the expected payload shape and validating required fields (e.g. `task`, `agent`) to fail fast on malformed input.

---

## 4. Agent Runtime and Tools

### 4.1 File reader tool — arbitrary file read — **CRITICAL**

**Location:** `tools/tool_executor.py` — `file_reader(file_path)`

**Finding:** The tool runs `open(file_path, "r")` with no path validation or sandbox. An agent (or any caller that can influence tool input) can pass `file_path="/etc/passwd"`, `"../../.env"`, or any path the process can read.

**Attack scenario:** A malicious or compromised agent, or a task that influences tool parameters, causes the worker to read secrets or sensitive files from the host.

**Recommendation:**

- Restrict to an allowed directory (e.g. a dedicated workspace per project/run). Resolve `file_path` to a real path and ensure it is under that directory; reject otherwise.
- Do not allow absolute paths or `..` outside the allowed root. Prefer a whitelist of extensions (e.g. `.txt`, `.json`, `.csv`) if applicable.

---

### 4.2 Web scraper and API caller — SSRF — **HIGH**

**Location:** `tools/tool_executor.py` — `web_scraper(url)`, `api_caller(endpoint)`

**Finding:** Both use user-controlled URLs with `requests.get()`. No validation of scheme or host. An agent can request `http://169.254.169.254/latest/meta-data/` (cloud metadata), internal services (e.g. `http://localhost:6379`), or other internal resources.

**Attack scenario:** Agent or manipulated task triggers requests to metadata endpoints, internal APIs, or admin interfaces, leading to credential theft or lateral movement.

**Recommendation:**

- Allow only `https` (and optionally `http` only for explicitly allowed hosts). Block private IP ranges (RFC 1918, link-local, metadata) and `localhost`.
- Use an allowlist of hostnames or domains if possible. Consider a short timeout and size limit on responses.
- Apply the same rules in any other HTTP-calling tools.

---

### 4.3 Analysis tool and tool registry — **LOW**

**Finding:** `analysis_tool(data)` and other tools do not execute code from input. Custom tools registered via `tool_registry` are loaded from the server; ensure only trusted code is registered. No further critical issues identified in the agent runtime itself (state is passed to `agent.run()`; no `eval`/`exec` of task text).

**Recommendation:** Document that only trusted tools may be registered; consider a sandbox or capability list for future tool types (e.g. shell or subprocess).

---

## 5. Autonomous Agent Abuse

### 5.1 Event-driven task burst — **MEDIUM**

**Location:** `engine/event_engine.py` — `process_event`

**Finding:** One event can match many triggers (`list_enabled_by_event_type`). For each trigger, a task is enqueued with no per-event or per-project cap. A single `ingest_event` or webhook call can therefore enqueue many tasks.

**Attack scenario:** Attacker sends an event that matches 50 triggers → 50 tasks enqueued at once; repeated events cause queue and worker overload.

**Recommendation:**

- Cap the number of tasks enqueued per event (e.g. 10 or 20). After the cap, log and skip remaining triggers or return a warning.
- Ensure event ingest and webhooks are rate-limited and project-scoped (see API and webhook sections).

---

### 5.2 Autonomous cycle policy — **SECURE**

**Finding:** `database/autonomous_policies.py` and `record_launch_and_check` enforce per-agent, per-project policies and `max_launches_per_hour`. The autonomous-cycle API uses `require_project_context` and checks policy before enqueueing. No abuse path identified beyond the need to rate-limit the autonomous-cycle endpoint itself if desired.

**Recommendation:** Optionally add a per-project or per-user rate limit on `POST /agent-instances/{id}/autonomous-cycle` to prevent excessive polling or scripted abuse.

---

## 6. Distributed System

### 6.1 Race in scan-and-claim — **LOW**

**Location:** `task_queue/task_queue.py` — `fetch_next_task` when using capability/region/worker_type filtering

**Finding:** When not using the atomic `UPDATE ... RETURNING` path, the code gets `get_pending_tasks()` then iterates and updates by ID. Two workers can grab the same task if they both read the same pending set before either commits. SQLite serializes per connection; with multiple workers this is still a possible race.

**Recommendation:** Prefer a single atomic claim (e.g. `UPDATE tasks SET status='running', worker_id=? WHERE id=(SELECT id FROM tasks WHERE status='pending' ... LIMIT 1) RETURNING ...`) and use the result; retry or skip if no row updated. This reduces duplicate execution risk.

---

### 6.2 Idempotency — **SECURE**

**Finding:** Idempotency keys and `try_claim` / `set_completed` are used correctly; duplicate completion is avoided. Dead-letter and retry limits are in place. No priority manipulation beyond the existing `priority` field (which is parsed from payload); consider validating and bounding priority if needed.

**Recommendation:** Keep current idempotency design; document expected key format and cleanup policy for old idempotency records.

---

## 7. Knowledge Graph

### 7.1 Project scoping and parameterized queries — **SECURE**

**Finding:** `database/knowledge_graph.py` uses `project_id` in all operations and parameterized SQL. Entities and edges are project-scoped. No SQL injection or cross-tenant read/write found.

### 7.2 Large JSON and traversal — **LOW**

**Finding:** `upsert_entity` stores `data` as JSON string with no size limit. `list_entities` has a default `limit=100`; `find_related_entities` does not limit recursion (it does one-hop edges only), so no graph traversal explosion. Large entity payloads could still stress storage and memory.

**Recommendation:** Enforce a maximum size for entity `data` (e.g. 64 KB). Optionally cap the number of related entities returned per call (e.g. limit 100) to avoid large responses.

---

## 8. Memory System

### 8.1 ChromaDB memory_engine — no project scoping — **MEDIUM**

**Location:** `memory/memory_engine.py`

**Finding:** A single global ChromaDB collection is used for all agents. There is no `project_id` or namespace. Any agent that uses this store can read/write memory that is visible to all others (cross-tenant data leakage if this path is used in production).

**Recommendation:**

- Either scope ChromaDB by project (e.g. collection per project or namespace in document IDs) and pass `project_id` from the caller, or deprecate this global store in favor of the project-scoped `database/agent_memory.py` only.
- Ensure the orchestrator and agents use the project-scoped persistent memory (`database.agent_memory`) for production and do not rely on the global ChromaDB for multi-tenant data.

---

### 8.2 Persistent agent_memory — **SECURE** (with size recommendation)

**Finding:** `database/agent_memory.py` is project- and agent-scoped; queries are parameterized. No cross-project access. Value is stored as TEXT with no maximum length.

**Recommendation:** Add a maximum value size (e.g. 256 KB or 1 MB) per key to prevent storage exhaustion; reject or truncate with a clear policy.

---

## 9. Dashboard and Browser

### 9.1 API exposure and CORS — **LOW / MEDIUM**

**Finding:** Dashboard uses `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) and sends `X-Project-ID` and `Content-Type`. It does not send `Authorization` in the snippets reviewed (`lib/api.ts`), so with `ALLOW_ANONYMOUS_DEV=1` the backend accepts requests without a token. CORS `allow_origins=["*"]` allows any origin to call the API.

**Attack scenario:** A malicious site can call the API from the browser if the user has no token (dev mode) or if endpoints remain unauthenticated. With auth enabled, CSRF is less of an issue for state-changing requests that require a Bearer token (same-origin or explicit CORS), but custom headers do not fully prevent GET abuse from other origins.

**Recommendation:**

- Send `Authorization: Bearer <token>` from the dashboard for production; store token securely (e.g. httpOnly cookie or secure storage) and avoid logging it.
- Restrict CORS in production to the dashboard origin(s). Do not rely on `ALLOW_ANONYMOUS_DEV` in production.
- Ensure no sensitive operations rely solely on `X-Project-ID` without verifying the user’s access to that project (already enforced where `require_project_context` is used).

### 9.2 XSS — **LOW**

**Finding:** No server-rendered unsanitized user content was reviewed in the dashboard. Task text and results are likely rendered in React; ensure any HTML or markdown from the API is sanitized or rendered in a safe way (e.g. no `dangerouslySetInnerHTML` with raw API data).

**Recommendation:** Audit all places that render task text, results, or agent output; use a safe renderer or sanitizer for user-generated content.

---

## 10. Denial of Service

### 10.1 Queue flooding — **HIGH**

**Finding:** Unauthenticated `/agent/run` and webhooks allow unlimited enqueue. No global or per-IP rate limit. Event ingest has quota check but no per-minute cap. Result: queue and worker exhaustion.

**Recommendation:** See sections 1.1, 1.4, 3.2: add auth, project scoping, and rate limits on all enqueue paths; optionally cap pending tasks per project.

---

### 10.2 Heavy metrics and expensive endpoints — **MEDIUM**

**Finding:** `/system/metrics`, `/system/workers`, workflow analytics, and optimization endpoints can be expensive. No rate limiting. Unauthenticated access allows repeated heavy requests.

**Recommendation:** Protect and rate-limit system and analytics endpoints; add caching (e.g. short TTL) for metrics where appropriate.

---

### 10.3 Large workflow graphs and payloads — **LOW**

**Finding:** Large DAGs and huge task payloads can stress the scheduler and workers. No explicit limits on workflow size or node count were found.

**Recommendation:** Enforce maximum nodes per workflow and maximum task payload size (see 3.1); reject creation when exceeded. Add timeouts for DAG scheduling and node execution where applicable.

---

## 11. Summary Table

| ID   | Finding                                      | Severity  |
|------|-----------------------------------------------|-----------|
| 1.1  | Unauthenticated /agent/run task enqueue       | Critical  |
| 1.2  | Unauthenticated task/stream/runs read         | High      |
| 1.3  | Unauthenticated system APIs                   | High      |
| 1.4  | Unauthenticated webhook + no project_id       | High      |
| 1.5  | Unauthenticated trigger disable               | Medium    |
| 1.6  | Workflow analytics without project context    | Medium    |
| 1.7  | ALLOW_ANONYMOUS_DEV default, CORS *           | Low/Med   |
| 2.1  | main.py SQL placeholder %s vs ?               | Medium    |
| 3.1  | No task payload size limit                    | Medium    |
| 3.2  | No enqueue rate limit                         | Medium    |
| 4.1  | file_reader arbitrary file read                | Critical  |
| 4.2  | web_scraper / api_caller SSRF                  | High      |
| 5.1  | Event-driven task burst                       | Medium    |
| 6.1  | Race in scan-and-claim                        | Low       |
| 7.2  | Knowledge graph entity size                  | Low       |
| 8.1  | ChromaDB memory not project-scoped            | Medium    |
| 8.2  | Agent memory value size                       | Low       |
| 9.1  | CORS and API exposure                         | Low/Med   |
| 9.2  | XSS in rendered content                       | Low       |
| 10.1 | Queue flooding                                | High      |
| 10.2 | Heavy metrics DoS                             | Medium    |
| 10.3 | Large workflow/payload DoS                    | Low       |

---

## 12. Recommended Fix Order

1. **Immediate:** Add auth and project scoping to `/agent/run`; fix or remove unauthenticated task/stream/runs read; restrict file_reader to a sandbox directory; add SSRF protections to web_scraper and api_caller.
2. **Short term:** Protect system and webhook APIs (auth + project scoping for webhooks); add trigger ownership check for DELETE trigger; fix main.py SQL placeholders; add task payload size limit and enqueue rate limits.
3. **Next:** Scope or deprecate ChromaDB memory; add project context to workflow analytics/optimization; tighten CORS and disable anonymous dev by default in production; add memory value size limit and knowledge graph entity size limit.
4. **Ongoing:** Rate limit autonomous-cycle and expensive endpoints; harden task claim to be atomic where possible; document and enforce tool registration and XSS/sanitization policies.

---

---

## 13. Optional Code Improvements Applied

The following defensive changes were applied in the codebase (can be reverted if they conflict with product decisions):

- **api/main.py:** SQL placeholders changed from `%s` to `?` for SQLite compatibility (fixes 2.1).
- **tools/tool_executor.py:**  
  - **file_reader:** Sandboxed to paths under `FILE_READ_ROOT` (env: `FILE_READ_ROOT`, default `./workspace`). Rejects paths outside that directory (fixes 4.1).  
  - **web_scraper / api_caller:** SSRF mitigations added: only `http`/`https`, block private IP ranges and localhost, timeout and response size cap (fixes 4.2).  
  - Built-in tools now accept either a dict (e.g. `{"file_path": "..."}`) or legacy positional input for backward compatibility.
- **api/event_api.py:** `DELETE /events/triggers/{trigger_id}` now requires `require_project_context` and verifies the trigger’s `project_id` matches the caller’s project (fixes 1.5).
- **api/workflow_api.py:** Workflow analytics and optimization endpoints now use `Depends(require_project_context)` so only authenticated users with a project can access them (fixes 1.6). Backend analytics functions do not yet filter by `project_id`; that is left as a follow-up.

**Not changed (require product/ops decisions):**  
- Auth on `/agent/run`, `/task/{id}`, `/tasks/{id}/stream`, `/task/{id}/runs`, system APIs, and webhooks.  
- Default for `ALLOW_ANONYMOUS_DEV`, CORS allowlist, rate limits, task payload size limit, ChromaDB project scoping.

---

*End of report. For questions or to request re-test after remediation, contact the security or platform team.*
