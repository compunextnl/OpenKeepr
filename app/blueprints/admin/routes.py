from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from sqlalchemy import desc, func, select

from flask import current_app

from app.blueprints.admin import admin_required, bp
from app.blueprints.admin.forms import FeedbackUpdateForm, SettingsForm, TestEmailForm
from app.extensions import db
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.feedback import Feedback
from app.models.message import Message
from app.models.settings import get_settings
from app.models.user import User
from app.services.audit import audit


@bp.get("/")
@admin_required
def dashboard():
    from pathlib import Path

    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # On-disk usage: SQLite file + attachment blob directory
    instance = Path(current_app.instance_path)
    db_bytes = 0
    db_file = instance / "openkeepr.db"
    if db_file.exists():
        db_bytes = db_file.stat().st_size
    attach_root = instance / "attachments"
    attach_bytes = 0
    attach_files = 0
    if attach_root.exists():
        for f in attach_root.rglob("*"):
            if f.is_file():
                attach_bytes += f.stat().st_size
                attach_files += 1

    stats = {
        "users": db.session.scalar(select(func.count(User.id))),
        "messages_total": db.session.scalar(select(func.count(Message.id))),
        "messages_24h": db.session.scalar(
            select(func.count(Message.id)).where(Message.created_at >= last_24h)
        ),
        "active_keys": db.session.scalar(
            select(func.count(ApiKey.id)).where(ApiKey.revoked.is_(False))
        ),
        "feedback_new": db.session.scalar(
            select(func.count(Feedback.id)).where(Feedback.status == "new")
        ),
        "db_bytes": db_bytes,
        "attach_bytes": attach_bytes,
        "attach_files": attach_files,
        "total_bytes": db_bytes + attach_bytes,
    }
    recent_events = db.session.scalars(
        select(AuditLog).order_by(desc(AuditLog.at)).limit(20)
    ).all()
    return render_template("admin/dashboard.html", stats=stats, recent_events=recent_events)


# ---------------------------------------------------------------------------
# Settings (maintenance mode, banner, defaults)
# ---------------------------------------------------------------------------


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    s = get_settings()
    form = SettingsForm(obj=s)
    if form.validate_on_submit():
        was_maintenance = bool(s.maintenance_mode)
        form.populate_obj(s)
        db.session.commit()
        if was_maintenance != bool(s.maintenance_mode):
            audit(
                "admin.maintenance.enabled" if s.maintenance_mode else "admin.maintenance.disabled"
            )
        audit("admin.setting.changed")
        flash(_("Settings saved."), "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", form=form, settings=s)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@bp.get("/audit")
@admin_required
def audit_log():
    page = max(1, int(request.args.get("page", 1)))
    per_page = 50
    event_type = request.args.get("type") or None

    q = select(AuditLog).order_by(desc(AuditLog.at))
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    total = db.session.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.session.scalars(q.offset((page - 1) * per_page).limit(per_page)).all()
    return render_template(
        "admin/audit.html",
        rows=rows,
        page=page,
        per_page=per_page,
        total=total or 0,
        event_type=event_type or "",
    )


# ---------------------------------------------------------------------------
# Feedback inbox
# ---------------------------------------------------------------------------


@bp.get("/feedback")
@admin_required
def feedback_list():
    status = request.args.get("status") or "new"
    q = select(Feedback).order_by(desc(Feedback.created_at))
    if status != "all":
        q = q.where(Feedback.status == status)
    items = db.session.scalars(q.limit(200)).all()
    return render_template("admin/feedback_list.html", items=items, status=status)


