"""Public landing pages."""

from flask import Blueprint

bp = Blueprint("main", __name__, template_folder="../../templates/main")

from app.blueprints.main import routes  # noqa: E402, F401
