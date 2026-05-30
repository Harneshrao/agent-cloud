import logging
import os
import ipaddress
import requests
from urllib.parse import urlparse

from registry.tool_registry import tool_registry

_security_log = logging.getLogger("security")

# Sandbox: file_reader only allows paths under this directory (set FILE_READ_ROOT to override).
# Default ./workspace so agents cannot escape to host filesystem.
FILE_READ_ROOT = os.path.abspath(
    os.environ.get("FILE_READ_ROOT", os.path.join(os.getcwd(), "workspace"))
)
# SSRF: block private/metadata IPs and only allow http(s).
BLOCKED_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / metadata
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)
MAX_RESPONSE_BYTES = 512 * 1024  # 512 KB cap for scraper/caller
REQUEST_TIMEOUT = 15  # seconds; aligned with TOOL_TIMEOUT_SECONDS for network portion


def run_tool(tool_name, task):

    # Prefer registered tools if available to keep the registry as the
    # single source of truth for tools.
    tool_meta = tool_registry.get_tool(tool_name)
    if tool_meta is not None:
        return tool_meta.function(task)

    if tool_name == "web_search":
        return web_search(task)

    elif tool_name == "web_scraper":
        return web_scraper(task)

    elif tool_name == "file_reader":
        return file_reader(task)

    elif tool_name == "api_caller":
        return api_caller(task)

    elif tool_name == "analysis_tool":
        return analysis_tool(task)

    else:
        return "Unknown tool"


def web_search(task):
    query = task.get("query", task) if isinstance(task, dict) else task
    query = str(query or "").strip()
    print("🌐 Running Web Search Tool")
    return f"Search results for: {query}"


def _is_url_allowed(url_str: str) -> bool:
    """DNS-aware SSRF check via security.ssrf (blocks private/metadata IPs)."""
    try:
        from security.ssrf import SSRFBlockedError, assert_url_allowed

        assert_url_allowed(url_str)
        return True
    except Exception:
        return False


def _safe_http_get(url: str) -> requests.Response:
    """GET with redirects disabled after SSRF validation."""
    return requests.get(
        url, timeout=REQUEST_TIMEOUT, allow_redirects=False, stream=True
    )


def _is_binary_content(content_type: str | None, content: bytes) -> bool:
    """Block binary downloads: octet-stream or likely binary body."""
    if not content_type:
        content_type = ""
    ct = content_type.split(";")[0].strip().lower()
    if ct in ("application/octet-stream", "application/pdf"):
        return True
    if ct.startswith("image/") or ct.startswith("video/") or ct.startswith("audio/"):
        return True
    # Heuristic: null byte or >30% non-printable in first 1KB
    sample = content[:1024]
    if b"\x00" in sample:
        return True
    printable = sum(1 for b in sample if 32 <= b < 127 or b in (9, 10, 13))
    if len(sample) > 0 and printable / len(sample) < 0.7:
        return True
    return False


def web_scraper(task):
    url = task.get("url", task) if isinstance(task, dict) else task
    url = str(url).strip() if url else ""
    print("🕸 Running Web Scraper")
    if not url or not _is_url_allowed(url):
        return "Scraping failed: URL not allowed (use https and avoid private IPs)"
    try:
        resp = _safe_http_get(url)
        resp.raise_for_status()
        content = resp.content[:MAX_RESPONSE_BYTES]
        if len(resp.content) > MAX_RESPONSE_BYTES:
            _security_log.warning(
                "tool_response_too_large tool=web_scraper size=%s limit=%s",
                len(content), MAX_RESPONSE_BYTES,
                extra={"event": "tool_response_too_large", "tool_name": "web_scraper", "size": len(resp.content), "limit": MAX_RESPONSE_BYTES},
            )
        if _is_binary_content(resp.headers.get("content-type"), content):
            return "Scraping failed: binary content not allowed"
        text = content.decode("utf-8", errors="replace")
        return text[:300]
    except requests.exceptions.Timeout:
        _security_log.warning(
            "tool_execution_timeout tool=web_scraper timeout_seconds=%s",
            REQUEST_TIMEOUT,
            extra={"event": "tool_execution_timeout", "tool_name": "web_scraper", "timeout_seconds": REQUEST_TIMEOUT},
        )
        return "Scraping failed: timeout"
    except Exception:
        return "Scraping failed"


