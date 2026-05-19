from __future__ import annotations

import os
import secrets
import tempfile

import pytest

# Set env BEFORE importing the app
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(32))
os.environ.setdefault("RECIPIENT_HASH_SECRET", secrets.token_urlsafe(32))
os.environ.setdefault("SERVER_ENCRYPTION_KEY", secrets.token_urlsafe(32))
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")
os.environ.setdefault("AUTO_COMPILE_TRANSLATIONS", "false")
os.environ.setdefault("MAIL_ENABLED", "false")


@pytest.fixture()
def app(tmp_path_factory):
    from app import create_app

    db_dir = tmp_path_factory.mktemp("db")
    app = create_app(config_overrides={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_dir/'test.db'}",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        from app.extensions import db

        db.create_all()
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()
