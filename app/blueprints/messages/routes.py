"""Message routes — server-side half of the zero-knowledge flow.

Flow (anonymous-recipient):
  1. Browser generates random 256-bit key K.
  2. Browser encrypts plaintext with AES-256-GCM using K → ciphertext + IV.
  3. Browser POSTs ciphertext+IV+expiry+options to /m/create (NO KEY).
  4. Server stores it, returns `public_id` (+ optional security code).
  5. Sender shares URL: https://host/m/<public_id>#<base64(K)>[:<code>]
  6. Recipient opens URL → browser parses K from fragment → fetches ciphertext
     → optionally prompts for code/e-mail → decrypts → renders.

The server never sees K.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import select

from app.blueprints.messages import bp
from app.extensions import csrf, db, limiter
from app.models.message import (
    Message,
    RecipientHash,
    VerificationCode,
    generate_public_id,
)
from app.services.audit import audit
from app.services.crypto import (
    aead_decrypt,
    aead_encrypt,
    hash_email,
    hash_password,
    random_6digit_code,
    verify_password,
)
from app.services.email_service import is_enabled as mail_is_enabled
from app.services.email_service import send_verification_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_b64(s: str) -> bytes:
    """Lenient base64 decoder for fields coming from the browser."""
    s = s.strip()
    # Accept URL-safe and standard, with or without padding
    s = s.replace("-", "+").replace("_", "/")
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.b64decode(s)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@bp.post("/m/create")
@limiter.limit("30 per hour")
def create():
    """Create a new encrypted message.

    JSON body:
      ciphertext_b64       (str)  required — AES-256-GCM ciphertext (+ auth tag appended)
      iv_b64               (str)  required — 12-byte nonce
      salt_b64             (str)  required — 16-byte random salt (forward-compat)
      is_markdown          (bool) optional, default false
      expires_in_hours     (int)  optional, default DEFAULT_EXPIRY_HOURS
      max_opens            (int)  optional, default null (unlimited)
      recipients           (list[str]) optional — plaintext e-mails, hashed before storage
      use_security_code    (bool) optional — return a 6-digit code if no recipients given
    """
    data = request.get_json(silent=True) or {}

    # --- Validate / size-cap ---
    try:
        ct = _parse_b64(data["ciphertext_b64"])
        iv = _parse_b64(data["iv_b64"])
        salt = _parse_b64(data["salt_b64"])
    except (KeyError, ValueError):
        return jsonify(error="missing or invalid ciphertext/iv/salt"), 400

    max_kb = current_app.config["MAX_MESSAGE_SIZE_KB"]
    if len(ct) > max_kb * 1024:
        return jsonify(error=f"ciphertext exceeds {max_kb} KB limit"), 413
    if len(iv) != 12 or len(salt) not in (16, 32):
        return jsonify(error="iv must be 12 bytes; salt 16 or 32 bytes"), 400

    # --- Expiry ---
    hard_cap_days = current_app.config["MAX_RETENTION_DAYS"]
    default_hours = current_app.config["DEFAULT_EXPIRY_HOURS"]
    try:
        hours = int(data.get("expires_in_hours") or default_hours)
    except (TypeError, ValueError):
        hours = default_hours
    hours = max(1, min(hours, hard_cap_days * 24))
    expires_at = _utcnow() + timedelta(hours=hours)

    # --- Max opens ---
    max_opens_raw = data.get("max_opens")
    max_opens: int | None
    if max_opens_raw in (None, "", 0, "0"):
        max_opens = None
    else:
        try:
            max_opens = max(1, min(int(max_opens_raw), current_app.config["MAX_OPENS_LIMIT"]))
        except (TypeError, ValueError):
            return jsonify(error="invalid max_opens"), 400

    # --- Recipients / security code ---
    recipients_raw: list[str] = data.get("recipients") or []
    recipients_raw = [r.strip().lower() for r in recipients_raw if r and "@" in r]
    use_code = bool(data.get("use_security_code")) or not recipients_raw

    security_code_plain: str | None = None
    security_code_hash: str | None = None
    if not recipients_raw and use_code:
        security_code_plain = random_6digit_code()
        security_code_hash = hash_password(security_code_plain)
    elif not recipients_raw and not use_code:
        # No recipients AND no code — this would make the message readable to
        # anyone with the link, which we allow but warn about in the UI.
        # (Confidentiality still rests on the URL fragment.)
        pass

    # --- Persist ---
    msg = Message(
        public_id=generate_public_id(),
        ciphertext=ct,
        iv=iv,
        salt=salt,
        is_markdown=bool(data.get("is_markdown")),
        expires_at=expires_at,
        max_opens=max_opens,
        security_code_hash=security_code_hash,
        creator_user_id=current_user.id if current_user.is_authenticated else None,
        ciphertext_size=len(ct),
    )
    db.session.add(msg)
    db.session.flush()

    for email in recipients_raw:
        db.session.add(RecipientHash(message_id=msg.id, email_hash=hash_email(email)))

    db.session.commit()
    audit(
        "message.created",
        subject=msg.public_id,
        detail={
            "size": len(ct),
            "max_opens": max_opens,
            "expires_in_hours": hours,
            "has_recipients": bool(recipients_raw),
            "has_security_code": bool(security_code_plain),
            "is_markdown": msg.is_markdown,
        },
    )

    base = current_app.config["BASE_URL"].rstrip("/")
    return jsonify(
        public_id=msg.public_id,
        url=f"{base}/m/{msg.public_id}",
        expires_at=msg.expires_at.replace(tzinfo=timezone.utc).isoformat(),
        max_opens=msg.max_opens,
        security_code=security_code_plain,  # only present when generated — shown ONCE
        requires_email=bool(recipients_raw),
    ), 201


# Tell CSRF this endpoint is JSON (browser fetch from same origin — Flask-WTF
# checks the CSRF token in a header for AJAX).
# We still rely on the SameSite=Lax cookie + CSRF header from app.js.


# ---------------------------------------------------------------------------
# View — landing page that loads the ciphertext via XHR
# ---------------------------------------------------------------------------


@bp.get("/m/<public_id>")
def view(public_id: str):
    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.is_expired:
        return render_template("messages/not_found.html"), 404
    return render_template(
        "messages/view.html",
        public_id=msg.public_id,
        requires_email=msg.requires_recipient_email,
        requires_code=msg.security_code_hash is not None,
        is_markdown=msg.is_markdown,
        expires_at=msg.expires_at.replace(tzinfo=timezone.utc).isoformat(),
        max_opens=msg.max_opens,
        opens=msg.opens,
    )


# ---------------------------------------------------------------------------
# Verification: request a code (only when recipients are set)
# ---------------------------------------------------------------------------


@bp.post("/m/<public_id>/request-code")
@limiter.limit("10 per hour")
def request_code(public_id: str):
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify(error="invalid e-mail"), 400

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.is_expired or not msg.requires_recipient_email:
        return jsonify(error="not eligible"), 400

    email_hash = hash_email(email)
    allowed = any(r.email_hash == email_hash for r in msg.recipients)

    # Constant-response behaviour: we always say "code sent" to avoid leaking
    # which e-mails are on the allow-list.
    if allowed:
        code = random_6digit_code()
        ttl = current_app.config["VERIFICATION_CODE_TTL_MINUTES"]
        vc = VerificationCode(
            message_id=msg.id,
            email_hash=email_hash,
            code_hash=hash_password(code),
            expires_at=_utcnow() + timedelta(minutes=ttl),
        )
        db.session.add(vc)
        db.session.commit()
        if mail_is_enabled():
            outcome = send_verification_code(
                to_email=email,
                code=code,
                message_url=f"{current_app.config['BASE_URL']}/m/{public_id}",
            )
            if outcome.sent:
                audit("verification.sent", subject=public_id, detail={"provider": outcome.provider})
        else:
            # Mail disabled — code is NOT delivered to the recipient. The
            # sender must convey it out-of-band. We don't expose the code via
            # this endpoint; ops/log review only.
            current_app.logger.info(
                "MAIL_ENABLED=false; verification code for msg %s NOT sent. Code (admin-eyes only): %s",
                public_id, code,
            )
            audit("verification.sent", subject=public_id, detail={"provider": "disabled"})

    return jsonify(ok=True, message="If your e-mail is allowed, a code has been sent."), 200


# ---------------------------------------------------------------------------
# Reveal: return ciphertext after passing the gate (e-mail+code OR code only)
# ---------------------------------------------------------------------------


@bp.post("/m/<public_id>/reveal")
@limiter.limit("20 per hour")
def reveal(public_id: str):
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower() or None
    code = (data.get("code") or "").strip() or None
    burn = bool(data.get("burn_after"))

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.is_expired:
        return jsonify(error="expired_or_missing"), 404

    # --- Gate 1: recipient e-mail allow-list ---
    if msg.requires_recipient_email:
        if not email or not code:
            return jsonify(error="email_and_code_required"), 400
        email_hash = hash_email(email)
        if not any(r.email_hash == email_hash for r in msg.recipients):
            audit("verification.failed", subject=public_id, detail={"reason": "email_not_allowed"})
            return jsonify(error="invalid_credentials"), 403

        # Find a non-consumed code for this e-mail, newest first
        vc = next(
            (
                v
                for v in sorted(
                    msg.verification_codes,
                    key=lambda v: v.created_at,
                    reverse=True,
                )
                if v.email_hash == email_hash
                and not v.consumed
                and v.expires_at.replace(tzinfo=timezone.utc) > _utcnow()
                and v.attempts < 5
            ),
            None,
        )
        if vc is None:
            return jsonify(error="invalid_credentials"), 403
        vc.attempts += 1
        if not verify_password(vc.code_hash, code):
            db.session.commit()
            audit("verification.failed", subject=public_id, detail={"reason": "bad_code"})
            return jsonify(error="invalid_credentials"), 403
        vc.consumed = True
        db.session.commit()
        audit("verification.verified", subject=public_id)

    # --- Gate 2: anonymous security code ---
    elif msg.security_code_hash is not None:
        if not code:
            return jsonify(error="code_required"), 400
        if not verify_password(msg.security_code_hash, code):
            audit("verification.failed", subject=public_id, detail={"reason": "bad_code"})
            return jsonify(error="invalid_credentials"), 403

    # --- Reveal ---
    msg.opens += 1
    if burn or (msg.max_opens is not None and msg.opens >= msg.max_opens):
        msg.burned = True
    db.session.commit()
    audit("message.viewed", subject=public_id, detail={"opens": msg.opens, "burned": msg.burned})

    return jsonify(
        ciphertext_b64=base64.b64encode(msg.ciphertext).decode("ascii"),
        iv_b64=base64.b64encode(msg.iv).decode("ascii"),
        salt_b64=base64.b64encode(msg.salt).decode("ascii"),
        is_markdown=msg.is_markdown,
        opens=msg.opens,
        max_opens=msg.max_opens,
        burned=msg.burned,
    ), 200


# ---------------------------------------------------------------------------
# Burn: recipient-initiated immediate destruction
# ---------------------------------------------------------------------------


@bp.post("/m/<public_id>/burn")
@limiter.limit("30 per hour")
def burn(public_id: str):
    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None:
        return jsonify(ok=True), 200  # idempotent
    msg.burned = True
    db.session.commit()
    audit("message.burned", subject=public_id)
    return jsonify(ok=True), 200
