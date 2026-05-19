"""Application factory.

Building the app in a function (rather than at module scope) lets us:
- pass overrides in tests,
- run multiple instances side-by-side,
- keep import side-effects minimal.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config
from app.extensions import babel, csrf, db, limiter, login_manager, migrate
from app.version import __version__


def _configure_logging(app: Flask) -> None:
    level = getattr(logging, app.config["LOG_LEVEL"].upper(), logging.INFO)
    handlers: list[logging.Handler] = []
    if app.config["LOG_FILE"]:
        handlers.append(logging.FileHandler(app.config["LOG_FILE"]))
    handlers.append(logging.StreamHandler())
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)
    app.logger.setLevel(level)


def _select_locale() -> str:
    """Locale selector for Flask-Babel.

    Order of precedence:
    1. `?lang=xx` query param (lets users force a language)
    2. `lang` cookie (sticky preference)
    3. Accept-Language header
    4. Default from config
    """
    from flask import current_app, session

    available: list[str] = current_app.config["AVAILABLE_LANGUAGES"]
    forced = request.args.get("lang")
    if forced and forced in available:
        session["lang"] = forced
        return forced
    sticky = session.get("lang") or request.cookies.get("lang")
    if sticky and sticky in available:
        return sticky
    best = request.accept_languages.best_match(available)
    return best or current_app.config["DEFAULT_LANGUAGE"]


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.api.v1 import bp as api_v1_bp
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.feedback import bp as feedback_bp
    from app.blueprints.legal import bp as legal_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.messages import bp as messages_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(legal_bp)
    if app.config["FEATURE_FEEDBACK"]:
        app.register_blueprint(feedback_bp, url_prefix="/feedback")
    if app.config["FEATURE_API"]:
        app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
        # CSRF must be disabled for API routes — they use API-key auth instead.
        csrf.exempt(api_v1_bp)

    # Register the admin-bypass login URL (separate from /auth/login) so that
    # admins can always reach the login form even when public login is off.
    admin_login_path = app.config.get("ADMIN_LOGIN_PATH", "/admin-login")
    if admin_login_path and admin_login_path != "/auth/login":
        from app.blueprints.auth.routes import login as login_view

        app.add_url_rule(
            admin_login_path,
            endpoint="auth.admin_login",
            view_func=login_view,
            methods=["GET", "POST"],
        )


def _register_error_handlers(app: Flask) -> None:
    from flask import render_template

    @app.errorhandler(404)
    def not_found(_e):  # type: ignore[no-untyped-def]
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(_e):  # type: ignore[no-untyped-def]
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(_e):  # type: ignore[no-untyped-def]
        return render_template("errors/500.html"), 500


def _register_context_processors(app: Flask) -> None:
    from datetime import datetime, timezone

    from flask import g
    from flask_babel import gettext

    @app.context_processor
    def inject_globals() -> dict:  # type: ignore[no-untyped-def]
        from flask_babel import get_locale

        from app.models.settings import get_settings

        try:
            settings = get_settings()
        except Exception:  # tables may not yet exist on first migration
            settings = None
        try:
            locale = str(get_locale() or app.config["DEFAULT_LANGUAGE"])
        except Exception:
            locale = app.config["DEFAULT_LANGUAGE"]

        # Effective flags = env flag AND runtime setting. Either side being
        # off disables the feature.
        def _eff(env_key: str, settings_attr: str, default_on: bool = True) -> bool:
            env_on = bool(app.config.get(env_key, default_on))
            runtime_on = True if settings is None else bool(getattr(settings, settings_attr, True))
            return env_on and runtime_on

        return {
            "app_name": app.config["APP_NAME"],
            "app_version": app.config["APP_VERSION"],
            "github_url": app.config["GITHUB_URL"],
            "buymeacoffee_url": app.config["BUYMEACOFFEE_URL"],
            "available_languages": app.config["AVAILABLE_LANGUAGES"],
            "language_meta": LANGUAGE_META,
            "current_year": datetime.now(timezone.utc).year,
            "feature_feedback": app.config["FEATURE_FEEDBACK"],
            "feature_cookie_banner": app.config["FEATURE_COOKIE_BANNER"],
            "feature_api": _eff("FEATURE_API", "api_enabled"),
            "feature_registration": _eff("FEATURE_REGISTRATION", "public_registration_enabled"),
            "feature_login": True if settings is None else bool(settings.public_login_enabled),
            "settings": settings,
            "current_locale": locale,
            "_": gettext,
        }


def _register_security_headers(app: Flask) -> None:
    from flask import make_response

    csp = (
        # Default deny + explicit allowances. We only serve our own static
        # assets — no CDNs. 'unsafe-inline' on style is needed for Bootstrap
        # utilities; we keep script-src strict. No inline previews of
        # attachments, so frame-src / object-src inherit the strict default.
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    @app.after_request
    def add_security_headers(response):  # type: ignore[no-untyped-def]
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


def _maintenance_gate(app: Flask) -> None:
    """Block all requests when maintenance mode is on, except admin & static."""
    from flask import g, redirect, render_template, request, url_for
    from flask_login import current_user

    @app.before_request
    def check_maintenance():  # type: ignore[no-untyped-def]
        from app.models.settings import get_settings

        settings = get_settings()
        if not settings or not settings.maintenance_mode:
            return None
        # Always-allowed paths
        path = request.path
        if (
            path.startswith("/static/")
            or path.startswith("/auth/")
            or path.startswith("/admin/")
            or path == "/healthz"
            or path == "/.well-known/security.txt"
        ):
            return None
        # Admins bypass the gate
        if current_user.is_authenticated and getattr(current_user, "is_admin", False):
            return None
        return render_template("errors/maintenance.html"), 503


def _bootstrap_admin(app: Flask) -> None:
    """If no admin exists, create one and print/log the initial password once."""
    from app.models.user import User
    from app.services.bootstrap import ensure_initial_admin

    with app.app_context():
        ensure_initial_admin(app.logger)


def _init_translations(app: Flask) -> None:
    """Optionally extract & compile translations on startup.

    This keeps `.po` files merged with the latest source strings without
    requiring the operator to run a script.
    """
    if not app.config["AUTO_COMPILE_TRANSLATIONS"]:
        return
    from app.services.translations import sync_translations

    try:
        sync_translations(app)
    except Exception as exc:  # pragma: no cover — never block startup on i18n
        app.logger.warning("Translation sync failed: %s", exc)


def _start_scheduler(app: Flask) -> None:
    if app.config.get("TESTING"):
        return
    # Avoid double-scheduling under the dev reloader (which forks).
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.config["DEBUG"]:
        from app.services.scheduler import start_background_jobs

        start_background_jobs(app)


# Map ISO-639-1 locale → display metadata. Used by the language switcher.
# `flag` is the basename of an SVG file under app/static/img/flags/ —
# rendered as an <img>, which works identically across Mac, Linux & Windows
# browsers (unlike regional-indicator emoji which depend on system fonts).
LANGUAGE_META: dict[str, dict[str, str]] = {
    "en": {"flag": "gb", "name": "English"},
    "nl": {"flag": "nl", "name": "Nederlands"},
    "fr": {"flag": "fr", "name": "Français"},
    "de": {"flag": "de", "name": "Deutsch"},
    "es": {"flag": "es", "name": "Español"},
    "it": {"flag": "it", "name": "Italiano"},
}


def create_app(*, config_overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="static",
        template_folder="templates",
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    # Base config from Config dataclass
    cfg = Config()
    cfg.APP_VERSION = __version__
    app.config.from_object(cfg)
    if config_overrides:
        app.config.update(config_overrides)

    # If using sqlite with a relative path, resolve it inside instance/
    db_uri: str = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///") and not db_uri.startswith("sqlite:////"):
        db_path = Path(app.instance_path) / db_uri.replace("sqlite:///", "")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    _configure_logging(app)
    app.logger.info("%s %s starting (env=%s)", app.config["APP_NAME"], __version__, app.config["ENV"])

    # Reverse proxy support (only when explicitly configured)
    hops = app.config["PROXY_FIX_HOPS"]
    if hops > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops, x_port=hops, x_prefix=hops
        )

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    limiter.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)

    # Make sure models are imported so SQLAlchemy sees them
    from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str):  # type: ignore[no-untyped-def]
        from app.models.user import User

        return db.session.get(User, int(user_id))

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_context_processors(app)
    _register_jinja_filters(app)
    _register_security_headers(app)
    _maintenance_gate(app)

    # Healthcheck for ops
    @app.get("/healthz")
    def healthz():  # type: ignore[no-untyped-def]
        return {"status": "ok", "version": __version__}

    # First-time setup
    _init_translations(app)
    _ensure_schema(app)
    _bootstrap_admin(app)
    _start_scheduler(app)

    return app


def _register_jinja_filters(app: Flask) -> None:
    """Custom Jinja filters — chiefly `|localtime` for TZ-aware display."""
    from datetime import datetime as _dt
    from datetime import timezone as _tz

    try:
        from zoneinfo import ZoneInfo  # stdlib (Python 3.9+)
    except ImportError:  # pragma: no cover
        ZoneInfo = None  # type: ignore[assignment]

    def localtime(value, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """Render a UTC datetime (naive or aware) in the configured TIMEZONE.

        DB timestamps are stored UTC-naive; this filter is the canonical way
        to show them to the user. Use everywhere `.strftime()` was used.
        """
        if value is None:
            return ""
        if isinstance(value, _dt):
            if value.tzinfo is None:
                value = value.replace(tzinfo=_tz.utc)
            if ZoneInfo is not None:
                try:
                    value = value.astimezone(ZoneInfo(app.config.get("TIMEZONE", "UTC")))
                except Exception:  # noqa: BLE001 — fall back to UTC on bad TZ
                    pass
            return value.strftime(fmt)
        return str(value)

    app.jinja_env.filters["localtime"] = localtime


def _ensure_schema(app: Flask) -> None:
    """Create tables on first run + add any new columns that models gained.

    Convenient for fresh installs and small upgrades (so the operator can
    just `git pull && systemctl restart` without learning Alembic). For
    complex migrations, the operator uses Flask-Migrate.
    """
    from sqlalchemy import inspect, text

    with app.app_context():
        try:
            insp = inspect(db.engine)
            tables = set(insp.get_table_names())
            if "users" not in tables:
                app.logger.info("First-time setup: creating database schema…")
                db.create_all()
            else:
                # Existing install — create any tables that didn't exist in a
                # previous version (e.g. `attachments` was added in v1.2.0).
                # `create_all` is idempotent and only touches missing tables.
                expected = set(db.metadata.tables.keys())
                missing = expected - tables
                if missing:
                    app.logger.info("Schema upgrade: creating new table(s): %s", sorted(missing))
                    db.create_all()
            tables = set(inspect(db.engine).get_table_names())

            # Light-touch additive migration: for every mapped model, ADD COLUMN
            # for any field that isn't in the table yet. SQLite supports this
            # for nullable / default-bearing columns, which covers all our
            # additions to date.
            for mapper in db.Model.registry.mappers:
                table = mapper.local_table
                if table.name not in tables:
                    continue
                existing = {c["name"] for c in insp.get_columns(table.name)}
                for col in table.columns:
                    if col.name in existing:
                        continue
                    coltype = col.type.compile(dialect=db.engine.dialect)
                    nullable = "" if col.nullable else " NOT NULL"
                    default = ""
                    if col.default is not None and getattr(col.default, "is_scalar", False):
                        val = col.default.arg
                        if isinstance(val, bool):
                            default = f" DEFAULT {1 if val else 0}"
                        elif isinstance(val, (int, float)):
                            default = f" DEFAULT {val}"
                        elif isinstance(val, str):
                            default = f" DEFAULT '{val}'"
                    sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}{default}{nullable}'
                    app.logger.info("Schema upgrade: %s", sql)
                    db.session.execute(text(sql))
            db.session.commit()
        except Exception:  # noqa: BLE001
            app.logger.exception("Could not ensure schema (will retry on next start)")
            db.session.rollback()
