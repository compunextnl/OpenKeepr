"""E-mail delivery.

Two providers are wired in:
  - "smtp"       — works against any SMTP server (default)
  - "postmark"   — HTTP API
  - "sendgrid"   — HTTP API
  - "mailgun"    — HTTP API

Per the user's chosen workflow, MAIL_ENABLED defaults to False — recipients
get their 6-digit code via the sender's preferred out-of-band channel. When
the operator turns mail on, the code can additionally be e-mailed.

This module intentionally never raises in the request path: e-mail failures
are logged and surface as a friendly UI error.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

import requests
from flask import current_app

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailOutcome:
    sent: bool
    provider: str
    error: str | None = None


def _provider() -> str:
    return current_app.config["MAIL_BACKEND"].lower()


def is_enabled() -> bool:
    return bool(current_app.config["MAIL_ENABLED"])


def send_test_email(*, to_email: str) -> EmailOutcome:
    """Send a self-contained test message — used by the admin SMTP tester.

    Unlike `send_verification_code`, this bypasses MAIL_ENABLED so the admin
    can validate credentials before flipping the flag.
    """
    from datetime import datetime, timezone

    name = current_app.config["APP_NAME"]
    subject = f"{name} test e-mail"
    body_text = (
        "Hi,\n\n"
        f"This is a test e-mail from your {name} instance.\n"
        f"Sent at: {datetime.now(timezone.utc).isoformat()}\n"
        f"Provider: {_provider()}\n\n"
        "If you received this message, your outbound mail configuration is working.\n"
        f"You can now safely set MAIL_ENABLED=true in your .env if you want {name}\n"
        "to deliver recipient verification codes by e-mail."
    )
    return _dispatch(to=to_email, subject=subject, body_text=body_text)


def send_verification_code(*, to_email: str, code: str, message_url: str) -> EmailOutcome:
    """Send the 6-digit verification code to a recipient.

    `to_email` is plaintext — used ONLY for delivery and never persisted.
    """
    if not is_enabled():
        log.info("Mail disabled; not sending verification code to <hashed>")
        return EmailOutcome(sent=False, provider="disabled", error="MAIL_ENABLED=false")

    name = current_app.config["APP_NAME"]
    subject = f"Your {name} verification code"
    body_text = (
        f"Someone shared a secure message with you on {name}.\n\n"
        f"Verification code: {code}\n"
        f"Open the message: {message_url}\n\n"
        f"This code expires in {current_app.config['VERIFICATION_CODE_TTL_MINUTES']} minutes.\n"
        f"If you weren't expecting this, you can safely ignore this e-mail."
    )

    return _dispatch(to=to_email, subject=subject, body_text=body_text)


def _dispatch(*, to: str, subject: str, body_text: str) -> EmailOutcome:
    provider = _provider()
    try:
        if provider == "smtp":
            return _send_smtp(to, subject, body_text)
        if provider == "postmark":
            return _send_postmark(to, subject, body_text)
        if provider == "sendgrid":
            return _send_sendgrid(to, subject, body_text)
        if provider == "mailgun":
            return _send_mailgun(to, subject, body_text)
        return EmailOutcome(sent=False, provider=provider, error=f"Unknown provider: {provider}")
    except Exception as exc:  # noqa: BLE001
        log.exception("E-mail send failed via %s", provider)
        return EmailOutcome(sent=False, provider=provider, error=str(exc))


def _send_smtp(to: str, subject: str, body_text: str) -> EmailOutcome:
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)

    if cfg["SMTP_USE_SSL"]:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"], context=ctx, timeout=15) as s:
            if cfg["SMTP_USERNAME"]:
                s.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as s:
            s.ehlo()
            if cfg["SMTP_USE_TLS"]:
                ctx = ssl.create_default_context()
                s.starttls(context=ctx)
                s.ehlo()
            if cfg["SMTP_USERNAME"]:
                s.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
    return EmailOutcome(sent=True, provider="smtp")


def _send_postmark(to: str, subject: str, body_text: str) -> EmailOutcome:
    cfg = current_app.config
    r = requests.post(
        "https://api.postmarkapp.com/email",
        headers={
            "X-Postmark-Server-Token": cfg["POSTMARK_API_TOKEN"],
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"From": cfg["MAIL_FROM"], "To": to, "Subject": subject, "TextBody": body_text},
        timeout=15,
    )
    r.raise_for_status()
    return EmailOutcome(sent=True, provider="postmark")


def _send_sendgrid(to: str, subject: str, body_text: str) -> EmailOutcome:
    cfg = current_app.config
    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {cfg['SENDGRID_API_KEY']}"},
        json={
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": cfg["MAIL_FROM"]},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}],
        },
        timeout=15,
    )
    r.raise_for_status()
    return EmailOutcome(sent=True, provider="sendgrid")


def _send_mailgun(to: str, subject: str, body_text: str) -> EmailOutcome:
    cfg = current_app.config
    r = requests.post(
        f"https://api.mailgun.net/v3/{cfg['MAILGUN_DOMAIN']}/messages",
        auth=("api", cfg["MAILGUN_API_KEY"]),
        data={"from": cfg["MAIL_FROM"], "to": to, "subject": subject, "text": body_text},
        timeout=15,
    )
    r.raise_for_status()
    return EmailOutcome(sent=True, provider="mailgun")
