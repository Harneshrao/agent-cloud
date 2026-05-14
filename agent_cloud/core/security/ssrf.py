"""
SSRF policy surface for domain layer.

Implementation is delegated to the shared `security.ssrf` module at repo root
(infra wraps httpx). Core may import only these callables for tests.
"""

from __future__ import annotations

from security.ssrf import (  # noqa: F401
    SSRFBlockedError,
    assert_url_allowed,
    safe_httpx_client,
)
