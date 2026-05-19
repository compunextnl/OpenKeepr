from __future__ import annotations

from flask import render_template, url_for

from app.blueprints.main import bp


@bp.get("/")
def index():
    # The landing page IS the message composer — quickest path for users.
    return render_template("main/index.html")


@bp.get("/about")
def about():
    return render_template("main/about.html")


@bp.get("/release-notes")
def release_notes():
    """Render CHANGELOG.md from the repo root."""
    from pathlib import Path

    import markdown

    repo_root = Path(__file__).resolve().parents[3]
    changelog = repo_root / "CHANGELOG.md"
    raw = changelog.read_text(encoding="utf-8") if changelog.exists() else "_No changelog yet._"
    html = markdown.markdown(raw, extensions=["fenced_code", "tables", "toc"])
    return render_template("main/release_notes.html", body=html)


@bp.get("/docs/api")
def api_docs():
    """Render docs/api.md."""
    from pathlib import Path

    import markdown
    from flask import abort, current_app

    # Honour both the env-level kill switch and the runtime toggle.
    from app.models.settings import get_settings

    settings = get_settings()
    runtime_on = True if settings is None else bool(settings.api_enabled)
    if not current_app.config["FEATURE_API"] or not runtime_on:
        abort(404)

    repo_root = Path(__file__).resolve().parents[3]
    doc = repo_root / "docs" / "api.md"
    raw = doc.read_text(encoding="utf-8") if doc.exists() else "_API documentation not found._"
    html = markdown.markdown(
        raw, extensions=["fenced_code", "tables", "toc", "codehilite"]
    )
    return render_template("main/api_docs.html", body=html)


@bp.post("/set-language/<lang>")
def set_language(lang: str):
    """Persist the user's language preference in a cookie + session."""
    from flask import current_app, make_response, redirect, request, session

    available = current_app.config["AVAILABLE_LANGUAGES"]
    if lang in available:
        session["lang"] = lang
    next_url = request.referrer or url_for("main.index")
    resp = make_response(redirect(next_url))
    if lang in available:
        resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=False)
    return resp
