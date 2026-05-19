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
    session,
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
    from email_validator import EmailNotValidError, validate_email

    raw_input: list[str] = [r for r in (data.get("recipients") or []) if r and r.strip()]
    valid_recipients: list[str] = []
    invalid_recipients: list[str] = []
    for r in raw_input:
        try:
            info = validate_email(r.strip(), check_deliverability=False)
            valid_recipients.append(info.normalized.lower())
        except EmailNotValidError:
            invalid_recipients.append(r.strip())
    if invalid_recipients:
        return (
            jsonify(
                error="invalid_recipients",
                invalid=invalid_recipients,
                message="One or more recipient e-mail addresses are not valid.",
            ),
            400,
        )
    # de-dup while preserving order
    _seen: set[str] = set()
    recipients_raw = [r for r in valid_recipients if not (r in _seen or _seen.add(r))]
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
    attachments_meta = [
        {"id": a.public_id, "size": a.size_bytes}
        for a in msg.attachments
    ]
    return render_template(
        "messages/view.html",
        public_id=msg.public_id,
        requires_email=msg.requires_recipient_email,
        requires_code=msg.security_code_hash is not None,
        is_markdown=msg.is_markdown,
        expires_at=msg.expires_at.replace(tzinfo=timezone.utc).isoformat(),
        max_opens=msg.max_opens,
        opens=msg.opens,
        attachments=attachments_meta,
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
        # Throttle: if we issued a code for this e-mail within the last 30
        # seconds and it's still valid, do NOT create a new one and do NOT
        # send another mail. Protects against double-clicks, browser
        # prefetches and duplicate-tab requests.
        throttle_window = timedelta(seconds=30)
        recent = next(
            (
                v for v in sorted(
                    msg.verification_codes,
                    key=lambda v: v.created_at, reverse=True,
                )
                if v.email_hash == email_hash
                and not v.consumed
                and v.attempts < 5
                and v.expires_at.replace(tzinfo=timezone.utc) > _utcnow()
                and (_utcnow() - v.created_at.replace(tzinfo=timezone.utc)) < throttle_window
            ),
            None,
        )
        if recent is not None:
            audit("verification.sent", subject=public_id, detail={"reused": True})
            return jsonify(ok=True, message="If your e-mail is allowed, a code has been sent."), 200

        # Invalidate any older, still-pending codes for this e-mail so that
        # only the freshly-issued one can succeed. Stops the "first mail's
        # code is wrong" surprise when a new mail is issued later.
        for v in msg.verification_codes:
            if v.email_hash == email_hash and not v.consumed:
                v.consumed = True

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
    # Mark this message as "unlocked" for the current browser session so
    # subsequent attachment downloads don't have to re-verify the code.
    # Note: we DO NOT purge attachment files here on auto-burn — the same
    # session is allowed to download attachments it just unlocked. The
    # background cleanup job will free the bytes within ~10 minutes, and the
    # `/burn` endpoint (explicit user action) purges immediately.
    session[f"unlocked:{public_id}"] = True

    return jsonify(
        ciphertext_b64=base64.b64encode(msg.ciphertext).decode("ascii"),
        iv_b64=base64.b64encode(msg.iv).decode("ascii"),
        salt_b64=base64.b64encode(msg.salt).decode("ascii"),
        is_markdown=msg.is_markdown,
        opens=msg.opens,
        max_opens=msg.max_opens,
        burned=msg.burned,
        attachments=[
            {"id": a.public_id, "size": a.size_bytes}
            for a in msg.attachments
        ],
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
    _purge_burned_now(msg)
    audit("message.burned", subject=public_id)
    return jsonify(ok=True), 200


def _purge_burned_now(msg: "Message") -> None:
    """Remove the on-disk attachment blobs immediately after a burn.

    The DB row + verification codes stick around until the scheduled cleanup
    job (within ~10 minutes), but admin storage stats should drop to the
    expected value right away, and we don't want the bytes on disk longer
    than strictly necessary.
    """
    try:
        from app.services.attachments import delete_message_dir

        delete_message_dir(msg.public_id)
    except Exception:  # noqa: BLE001
        current_app.logger.exception("Failed to purge attachment dir for %s", msg.public_id)


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


def _attachments_enabled() -> bool:
    return bool(current_app.config.get("ATTACHMENTS_ENABLED", True))


@bp.post("/m/<public_id>/attachments")
@limiter.limit("60 per hour")
def upload_attachment(public_id: str):
    """Upload one encrypted attachment for an existing message.

    The browser must POST multipart/form-data with:
      - `iv`         (binary, 12 bytes)
      - `ciphertext` (binary, the encrypted blob — filename+MIME+bytes inside)

    The server NEVER sees the plaintext.
    """
    if not _attachments_enabled():
        return jsonify(error="attachments_disabled"), 404

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None or msg.is_expired:
        return jsonify(error="message_not_found"), 404
    # Attachments can only be added before the recipient first opens the
    # message. After that, the message is sealed — protects the recipient
    # from late tampering by anyone who knows the public ID.
    if msg.opens > 0:
        return jsonify(error="message_sealed"), 403

    iv_file = request.files.get("iv")
    ct_file = request.files.get("ciphertext")
    if iv_file is None or ct_file is None:
        return jsonify(error="missing iv or ciphertext"), 400

    iv = iv_file.read()
    ciphertext = ct_file.read()
    if len(iv) != 12:
        return jsonify(error="iv must be 12 bytes"), 400

    max_file = current_app.config["ATTACHMENTS_MAX_FILE_SIZE_MB"] * 1024 * 1024
    max_total = current_app.config["ATTACHMENTS_MAX_TOTAL_MB"] * 1024 * 1024
    max_count = current_app.config["ATTACHMENTS_MAX_PER_MESSAGE"]

    if len(ciphertext) > max_file:
        return jsonify(error="file_too_large", limit_bytes=max_file), 413
    if len(msg.attachments) >= max_count:
        return jsonify(error="too_many_attachments", limit=max_count), 413
    total_so_far = sum(a.size_bytes for a in msg.attachments)
    if total_so_far + len(ciphertext) > max_total:
        return jsonify(error="total_size_exceeded", limit_bytes=max_total), 413

    from app.models.attachment import Attachment, generate_attachment_id
    from app.services.attachments import save_blob

    att_public_id = generate_attachment_id()
    size = save_blob(msg.public_id, att_public_id, ciphertext)
    att = Attachment(
        public_id=att_public_id,
        message_id=msg.id,
        iv=iv,
        size_bytes=size,
    )
    db.session.add(att)
    db.session.commit()
    audit("attachment.uploaded", subject=public_id, detail={"att_id": att_public_id, "size": size})
    return jsonify(id=att.public_id, size_bytes=size), 201


@bp.post("/m/<public_id>/a/<att_id>")
@limiter.limit("60 per hour")
def reveal_attachment(public_id: str, att_id: str):
    """Stream an attachment ciphertext to the client, after gate verification.

    Uses the same gate as `reveal`: the client must POST {email?, code?}.
    The server returns the raw ciphertext bytes; decryption happens client-side.
    """
    if not _attachments_enabled():
        return jsonify(error="attachments_disabled"), 404

    from flask import Response

    msg = db.session.scalar(select(Message).where(Message.public_id == public_id))
    if msg is None:
        return jsonify(error="message_not_found"), 404

    # The attachment is only accessible to a browser session that has already
    # passed the message reveal gate (see /reveal). No need to re-verify the
    # code on every file download.
    if not session.get(f"unlocked:{public_id}"):
        return jsonify(error="message_not_unlocked"), 403

    # Note: we deliberately do NOT bail out here when `msg.is_expired` is
    # True. Revealing the message body via /reveal can flip the burned flag
    # immediately (max_opens=1 + burn-after-reading), and the same browser
    # session must still be able to download the attachments it just saw.
    # The cleanup job will physically delete the blob soon enough.

    att = next((a for a in msg.attachments if a.public_id == att_id), None)
    if att is None:
        return jsonify(error="attachment_not_found"), 404

    from app.services.attachments import read_blob

    try:
        body = read_blob(public_id, att_id)
    except FileNotFoundError:
        return jsonify(error="blob_missing"), 410

    audit("attachment.downloaded", subject=public_id, detail={"att_id": att_id})
    # Use application/octet-stream so the browser doesn't try to interpret.
    # Send the IV as a custom header for the client to grab without a second roundtrip.
    return Response(
        body,
        mimetype="application/octet-stream",
        headers={
            "X-OpenKeepr-IV": base64.b64encode(att.iv).decode("ascii"),
            "Cache-Control": "private, no-store",
            "Content-Length": str(len(body)),
        },
    )
