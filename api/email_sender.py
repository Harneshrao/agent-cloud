"""
Send emails: verification and password reset.

Uses SMTP if SMTP_HOST, SMTP_USER, SMTP_PASSWORD are set; otherwise logs in development.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "noreply@agent-cloud.local")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip().rstrip("/")


def _send_mail(to_email: str, subject: str, body: str, log_label: str = "email") -> None:
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, to_email, msg.as_string())
            logger.info("%s sent to %s", log_label, to_email)
        except Exception as e:
            logger.exception("Failed to send %s: %s", log_label, e)
    else:
        logger.info("%s (mock): to=%s subject=%s", log_label, to_email, subject)


def send_verification_email(to_email: str, verify_link: str) -> None:
    """Send email verification link. 24h expiry."""
    subject = "Agent Cloud – Verify your email"
    body = f"""Welcome to Agent Cloud.

Please verify your email by clicking the link below (link expires in 24 hours):

{verify_link}

If you did not create an account, you can ignore this email.
"""
    _send_mail(to_email, subject, body, "Verification email")


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """Send password reset email. 15 min expiry."""
    subject = "Agent Cloud – Reset your password"
    body = f"""You requested a password reset for Agent Cloud.

Click the link below to set a new password (link expires in 15 minutes):

{reset_link}

If you did not request this, you can ignore this email.
"""
    _send_mail(to_email, subject, body, "Password reset email")
