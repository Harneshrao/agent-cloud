# Security Layer 2: Execution and Payload Hardening

This document describes the **next security layer** added to the AI automation platform: request body limits, agent execution time and memory guards, tool execution safety, and fail-safe worker behavior.

---

## 1. Request Body Size Limit

**Middleware:** `api/body_size_limit.py` — `BodySizeLimitMiddleware`

**Behavior:**
- **Maximum request size:** 2 MB.
- Uses the **Content-Length** header when present. If `Content-Length > 2 MB`, the request is rejected **before** reading the body.
- **Response:** HTTP **413** with body `{"error": "Request entity too large", "detail": "..."}`.
- **Logging:** Event **request_body_too_large** (content_length, limit, client_host, path).

**Integration:** Middleware is registered in `api/main.py` (first in the stack so large bodies are rejected early).

**Limitation:** Chunked requests without Content-Length are not size-limited by this middleware; consider an upstream limit (e.g. reverse proxy) for full coverage.

---

## 2. Agent Execution Time Limit

**Module:** `engine/safe_execution.py`

**Behavior:**
- **Timeout:** 60 seconds (configurable via `AGENT_TIMEOUT_SECONDS`).
- Agent run (e.g. `run_single_agent_node` or `run_pipeline`) is executed in a **daemon thread**; the main thread waits up to 60 seconds.
- If the thread does not finish in time:
  - **AgentTimeoutError** is raised.
  - Event **agent_timeout** is logged (task_id, agent_name, timeout_seconds).
  - The worker catches the exception, marks the task as **failed**, and optionally retries or moves it to the dead-letter queue (same as other failures).

**Integration:** In `workers/worker.py`, both DAG node execution and full pipeline execution are wrapped with `run_with_timeout(..., timeout_seconds=60, task_id=..., agent_name=...)`.

---

## 3. Agent Memory Limit (Fail-Safe)

**Module:** `engine/safe_execution.py`

**Behavior:**
- The same thread that runs the agent catches **MemoryError** and converts it to **MemoryLimitExceededError**.
- Event **memory_limit_exceeded** is logged (task_id, agent_name).
- The worker catches **MemoryLimitExceededError**, marks the task as **failed**, and retries or DLQ as usual.

**Note:** Python does not support hard memory caps per thread. This guard ensures that if the agent triggers a **MemoryError** (e.g. very large allocations), the worker does not crash and the task is marked failed and logged. For strict memory limits, use process-level limits (e.g. container memory limits) or a separate sandbox process.

---

## 4. Tool Execution Safety

**Locations:** `engine/tool_executor.py`, `tools/tool_executor.py`

**Rules:**
- **Maximum tool execution time:** 15 seconds per tool run. Enforced in `engine/tool_executor.execute_tool()` via `run_with_timeout(..., timeout_seconds=TOOL_TIMEOUT_SECONDS)`.
- **Maximum response size:** 512 KB for **web_scraper** and **api_caller**. Responses are truncated; if the full response exceeds 512 KB, event **tool_response_too_large** is logged.
- **Binary content blocked:** For **web_scraper** and **api_caller**, responses with `Content-Type` such as `application/octet-stream`, `application/pdf`, or `image/*` / `video/*` / `audio/*` are rejected. A heuristic (null bytes or low proportion of printable characters in the first 1 KB) also blocks likely binary bodies. The tool returns a safe error message instead of passing binary data.
- **Timeouts:** HTTP requests in these tools use **REQUEST_TIMEOUT = 15** seconds. On **requests.exceptions.Timeout**, event **tool_execution_timeout** is logged and a safe error string is returned.
- **Logging:** Tool failures (timeout, response too large) are logged with the existing **security** logger (events **tool_execution_timeout**, **tool_response_too_large**).

---

## 5. Agent Sandbox Policy (Summary)

The platform enforces:

