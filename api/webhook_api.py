"""
Webhook API: external systems can trigger events via POST /webhooks/{source}.

POST /webhooks/{source} - Ingest webhook; body: { "event_type": "...", "payload": {...} }
Requires X-Signature: HMAC-SHA256(secret, raw_body) in hex. Secret from WEBHOOK_SECRET or WEBHOOK_SECRET_<SOURCE>.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import os

from fastapi import APIRouter, HTTPException, Request

from api.security_logger import log_failed_webhook_verification
from api.schemas.task_responses import WebhookIngestResponse
from engine.webhook_engine import process_webhook


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _get_webhook_secret(source: str) -> str | None:
    """Return secret for signature verification: WEBHOOK_SECRET_<SOURCE> or WEBHOOK_SECRET."""
    source_upper = source.replace("-", "_").upper()
    per_source = os.environ.get(f"WEBHOOK_SECRET_{source_upper}", "").strip()
    if per_source:
        return per_source
    return os.environ.get("WEBHOOK_SECRET", "").strip() or None


def _verify_webhook_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
    """Verify X-Signature equals HMAC-SHA256(secret, payload) in hex. Constant-time compare."""
    if not signature_header or not secret:
        return False
    expected = hmac.new(
        secret.encode("utf-8") if isinstance(secret, str) else secret,
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


@router.post("/{source}")
async def ingest_webhook(source: str, request: Request):
    """
    Receive a webhook from an external system. Source must be allowed (e.g. github, slack).
    Requires X-Signature: HMAC-SHA256(secret, raw_body) in hex. Secret from WEBHOOK_SECRET or WEBHOOK_SECRET_<SOURCE>.
    """
    client_host = request.client.host if request.client else ""
    body = await request.body()

    secret = _get_webhook_secret(source)
    if not secret:
        log_failed_webhook_verification(source, "WEBHOOK_SECRET not configured", client_host)
        raise HTTPException(status_code=501, detail="Webhook verification not configured")

    signature = request.headers.get("X-Signature", "")
    if not _verify_webhook_signature(secret, body, signature):
        log_failed_webhook_verification(source, "Invalid or missing X-Signature", client_host)
        raise HTTPException(status_code=401, detail="Invalid or missing X-Signature")

    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log_failed_webhook_verification(source, f"Invalid JSON: {e}", client_host)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event_type = data.get("event_type")
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type required")

    try:
        task_ids = process_webhook(source, event_type, payload)
        return WebhookIngestResponse(
            status="accepted",
            source=source,
            event_type=event_type,
            tasks_queued=len(task_ids),
            task_ids=task_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
