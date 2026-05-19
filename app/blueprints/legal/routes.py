"""Privacy / cookies / security.txt — text-only pages, no tracking.

`security.txt` is generated dynamically so its `Expires:` field stays current
(re-anchored every request to NOW + SECURITY_EXPIRES_DAYS). This way you
never need to manually rotate it — no annual reminder needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Response, current_app, render_template, url_for

from app.blueprints.legal import bp


@bp.get("/privacy")
def privacy():
    return render_template("legal/privacy.html")


@bp.get("/cookies")
def cookies():
    return render_template("legal/cookies.html")


@bp.get("/security")
def security_policy():
    """Human-readable security policy linked from security.txt."""
    return render_template("legal/security.html")


@bp.get("/.well-known/security.txt")
def security_txt():
    """RFC 9116 security.txt — auto-renewed each request.

    The `Expires:` line is always set to NOW + SECURITY_EXPIRES_DAYS so it
    never goes stale. Sign with PGP at deploy time if you want stricter
    integrity (out of scope for this build).
    """
    cfg = current_app.config
    expires_in = cfg["SECURITY_EXPIRES_DAYS"]
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    policy_url = cfg["SECURITY_POLICY_URL"] or (cfg["BASE_URL"].rstrip("/") + url_for("legal.security_policy"))
    lines = [
        f"Contact: {cfg['SECURITY_CONTACT']}",
        f"Expires: {expires_at}",
        f"Policy: {policy_url}",
        "Preferred-Languages: en, nl",
        f"Canonical: {cfg['BASE_URL'].rstrip('/')}/.well-known/security.txt",
        "",
        "# This file is generated dynamically; the Expires field is renewed",
        "# on every request, so it can never go stale.",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain")
