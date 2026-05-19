"""Filesystem storage for attachment ciphertext blobs.

Layout:
    instance/attachments/<message_public_id>/<attachment_public_id>.bin

Helpers here never touch plaintext — they only move opaque bytes around.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from flask import current_app


def attachments_root() -> Path:
    root = Path(current_app.instance_path) / "attachments"
    root.mkdir(parents=True, exist_ok=True)
    return root


def message_dir(message_public_id: str) -> Path:
    p = attachments_root() / message_public_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def blob_path(message_public_id: str, attachment_public_id: str) -> Path:
    return message_dir(message_public_id) / f"{attachment_public_id}.bin"


def save_blob(message_public_id: str, attachment_public_id: str, data: bytes) -> int:
    """Write ciphertext to disk. Returns the byte count."""
    path = blob_path(message_public_id, attachment_public_id)
    # Write to a temporary file then rename — avoids partial files on disk full.
    tmp = path.with_suffix(".bin.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return path.stat().st_size


def read_blob(message_public_id: str, attachment_public_id: str) -> bytes:
    path = blob_path(message_public_id, attachment_public_id)
    return path.read_bytes()


def delete_blob(message_public_id: str, attachment_public_id: str) -> None:
    path = blob_path(message_public_id, attachment_public_id)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def delete_message_dir(message_public_id: str) -> int:
    """Remove the entire directory for a message. Returns bytes freed."""
    p = attachments_root() / message_public_id
    if not p.exists():
        return 0
    freed = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    shutil.rmtree(p, ignore_errors=True)
    return freed
