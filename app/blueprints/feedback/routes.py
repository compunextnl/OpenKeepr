from __future__ import annotations

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_babel import gettext as _

from app.blueprints.feedback import bp
from app.blueprints.feedback.forms import FeedbackForm
from app.extensions import db, limiter
from app.models.feedback import Feedback
from app.services.audit import audit
from app.version import __version__


@bp.route("/", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def submit():
    form = FeedbackForm()
    if form.validate_on_submit():
        # Honeypot — silently accept then drop
        if form.website.data:
            audit("feedback.submitted", subject="honeypot", detail={"dropped": True})
            flash(_("Thanks! Your feedback has been received."), "success")
            return redirect(url_for("main.index"))

        fb = Feedback(
            type=form.type.data,
            message=form.message.data.strip(),
            contact=(form.contact.data or "").strip() or None,
            page=request.referrer,
            user_agent=request.headers.get("User-Agent", "")[:255] or None,
            app_version=__version__,
            language=session.get("lang") or current_app.config["DEFAULT_LANGUAGE"],
        )
        db.session.add(fb)
        db.session.commit()
        audit("feedback.submitted", subject=str(fb.id), detail={"type": fb.type, "via": "web"})
        flash(_("Thanks! Your feedback has been received."), "success")
        return redirect(url_for("main.index"))

    return render_template("feedback/submit.html", form=form)
