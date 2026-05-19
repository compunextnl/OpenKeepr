"""Gunicorn config for production.

Used by:  gunicorn -c deploy/gunicorn.conf.py wsgi:application
"""

from __future__ import annotations

import multiprocessing
import os

# Bind to a Unix socket by default — nginx talks to us through it.
# Override with GUNICORN_BIND=0.0.0.0:8000 if you must.
bind = os.environ.get("GUNICORN_BIND", "unix:/run/openkeepr/openkeepr.sock")

# 2*CPU + 1 is the classic rule of thumb. Override with GUNICORN_WORKERS.
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker class: sync is fine for OpenKeepr (no long-poll endpoints).
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")
threads = int(os.environ.get("GUNICORN_THREADS", 4))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = 30
keepalive = 5

# Logs to stdout/stderr so journald captures them.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(L)s "%(f)s" "%(a)s"'

# Limit request size to a sane number — Flask enforces ciphertext size separately.
limit_request_line = 8190
limit_request_field_size = 8190

# Pre-load the app — avoids per-worker startup overhead.
preload_app = True

# When running behind nginx on a Unix socket, ProxyFix in app/__init__.py
# uses PROXY_FIX_HOPS=1 to trust forwarded headers.
forwarded_allow_ips = "*"

# Don't write a PID file by default — systemd tracks the main PID via
# Type=notify, so a stale PID file from a crashed run can only hurt.
pidfile = None
