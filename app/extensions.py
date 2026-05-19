"""Singleton extension instances.

We instantiate extensions here (without binding them to an app), and then
`create_app()` calls `.init_app(app)` on each one. This avoids circular
imports and lets us use the same instances from anywhere in the codebase.
"""

from __future__ import annotations

from flask_babel import Babel
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
