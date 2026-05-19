from flask import Blueprint

bp = Blueprint("feedback", __name__, template_folder="../../templates/feedback")

from app.blueprints.feedback import routes  # noqa: E402, F401