@bp.route("/feedback/<int:item_id>", methods=["GET", "POST"])
@admin_required
def feedback_detail(item_id: int):
    item = db.session.get(Feedback, item_id)
    if item is None:
        flash(_("Feedback not found."), "warning")
        return redirect(url_for("admin.feedback_list"))
    form = FeedbackUpdateForm(obj=item)
    if form.validate_on_submit():
        item.status = form.status.data
        item.admin_notes = form.admin_notes.data
        db.session.commit()
        flash(_("Feedback updated."), "success")
        return redirect(url_for("admin.feedback_detail", item_id=item.id))
    return render_template("admin/feedback_detail.html", item=item, form=form)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@bp.get("/users")
@admin_required
def users():
    items = db.session.scalars(select(User).order_by(User.id)).all()
    return render_template("admin/users.html", items=items)


@bp.post("/users/<int:user_id>/toggle-active")
@admin_required
def toggle_user_active(user_id: int):
    u = db.session.get(User, user_id)
    if u and not u.is_admin:
        u.is_active_flag = not u.is_active_flag
        db.session.commit()
        audit("user.locked" if not u.is_active_flag else "user.unlocked", subject=str(u.id))
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# API keys (per-user management)
# ---------------------------------------------------------------------------


@bp.get("/api-keys")
@admin_required
def api_keys():
    items = db.session.scalars(select(ApiKey).order_by(desc(ApiKey.created_at))).all()
    return render_template("admin/api_keys.html", items=items)


@bp.post("/cleanup/run")
@admin_required
def run_cleanup_now():
    """Trigger the scheduled cleanup synchronously, then return to the dashboard."""
    from app.services.cleanup import purge_expired_messages, purge_old_verification_codes

    msgs = purge_expired_messages(max_retention_days=current_app.config["MAX_RETENTION_DAYS"])
    codes = purge_old_verification_codes()
    flash(_("Cleanup finished — purged %(m)d message(s) and %(c)d expired code(s).", m=msgs, c=codes), "success")
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------------------------
# Outbound e-mail tester
# ---------------------------------------------------------------------------


@bp.route("/email-test", methods=["GET", "POST"])
@admin_required
def email_test():
    from app.services.email_service import send_test_email

    form = TestEmailForm()
    if not form.to_email.data and request.method == "GET":
        # Pre-fill with the admin's own e-mail for convenience
        from flask_login import current_user

        form.to_email.data = getattr(current_user, "email", "")

    outcome = None
    if form.validate_on_submit() and form.to_email.data:
        outcome = send_test_email(to_email=form.to_email.data.strip())
        if outcome.sent:
            audit("admin.email.test.sent", detail={"provider": outcome.provider})
            flash(_("Test e-mail sent via %(p)s.", p=outcome.provider), "success")
        else:
            audit(
                "admin.email.test.failed",
                detail={"provider": outcome.provider, "error": (outcome.error or "")[:200]},
            )
            flash(_("Could not send: %(e)s", e=outcome.error or "unknown error"), "danger")

    cfg = current_app.config
    config_snapshot = {
        "MAIL_ENABLED": cfg["MAIL_ENABLED"],
        "MAIL_BACKEND": cfg["MAIL_BACKEND"],
        "MAIL_FROM": cfg["MAIL_FROM"],
        "SMTP_HOST": cfg.get("SMTP_HOST", ""),
        "SMTP_PORT": cfg.get("SMTP_PORT", ""),
        "SMTP_USERNAME": cfg.get("SMTP_USERNAME", ""),
        "SMTP_USE_TLS": cfg.get("SMTP_USE_TLS", False),
        "SMTP_USE_SSL": cfg.get("SMTP_USE_SSL", False),
        "SMTP_PASSWORD_SET": bool(cfg.get("SMTP_PASSWORD")),
        "POSTMARK_TOKEN_SET": bool(cfg.get("POSTMARK_API_TOKEN")),
        "SENDGRID_KEY_SET": bool(cfg.get("SENDGRID_API_KEY")),
        "MAILGUN_KEY_SET": bool(cfg.get("MAILGUN_API_KEY")),
    }
    return render_template(
        "admin/email_test.html",
        form=form,
        outcome=outcome,
        cfg=config_snapshot,
    )
