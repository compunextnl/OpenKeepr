"""Development entry point.

Run with:  python run.py
Or:        flask --app run.py run

For production, use `wsgi.py` with gunicorn (see deploy/openkeepr.service).
"""

from __future__ import annotations

from app import create_app
from app.config import load_runtime_config

app = create_app()


if __name__ == "__main__":  # pragma: no cover
    cfg = load_runtime_config()
    app.run(
        host=cfg.host,
        port=cfg.port,
        debug=cfg.debug,
        # Threaded so background scheduler can co-exist with the dev server
        threaded=True,
        # Use the stdlib reloader; werkzeug's is fine for dev only
        use_reloader=cfg.debug,
    )
