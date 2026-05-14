"""
SSRF-safe outbound HTTP: resolve hostnames and reject private / link-local / metadata IPs.

Use `safe_httpx_client()` for user-influenced URLs. Fixed first-party URLs (e.g. Google OAuth)
may use `assert_url_allowed()` before a one-off request.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any, Iterable, Union
from urllib.parse import urlparse

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB response cap for streaming reads


class SSRFBlockedError(ValueError):
    """Raised when a URL resolves to or targets a disallowed address."""


def _is_ip_allowed(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _is_ip_allowed(ip.ipv4_mapped)
    if ip.is_loopback or ip.is_link_local:
        return False
    if ip.is_multicast or ip.is_reserved:
        return False
    if ip.version == 4:
        if ip in ipaddress.ip_network("169.254.0.0/16"):
            return False
        if ip in ipaddress.ip_network("0.0.0.0/8"):
            return False
        if ip in ipaddress.ip_network("10.0.0.0/8"):
            return False
        if ip in ipaddress.ip_network("172.16.0.0/12"):
            return False
        if ip in ipaddress.ip_network("192.168.0.0/16"):
            return False
        if ip in ipaddress.ip_network("100.64.0.0/10"):  # CGNAT
            return False
    else:  # IPv6
        if ip in ipaddress.ip_network("fc00::/7"):  # ULA
            return False
        if ip in ipaddress.ip_network("fe80::/10"):
            return False
    return True


def _resolved_ips(hostname: str, port: int = 443) -> Iterable[str]:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFBlockedError(f"DNS resolution failed for {hostname!r}") from e
    seen: set[str] = set()
    for fam, _, _, _, sockaddr in infos:
        if fam == socket.AF_INET:
            seen.add(sockaddr[0])
        elif fam == socket.AF_INET6:
            seen.add(sockaddr[0])
    return seen


def assert_url_allowed(url: str, *, allowed_schemes: tuple[str, ...] = ("https", "http")) -> None:
    """
    Validate URL: scheme, no credentials, resolve host, reject private IPs.
    Call before httpx/requests to user-controlled URLs.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in allowed_schemes:
        raise SSRFBlockedError(f"URL scheme not allowed: {parsed.scheme!r}")
    if not parsed.hostname:
        raise SSRFBlockedError("URL has no hostname")
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith(".localhost"):
        raise SSRFBlockedError("localhost hostnames are not allowed")
    try:
        ip = ipaddress.ip_address(host)
        if not _is_ip_allowed(ip):
            raise SSRFBlockedError(f"Blocked IP: {ip}")
        return
    except ValueError:
        pass
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    for addr in _resolved_ips(host, port):
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not _is_ip_allowed(ip):
            raise SSRFBlockedError(f"Hostname {host!r} resolves to blocked IP {ip}")


def safe_httpx_client(**kwargs: Any) -> httpx.Client:
    """
    httpx Client with default timeouts. Call assert_url_allowed(url) before each request
    when the URL is not a fixed first-party endpoint.
    """
    t = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    return httpx.Client(timeout=t, follow_redirects=False, **kwargs)


def read_response_body_cap(response: httpx.Response, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """Read response body up to max_bytes (SSRF response size limit)."""
    data = response.content
    if len(data) > max_bytes:
        raise SSRFBlockedError("Response body exceeds maximum allowed size")
    return data
