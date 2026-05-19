"""Authentication routes.

Login is a two-step process when 2FA is enabled:
  1. POST /auth/login → on success, store user_id in session and redirect to /auth/2fa
  2. POST /auth/2fa   → verify TOTP token → flask_login.login_user(...)
"""

from __future__ import annotations

import base64
import io
import json
import secrets
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_babel import gettext as _
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from app.blueprints.auth import bp
from app.blueprints.auth.forms import (
    ChangePasswordForm,
    Enable2FAForm,
    LoginForm,
    RegisterForm,
    TwoFactorForm,
)
from app.extensions import db, limiter
from app.models.user import User
from app.services.audit import audit
from app.services.crypto import (
    aead_decrypt,
    aead_encrypt,
    constant_time_eq,
    hash_password,
    password_needs_rehash,
    verify_password,
)


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------


def _public_login_enabled() -> bool:
    """True when the public login page (/auth/login) is allowed.

    The ADMIN_LOGIN_PATH bypass is checked separately in the view.
    """
    from app.models.settings import get_settings

    s = get_settings()
    return True if s is None else bool(s.public_login_enabled)


def _is_bypass_request() -> bool:
    """The current request is being served via the admin-bypass URL."""
    return request.path == current_app.config.get("ADMIN_LOGIN_PATH", "/admin-login")


@bp.route("/login", methods=["GET", "POST"], endpoint="login")
@limiter.limit("10 per minute")
def login():
    # Public login disabled by admin? Refuse the public URL, but allow the
    # admin-bypass URL to reach the same view.
    if not _public_login_enabled() and not _is_bypass_request():
        abort(404)

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.email == form.email.data.lower()))
        if user is None or not user.is_active or not verify_password(user.password_hash, form.password.data):
            audit("auth.login.failed", subject=form.email.data.lower())
            flash(_("Invalid e-mail or password."), "danger")
            return render_template("auth/login.html", form=form)

        # Successful primary auth
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(form.password.data)

        user.failed_login_count = 0
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        if user.totp_enabled:
            session["pending_2fa_user_id"] = user.id
            session["pending_2fa_remember"] = bool(form.remember.data)
            return redirect(url_for("auth.two_factor"))

        login_user(user, remember=bool(form.remember.data))
        audit("auth.login.success", actor_user_id=user.id)
        return redirect(request.args.get("next") or url_for("main.index"))

    return render_template("auth/login.html", form=form)


@bp.route("/2fa", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def two_factor():
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, user_id)
    if user is None or not user.totp_enabled:
        session.pop("pending_2fa_user_id", None)
        return redirect(url_for("auth.login"))

    form = TwoFactorForm()
    if form.validate_on_submit():
        token = form.token.data.strip().replace(" ", "")
        ok = False
        if user.totp_secret_encrypted:
            secret = aead_decrypt(user.totp_secret_encrypted).decode()
            totp = pyotp.TOTP(secret)
            if totp.verify(token, valid_window=1):
                ok = True

        # Try backup codes if the TOTP didn't match
        if not ok and user.backup_codes_encrypted:
            codes_json = aead_decrypt(user.backup_codes_encrypted).decode()
            codes: list[str] = json.loads(codes_json)
            for c in codes:
                if constant_time_eq(c, token):
                    codes.remove(c)
                    user.backup_codes_encrypted = aead_encrypt(json.dumps(codes).encode())
                    ok = True
                    break

        if ok:
            remember = session.pop("pending_2fa_remember", False)
            session.pop("pending_2fa_user_id", None)
            login_user(user, remember=remember)
            db.session.commit()
            audit("auth.login.success", actor_user_id=user.id, detail={"method": "2fa"})
            return redirect(request.args.get("next") or url_for("main.index"))

        audit("auth.login.failed", actor_user_id=user.id, detail={"reason": "bad_2fa"})
        flash(_("Invalid two-factor code."), "danger")

    return render_template("auth/two_factor.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    audit("auth.logout", actor_user_id=int(current_user.id))
    logout_user()
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Registration (only when FEATURE_REGISTRATION is true)
# ---------------------------------------------------------------------------


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():
    from app.models.settings import get_settings

    s = get_settings()
    runtime_on = True if s is None else bool(s.public_registration_enabled)
    if not current_app.config["FEATURE_REGISTRATION"] or not runtime_on:
        abort(404)

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        existing = db.session.scalar(select(User).where(User.email == email))
        if existing:
            # Don't leak which e-mails are registered — generic message
            flash(_("If that e-mail is available, your account was created. You can log in."), "info")
            return redirect(url_for("auth.login"))
        user = User(email=email, password_hash=hash_password(form.password.data))
        db.session.add(user)
        db.session.commit()
        audit("auth.register", actor_user_id=user.id)
        flash(_("Account created. Please sign in."), "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


# ---------------------------------------------------------------------------
# Account settings
# ---------------------------------------------------------------------------


@bp.get("/account")
@login_required
def account():
    return render_template("auth/account.html", user=current_user)


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not verify_password(current_user.password_hash, form.current_password.data):
            flash(_("Current password is incorrect."), "danger")
        else:
            current_user.password_hash = hash_password(form.new_password.data)
            db.session.commit()
            audit("auth.password.changed", actor_user_id=int(current_user.id))
            flash(_("Password updated."), "success")
            return redirect(url_for("auth.account"))
    return render_template("auth/change_password.html", form=form)


# ---------------------------------------------------------------------------
# 2FA setup
# ---------------------------------------------------------------------------


@bp.route("/account/2fa", methods=["GET", "POST"])
@login_required
def setup_2fa():
    if current_user.totp_enabled:
        return render_template("auth/2fa_enabled.html", user=current_user)

    # Generate a pending secret (kept in session until verified)
    secret = session.get("pending_totp_secret")
    if not secret:
        secret = pyotp.random_base32()
        session["pending_totp_secret"] = secret

    issuer = current_app.config["APP_NAME"]
    uri = pyotp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name=issuer)

    # Render QR as data URL (no external requests)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    form = Enable2FAForm()
    if form.validate_on_submit():
        if pyotp.TOTP(secret).verify(form.token.data, valid_window=1):
            current_user.totp_secret_encrypted = aead_encrypt(secret.encode())
            current_user.totp_enabled = True
            # Generate 10 backup codes
            codes = [secrets.token_hex(5) for _ in range(10)]
            current_user.backup_codes_encrypted = aead_encrypt(json.dumps(codes).encode())
            db.session.commit()
            session.pop("pending_totp_secret", None)
            audit("auth.2fa.enabled", actor_user_id=int(current_user.id))
            return render_template("auth/2fa_backup_codes.html", codes=codes)
        flash(_("That code didn't match. Try again."), "danger")

    return render_template(
        "auth/setup_2fa.html",
        form=form,
        secret=secret,
        qr_data_url=qr_data_url,
    )


@bp.post("/account/2fa/disable")
@login_required
def disable_2fa():
    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    current_user.backup_codes_encrypted = None
    db.session.commit()
    audit("auth.2fa.disabled", actor_user_id=int(current_user.id))
    flash(_("Two-factor authentication disabled."), "warning")
    return redirect(url_for("auth.account"))