- **Filesystem:** Only paths under **FILE_READ_ROOT** (default `./workspace`) are readable by the **file_reader** tool; path traversal and absolute paths outside the root are rejected and logged (**file_reader_sandbox_denied**).
- **Network:** **web_scraper** and **api_caller** allow only **http** and **https**; private IP ranges, localhost, and metadata addresses are blocked (SSRF protection). Timeout and response size limits apply.
- **No arbitrary shell:** Agent code runs in the same process as the worker; there is no execution of user-provided shell commands. Tools are fixed (file_reader, web_scraper, api_caller, etc.); agents cannot register new tools at runtime from task payloads.
- **Database:** Agents access data only through the application’s database layer (e.g. memory, knowledge graph, project-scoped APIs); no raw SQL from agent code.

Unsafe behavior (e.g. sandbox escape attempt, blocked URL, binary download) results in a safe error response and, where implemented, a security log event.

---

## 6. Security Logging (New Events)

**Logger:** `security` (see `api/security_logger.py`).

**New events:**

| Event                     | When |
|---------------------------|------|
| **request_body_too_large** | Request Content-Length > 2 MB (413). |
| **agent_timeout**         | Agent execution exceeded 60 seconds. |
| **memory_limit_exceeded** | Agent execution raised MemoryError. |
| **tool_execution_timeout**| Tool run exceeded 15 seconds or HTTP timeout. |
| **tool_response_too_large** | Tool response body exceeded 512 KB (truncated). |

All use the same structured **extra** fields (e.g. task_id, agent_name, limit, path) for audit and SIEM.

---

## 7. Fail-Safe Worker Behavior

**Location:** `workers/worker.py`

**Behavior:**
- The entire agent execution block (including `run_with_timeout`) is inside a **try/except**.
- **AgentTimeoutError** and **MemoryLimitExceededError** are caught explicitly; the task is marked failed, retry count is updated, and on max retries the task is moved to the dead-letter queue. The worker then continues to the next task.
- **Any other Exception** is caught by the existing `except Exception` block (DLQ/retry/requeue). The worker **always** continues processing other tasks and does not crash on agent or tool errors.

---

## 8. Modified and New Files

| File | Change |
|------|--------|
| **api/body_size_limit.py** | **New.** Body size limit middleware (2 MB, 413, logging). |
| **api/main.py** | Register **BodySizeLimitMiddleware** (first). |
| **api/security_logger.py** | Add **log_request_body_too_large**, **log_agent_timeout**, **log_memory_limit_exceeded**, **log_tool_execution_timeout**, **log_tool_response_too_large**. |
| **engine/safe_execution.py** | **New.** **run_with_timeout** (thread + 60s), **AgentTimeoutError**, **MemoryLimitExceededError**; **MemoryError** caught in thread and re-raised as **MemoryLimitExceededError**. |
| **engine/tool_executor.py** | **execute_tool** wraps tool run in **run_with_timeout(..., 15s)**; on **AgentTimeoutError** logs **tool_execution_timeout** and returns safe error string. |
| **workers/worker.py** | Wrap **run_single_agent_node** and **run_pipeline** in **run_with_timeout(..., 60)**; catch **AgentTimeoutError** and **MemoryLimitExceededError** and handle like other failures (retry/DLQ). |
| **tools/tool_executor.py** | **web_scraper** / **api_caller**: enforce 15s timeout, 512 KB cap, **block binary** content (Content-Type + heuristic), log **tool_response_too_large** and **tool_execution_timeout**. |
| **SECURITY_LAYER2.md** | **New.** This document. |

---

## 9. Protections Summary

- **Denial-of-service:** 2 MB body limit (413), 60s agent timeout, 15s tool timeout, rate limiting (existing).
- **Malicious agents:** No shell, file access only under `./workspace`, SSRF protections and binary blocking on URL tools.
- **Infinite loops / runaway execution:** 60s agent timeout; worker stays responsive and marks task failed.
- **Memory exhaustion:** **MemoryError** caught in agent thread, task failed and logged; worker continues.
- **Oversized payloads:** 413 for large request bodies; 512 KB cap and binary blocking for tool responses.

Together with existing auth, project isolation, rate limiting, webhook verification, and security logging, the platform is more resilient against abuse, crashes, and malicious or buggy agent execution.
