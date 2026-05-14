"""
Structured security event logging for audit and incident response.

Logs: failed webhook verification, unauthorized access (401/403),
rate limit violations. Use standard logging with JSON-friendly extra fields.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

# Use a dedicated logger so handlers can be attached (e.g. file, SIEM).
logger = logging.getLogger("security")

# Optional: emit as single-line JSON for log aggregators.
LOG_AS_JSON = os.environ.get("SECURITY_LOG_JSON", "").strip().lower() in ("1", "true", "yes")


def _extra(event: str, **kwargs: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"event": event, **kwargs}
    return out


def log_failed_webhook_verification(source: str, reason: str, client_host: str | None = None) -> None:
    """Log when webhook X-Signature verification fails."""
    logger.warning(
        "Webhook verification failed: source=%s reason=%s client=%s",
        source,
        reason,
        client_host or "",
        extra=_extra("failed_webhook_verification", source=source, reason=reason, client_host=client_host or ""),
    )


def log_unauthorized_access(
    detail: str,
    path: str | None = None,
    client_host: str | None = None,
    status_code: int = 401,
) -> None:
    """Log 401/403 responses for audit."""
    logger.warning(
        "Unauthorized access: detail=%s path=%s client=%s status=%s",
        detail,
        path or "",
        client_host or "",
        status_code,
        extra=_extra(
            "unauthorized_access",
            detail=detail,
            path=path or "",
            client_host=client_host or "",
            status_code=status_code,
        ),
    )


def log_rate_limit_exceeded(
    client_key: str,
    path: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """Log when a client exceeds rate limit."""
    logger.warning(
        "Rate limit exceeded: client=%s path=%s limit=%s window=%s",
        client_key,
        path,
        limit,
        window_seconds,
        extra=_extra(
            "rate_limit_exceeded",
            client_key=client_key,
            path=path,
            limit=limit,
            window_seconds=window_seconds,
        ),
    )


def log_failed_login(email: str, reason: str, client_host: str | None = None, path: str | None = None) -> None:
    """Log failed login attempt."""
    logger.warning(
        "Failed login: email=%s reason=%s client=%s path=%s",
        email,
        reason,
        client_host or "",
        path or "",
        extra=_extra("failed_login", email=email, reason=reason, client_host=client_host or "", path=path or ""),
    )


def log_invalid_jwt(reason: str, client_host: str | None = None, path: str | None = None) -> None:
    """Log invalid or expired JWT."""
    logger.warning(
        "Invalid JWT: reason=%s client=%s path=%s",
        reason,
        client_host or "",
        path or "",
        extra=_extra("invalid_jwt", reason=reason, client_host=client_host or "", path=path or ""),
    )


def log_unauthorized_project_access(
    user_id: str | int,
    project_id: str,
    client_host: str | None = None,
    path: str | None = None,
) -> None:
    """Log 403 when user tries to access a project they are not in."""
    logger.warning(
        "Unauthorized project access: user_id=%s project_id=%s client=%s path=%s",
        user_id,
        project_id,
        client_host or "",
        path or "",
        extra=_extra("unauthorized_project_access", user_id=user_id, project_id=project_id, client_host=client_host or "", path=path or ""),
    )


def log_request_body_too_large(
    content_length: int,
    limit: int,
    client_host: str | None = None,
    path: str | None = None,
) -> None:
    """Log when request body exceeds allowed size (413)."""
    logger.warning(
        "Request body too large: content_length=%s limit=%s client=%s path=%s",
        content_length,
        limit,
        client_host or "",
        path or "",
        extra=_extra("request_body_too_large", content_length=content_length, limit=limit, client_host=client_host or "", path=path or ""),
    )


def log_agent_timeout(task_id: int | None, agent_name: str | None, timeout_seconds: int) -> None:
    """Log when agent execution exceeds timeout."""
    logger.warning(
        "Agent execution timeout: task_id=%s agent=%s timeout_seconds=%s",
        task_id,
        agent_name or "",
        timeout_seconds,
        extra=_extra("agent_timeout", task_id=task_id, agent_name=agent_name or "", timeout_seconds=timeout_seconds),
    )


def log_memory_limit_exceeded(task_id: int | None, agent_name: str | None) -> None:
    """Log when agent execution hits MemoryError."""
    logger.warning(
        "Memory limit exceeded: task_id=%s agent=%s",
        task_id,
        agent_name or "",
        extra=_extra("memory_limit_exceeded", task_id=task_id, agent_name=agent_name or ""),
    )


def log_tool_execution_timeout(tool_name: str, timeout_seconds: int, task_id: int | None = None) -> None:
    """Log when tool execution exceeds timeout."""
    logger.warning(
        "Tool execution timeout: tool=%s timeout_seconds=%s task_id=%s",
        tool_name,
        timeout_seconds,
        task_id,
        extra=_extra("tool_execution_timeout", tool_name=tool_name, timeout_seconds=timeout_seconds, task_id=task_id),
    )


def log_tool_response_too_large(tool_name: str, size: int, limit: int, task_id: int | None = None) -> None:
    """Log when tool response exceeds allowed size."""
    logger.warning(
        "Tool response too large: tool=%s size=%s limit=%s task_id=%s",
        tool_name,
        size,
        limit,
        task_id,
        extra=_extra("tool_response_too_large", tool_name=tool_name, size=size, limit=limit, task_id=task_id),
    )


def log_refresh_token_used(user_id: int, client_host: str | None = None, path: str | None = None) -> None:
    """Log successful refresh token use (before rotation)."""
    logger.info(
        "Refresh token used: user_id=%s client=%s path=%s",
        user_id,
        client_host or "",
        path or "",
        extra=_extra("refresh_token_used", user_id=user_id, client_host=client_host or "", path=path or ""),
    )


def log_refresh_token_revoked(user_id: int, reason: str, client_host: str | None = None, path: str | None = None) -> None:
    """Log when a refresh token is revoked (logout or rotation)."""
    logger.info(
        "Refresh token revoked: user_id=%s reason=%s client=%s path=%s",
        user_id,
        reason,
        client_host or "",
        path or "",
        extra=_extra("refresh_token_revoked", user_id=user_id, reason=reason, client_host=client_host or "", path=path or ""),
    )


def log_invalid_refresh_attempt(reason: str, client_host: str | None = None, path: str | None = None) -> None:
    """Log invalid or expired refresh token attempt."""
    logger.warning(
        "Invalid refresh attempt: reason=%s client=%s path=%s",
        reason,
        client_host or "",
        path or "",
        extra=_extra("invalid_refresh_attempt", reason=reason, client_host=client_host or "", path=path or ""),
    )


def log_logout_event(user_id: int, client_host: str | None = None, path: str | None = None) -> None:
    """Log explicit logout."""
    logger.info(
        "Logout: user_id=%s client=%s path=%s",
        user_id,
        client_host or "",
        path or "",
        extra=_extra("logout_event", user_id=user_id, client_host=client_host or "", path=path or ""),
    )
