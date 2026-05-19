"""Authentication: register, login (with 2FA), password reset, settings."""

from flask import Blueprint

bp = Blueprint("auth", __name__, template_folder="../../templates/auth")

from app.blueprints.auth import routes  # noqa: E402, F401
