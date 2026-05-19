"""Production WSGI entry point for gunicorn / uWSGI.

Example:
    gunicorn -c deploy/gunicorn.conf.py wsgi:application
"""

from __future__ import annotations

from app import create_app

application = create_app()
