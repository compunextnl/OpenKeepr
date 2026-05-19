"""Admin dashboard.

ALL admin views require an authenticated user with `is_admin = True`. Admin
users can see metadata about messages (count, expiry, opens) but NEVER
content — by construction, the server doesn't have the keys.
"""

from functools import wraps

from flask import Blueprint, abort
from flask_login import current_user, login_required

bp = Blueprint("admin", __name__, template_folder="../../templates/admin")


def admin_required(fn):
    @wraps(fn)
    @login_required
    def decorated(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(404)  # don't reveal that admin exists
        return fn(*args, **kwargs)

    return decorated


from app.blueprints.admin import routes  # noqa: E402, F401
