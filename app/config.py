"""Application configuration.

All settings are sourced from environment variables (loaded via python-dotenv
from a `.env` file in development). Required secrets fail-fast on boot if
unset in production.
"""

from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env early — but never override real environment variables that may
# already be set by systemd / the shell.
load_dotenv(override=False)


_INLINE_COMMENT = re.compile(r"\s+#.*$")


def _str(name: str, default: str = "") -> str:
    """Read a string env var, defensive against inline `# comment` leftovers.

    python-dotenv strips inline comments for non-empty values, but the
    behaviour is fragile when the value before the `#` is whitespace-only.
    We normalise here so that `KEY=    # explanation` always resolves to "".
    URL fragments (e.g. https://example.com/#x) are preserved because we
    only strip when `#` is preceded by whitespace.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    val = raw.strip()
    if val.startswith("#"):  # comment-only line, no real value
        return default
    val = _INLINE_COMMENT.sub("", val).strip()
    return val or default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bool(name: str, default: bool = False) -> bool:
    value = _str(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = _str(name)
    if not value:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list(name: str, default: list[str] | None = None, sep: str = ",") -> list[str]:
    raw = _str(name)
    if not raw:
        return list(default or [])
    return [item.strip() for item in raw.split(sep) if item.strip()]


def _required(name: str, *, allow_dev_fallback: bool = True) -> str:
    """Read a required env var; in dev, fall back to an ephemeral secret.

    In production (FLASK_ENV=production) we refuse to start without a real value.
    """
    value = os.environ.get(name, "").strip()
    if value and value != "changeme-please-generate-a-real-key":
        return value
    env = os.environ.get("FLASK_ENV", "development").lower()
    if env == "production" or not allow_dev_fallback:
        raise RuntimeError(
            f"Refusing to start: {name} is not set. Generate one with:\n"
            "  python -c \"import secrets;print(secrets.token_urlsafe(64))\"\n"
            "and put it in your .env file."
        )
    # Dev fallback — ephemeral, regenerated every restart. Sessions don't
    # survive a restart in dev, which is fine.
    return secrets.token_urlsafe(48)


def _normalise_bmc(value: str) -> str:
    """Accept either a full BuyMeACoffee URL or just a username."""
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://www.buymeacoffee.com/{value.lstrip('/')}"


# ---------------------------------------------------------------------------
# Runtime config (used by run.py to pick host/port — separate from Flask config)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    debug: bool


def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        host=_str("HOST", "127.0.0.1"),
        port=_int("PORT", 5000),
        debug=_bool("DEBUG", default=_str("FLASK_ENV", "development") != "production"),
    )


# ---------------------------------------------------------------------------
# Flask config class
# ---------------------------------------------------------------------------


@dataclass
class Config:
    # Identity
    ENV: str = _str("FLASK_ENV", "development")
    DEBUG: bool = _bool("DEBUG", default=_str("FLASK_ENV", "development") != "production")
    TESTING: bool = False

    # Branding — overridable by operators that fork the app.
    # BUYMEACOFFEE_URL accepts either a full URL or just the username; we
    # normalise to https://www.buymeacoffee.com/<username> if no scheme given.
    APP_NAME: str = _str("APP_NAME", "OpenKeepr")
    GITHUB_URL: str = _str("GITHUB_URL", "https://github.com/OWNER/openkeepr")
    BUYMEACOFFEE_URL: str = field(default_factory=lambda: _normalise_bmc(_str("BUYMEACOFFEE_URL")))

    # Secrets
    SECRET_KEY: str = field(default_factory=lambda: _required("SECRET_KEY"))
    RECIPIENT_HASH_SECRET: bytes = field(
        default_factory=lambda: _required("RECIPIENT_HASH_SECRET").encode()
    )
    SERVER_ENCRYPTION_KEY: str = field(
        default_factory=lambda: _required("SERVER_ENCRYPTION_KEY")
    )

    # URLs
    BASE_URL: str = field(default_factory=lambda: _str("BASE_URL", "http://127.0.0.1:5000").rstrip("/"))
    PREFERRED_URL_SCHEME: str = _str("PREFERRED_URL_SCHEME", "http")
    ALLOWED_HOSTS: list[str] = field(default_factory=lambda: _list("ALLOWED_HOSTS", ["*"]))

    # Database — paths are resolved against instance/
    SQLALCHEMY_DATABASE_URI: str = _str("DATABASE_URL", "sqlite:///openkeepr.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = field(
        default_factory=lambda: {
            # Helps SQLite play nice with multiple threads / scheduler.
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": True,
        }
    )

    # Sessions / cookies
    SESSION_COOKIE_SECURE: bool = _bool("SESSION_COOKIE_SECURE", default=False)
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    PERMANENT_SESSION_LIFETIME: int = 60 * 60 * 8  # 8 hours

    # CSRF
    WTF_CSRF_TIME_LIMIT: int | None = None  # tie to session
    WTF_CSRF_SSL_STRICT: bool = _bool("SESSION_COOKIE_SECURE", default=False)

    # Message limits (hard caps)
    MAX_MESSAGE_SIZE_KB: int = _int("MAX_MESSAGE_SIZE_KB", 256)
    MAX_RETENTION_DAYS: int = _int("MAX_RETENTION_DAYS", 30)
    DEFAULT_EXPIRY_HOURS: int = _int("DEFAULT_EXPIRY_HOURS", 24)
    MAX_OPENS_LIMIT: int = _int("MAX_OPENS_LIMIT", 100)
    VERIFICATION_CODE_TTL_MINUTES: int = _int("VERIFICATION_CODE_TTL_MINUTES", 10)

    # Attachments — all enforced client-side AND server-side where possible.
    # NOTE: the server cannot inspect the plaintext file, so ALLOWED_TYPES is a
    # UI-side guard rail (advisory). The server only checks SIZE + COUNT.
    ATTACHMENTS_ENABLED: bool = _bool("ATTACHMENTS_ENABLED", default=True)
    ATTACHMENTS_MAX_FILE_SIZE_MB: int = _int("ATTACHMENTS_MAX_FILE_SIZE_MB", 25)
    ATTACHMENTS_MAX_PER_MESSAGE: int = _int("ATTACHMENTS_MAX_PER_MESSAGE", 10)
    ATTACHMENTS_MAX_TOTAL_MB: int = _int("ATTACHMENTS_MAX_TOTAL_MB", 100)
    # Mix of file extensions (".pdf") and MIME globs ("image/*"). Comma-separated.
    # Empty string == allow everything (NOT recommended).
    ATTACHMENTS_ALLOWED_TYPES: list[str] = field(
        default_factory=lambda: _list(
            "ATTACHMENTS_ALLOWED_TYPES",
            default=[
                ".pdf", ".txt", ".md", ".csv", ".log",
                ".doc", ".docx", ".odt",
                ".xls", ".xlsx", ".ods",
                ".ppt", ".pptx", ".odp",
                ".zip", ".7z", ".tar", ".gz",
                "image/*",
                ".json", ".xml", ".yaml", ".yml",
            ],
        )
    )

    # Mail
    MAIL_ENABLED: bool = _bool("MAIL_ENABLED", default=False)
    MAIL_BACKEND: str = _str("MAIL_BACKEND", "smtp")
    MAIL_FROM: str = _str("MAIL_FROM", "OpenKeepr <noreply@example.com>")
    SMTP_HOST: str = _str("SMTP_HOST")
    SMTP_PORT: int = _int("SMTP_PORT", 587)
    SMTP_USERNAME: str = _str("SMTP_USERNAME")
    SMTP_PASSWORD: str = _str("SMTP_PASSWORD")
    SMTP_USE_TLS: bool = _bool("SMTP_USE_TLS", default=True)
    SMTP_USE_SSL: bool = _bool("SMTP_USE_SSL", default=False)
    POSTMARK_API_TOKEN: str = _str("POSTMARK_API_TOKEN")
    SENDGRID_API_KEY: str = _str("SENDGRID_API_KEY")
    MAILGUN_API_KEY: str = _str("MAILGUN_API_KEY")
    MAILGUN_DOMAIN: str = _str("MAILGUN_DOMAIN")

    # Admin bootstrap
    ADMIN_EMAIL: str = _str("ADMIN_EMAIL", "admin@example.com")
    ADMIN_INITIAL_PASSWORD: str = _str("ADMIN_INITIAL_PASSWORD")
    # Secret URL that always lets admins log in, even when public login is off.
    ADMIN_LOGIN_PATH: str = _str("ADMIN_LOGIN_PATH", "/admin-login")

    # Rate limits
    RATELIMIT_STORAGE_URI: str = _str("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT: str = _str("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_HEADERS_ENABLED: bool = True

    # security.txt
    SECURITY_CONTACT: str = _str("SECURITY_CONTACT", "mailto:security@example.com")
    SECURITY_POLICY_URL: str = _str("SECURITY_POLICY_URL")
    SECURITY_EXPIRES_DAYS: int = _int("SECURITY_EXPIRES_DAYS", 365)

    # i18n
    DEFAULT_LANGUAGE: str = _str("DEFAULT_LANGUAGE", "en")
    AVAILABLE_LANGUAGES: list[str] = field(
        default_factory=lambda: _list("AVAILABLE_LANGUAGES", ["en", "nl", "fr", "de", "es", "it"])
    )
    BABEL_DEFAULT_LOCALE: str = _str("DEFAULT_LANGUAGE", "en")
    BABEL_TRANSLATION_DIRECTORIES: str = "translations"
    AUTO_COMPILE_TRANSLATIONS: bool = _bool("AUTO_COMPILE_TRANSLATIONS", default=True)

    # Timezone — used by Flask-Babel (e.g. `{{ moment|format_datetime }}`),
    # the background scheduler and any timezone-aware operations.
    # All timestamps in the DB remain UTC; this only affects *display*.
    TIMEZONE: str = _str("TIMEZONE", "UTC")
    BABEL_DEFAULT_TIMEZONE: str = field(default_factory=lambda: _str("TIMEZONE", "UTC"))

    # Logging
    LOG_LEVEL: str = _str("LOG_LEVEL", "INFO")
    LOG_FILE: str = _str("LOG_FILE")

    # Feature flags
    FEATURE_REGISTRATION: bool = _bool("FEATURE_REGISTRATION", default=True)
    FEATURE_API: bool = _bool("FEATURE_API", default=True)
    FEATURE_FEEDBACK: bool = _bool("FEATURE_FEEDBACK", default=True)
    FEATURE_COOKIE_BANNER: bool = _bool("FEATURE_COOKIE_BANNER", default=False)

    # Trusted proxies (ProxyFix hops)
    PROXY_FIX_HOPS: int = _int("PROXY_FIX_HOPS", 0 if _str("FLASK_ENV", "development") != "production" else 1)

    # Internal — populated by app factory
    APP_VERSION: str = ""
    REPO_ROOT: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent)