def file_reader(task):
    raw = task.get("file_path", task) if isinstance(task, dict) else task
    file_path = str(raw).strip() if raw else ""
    print("📂 Running File Reader")
    if not file_path:
        return "File not found: no path provided"
    try:
        root = os.path.abspath(FILE_READ_ROOT)
        if not os.path.isdir(root):
            os.makedirs(root, exist_ok=True)
        resolved = os.path.normpath(file_path)
        if not os.path.isabs(resolved):
            resolved = os.path.join(root, resolved)
        resolved = os.path.realpath(resolved)
        try:
            if os.path.commonpath([resolved, root]) != root:
                _security_log.warning(
                    "file_reader sandbox denied: requested_path=%s resolved=%s root=%s",
                    file_path, resolved, root,
                    extra={"event": "file_reader_sandbox_denied", "requested_path": file_path, "resolved": resolved, "root": root},
                )
                return "File not found: path outside allowed directory"
        except ValueError:
            return "File not found: path outside allowed directory"
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return "File not found"
    except Exception:
        return "File not found"


def api_caller(task):
    endpoint = task.get("endpoint", task) if isinstance(task, dict) else task
    endpoint = str(endpoint).strip() if endpoint else ""
    print("🔗 Running API Caller")
    if not endpoint or not _is_url_allowed(endpoint):
        return "API call failed: URL not allowed (use https and avoid private IPs)"
    try:
        resp = _safe_http_get(endpoint)
        resp.raise_for_status()
        content = resp.content[:MAX_RESPONSE_BYTES]
        if len(resp.content) > MAX_RESPONSE_BYTES:
            _security_log.warning(
                "tool_response_too_large tool=api_caller size=%s limit=%s",
                len(content), MAX_RESPONSE_BYTES,
                extra={"event": "tool_response_too_large", "tool_name": "api_caller", "size": len(resp.content), "limit": MAX_RESPONSE_BYTES},
            )
        if _is_binary_content(resp.headers.get("content-type"), content):
            return "API call failed: binary content not allowed"
        ct = (resp.headers.get("content-type") or "").lower()
        if ct.startswith("application/json"):
            return resp.json()
        return {"raw": content.decode("utf-8", errors="replace")[:1000]}
    except requests.exceptions.Timeout:
        _security_log.warning(
            "tool_execution_timeout tool=api_caller timeout_seconds=%s",
            REQUEST_TIMEOUT,
            extra={"event": "tool_execution_timeout", "tool_name": "api_caller", "timeout_seconds": REQUEST_TIMEOUT},
        )
        return "API call failed: timeout"
    except Exception:
        return "API call failed"


def analysis_tool(task):
    data = task.get("data", task) if isinstance(task, dict) else task
    print("📊 Running Analysis Tool")
    return f"Analysis result for: {data}"


def execute_tool(tool_name, input_data):

    tool_meta = tool_registry.get_tool(tool_name)
    if tool_meta is None:
        return "Tool not found"

    return tool_meta.function(input_data)


# Register built-in tools with the global registry so they are discoverable
# across the platform.
tool_registry.register_tool(
    name="web_search",
    description="Search the web for information based on a query string.",
    function=web_search,
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query text."},
        },
        "required": ["query"],
    },
    output_schema={
        "type": "string",
        "description": "A short textual description of search results.",
    },
)

tool_registry.register_tool(
    name="web_scraper",
    description="Fetch and return the first 300 characters of a web page for a given URL.",
    function=web_scraper,
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri", "description": "URL to scrape."},
        },
        "required": ["url"],
    },
    output_schema={
        "type": "string",
        "description": "Raw HTML/text snippet from the target page.",
    },
)

tool_registry.register_tool(
    name="file_reader",
    description="Read and return the full contents of a local text file.",
    function=file_reader,
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the target file.",
            },
        },
        "required": ["file_path"],
    },
    output_schema={
        "type": "string",
        "description": "Contents of the specified file, or an error message.",
    },
)

tool_registry.register_tool(
    name="api_caller",
    description="Perform an HTTP GET request to an API endpoint and return the JSON body.",
    function=api_caller,
    input_schema={
        "type": "object",
        "properties": {
            "endpoint": {
                "type": "string",
                "format": "uri",
                "description": "HTTP(S) endpoint to call.",
            },
        },
        "required": ["endpoint"],
    },
    output_schema={
        "type": "object",
        "description": "Parsed JSON response from the API, or an error message.",
    },
)

tool_registry.register_tool(
    name="analysis_tool",
    description="Run a simple analysis over provided data and return a human-readable summary.",
    function=analysis_tool,
    input_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "description": "Raw text or serialized data to analyze.",
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "string",
        "description": "Human-readable analysis summary for the input data.",
    },
)