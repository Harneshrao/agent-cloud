"""SSRF-safe HTTP — delegates to `security.ssrf` + httpx."""

from __future__ import annotations

from typing import Any

import httpx

from security.ssrf import assert_url_allowed, safe_httpx_client


def request_safe(method: str, url: str, **kwargs: Any) -> httpx.Response:
    assert_url_allowed(url)
    with safe_httpx_client() as client:
        return client.request(method, url, **kwargs)
