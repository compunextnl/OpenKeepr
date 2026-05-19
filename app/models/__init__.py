"""Database models.

Importing this package registers all models with SQLAlchemy so Flask-Migrate
can autogenerate migrations.
"""

from app.models.api_key import ApiKey  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.message import Message, RecipientHash, VerificationCode  # noqa: F401
from app.models.settings import Settings  # noqa: F401
from app.models.user import User  # noqa: F401
