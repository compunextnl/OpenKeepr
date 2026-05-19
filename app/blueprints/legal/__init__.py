from flask import Blueprint

bp = Blueprint("legal", __name__, template_folder="../../templates/legal")

from app.blueprints.legal import routes  # noqa: E402, F401
