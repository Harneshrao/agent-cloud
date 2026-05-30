"""
Production safety checks — fail fast on insecure defaults when ENVIRONMENT=production.
"""

from __future__ import annotations

import logging
import os
import sys

_log = logging.getLogger("production_guard")

_INSECURE_JWT_SECRETS = frozenset(
    {
        "agent-cloud-secret",
        "change-me-in-production",
        "changeme",
        "secret",
    }
)


def is_production() -> bool:
    env = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip().lower()
    return env in ("production", "prod")


def assert_production_safety() -> None:
    """
    Raise RuntimeError on critical misconfig in production.
    Logs warnings in non-production for weak settings.
    """
    if os.environ.get("DISABLE_PRODUCTION_GUARD", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return

    anon = os.environ.get("ALLOW_ANONYMOUS_DEV", "").strip().lower()
    jwt_secret = (os.environ.get("JWT_SECRET") or "agent-cloud-secret").strip()
    require_docker = os.environ.get("REQUIRE_DOCKER_FOR_DEPLOYMENTS", "").strip().lower()

    issues: list[str] = []
    if is_production():
        if anon in ("1", "true", "yes"):
            issues.append("ALLOW_ANONYMOUS_DEV must be disabled in production")
        if not jwt_secret or jwt_secret.lower() in _INSECURE_JWT_SECRETS:
            issues.append("JWT_SECRET must be set to a strong random value in production")
        if require_docker not in ("1", "true", "yes"):
            issues.append(
                "REQUIRE_DOCKER_FOR_DEPLOYMENTS=1 recommended in production "
                "(untrusted agent code)"
            )
        if issues:
            msg = "Production safety check failed: " + "; ".join(issues)
            _log.error(msg)
            raise RuntimeError(msg)
    else:
        if anon in ("1", "true", "yes"):
            _log.warning("ALLOW_ANONYMOUS_DEV is enabled — not for production")
        if jwt_secret.lower() in _INSECURE_JWT_SECRETS:
            _log.warning("JWT_SECRET is using a default value — change before production")


def check_emergency_disable(action: str) -> None:
    """Raise if global kill switch env is set (e.g. DISABLE_TASK_ENQUEUE)."""
    if action == "enqueue" and os.environ.get("DISABLE_TASK_ENQUEUE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        raise RuntimeError("Task enqueue is disabled (DISABLE_TASK_ENQUEUE)")


def abort_startup_on_fatal(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)
