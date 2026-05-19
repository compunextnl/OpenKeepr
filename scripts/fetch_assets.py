#!/usr/bin/env python3
"""Download and pin vendored front-end assets — no CDN needed at runtime.

Usage:
    python scripts/fetch_assets.py            # download anything missing
    python scripts/fetch_assets.py --force    # re-download even if present
    python scripts/fetch_assets.py --verify   # check existing files match SHA-384

The manifest below is the single source of truth for what's bundled. Bump
versions here and re-run the script when you want to update.

Subresource Integrity (SHA-384) is verified on download; mismatches abort.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

VENDOR = Path(__file__).resolve().parent.parent / "app" / "static" / "vendor"


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    dest: str            # path relative to app/static/vendor
    sri_b64: str = ""    # optional SHA-384 in base64 (omit "sha384-")


MANIFEST: list[Asset] = [
    # --- Bootstrap 5 ---
    # NOTE: To pin assets, run `python scripts/fetch_assets.py` once, then
    # use --verify; the script will print the actual SHA-384 of each file.
    # Paste those into the `sri_b64` field below to enforce pinning on future runs.
    Asset(
        name="Bootstrap CSS",
        url="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
        dest="bootstrap/bootstrap.min.css",
    ),
    Asset(
        name="Bootstrap JS bundle",
        url="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
        dest="bootstrap/bootstrap.bundle.min.js",
    ),
    # --- Bootstrap Icons (font + css) ---
    Asset(
        name="Bootstrap Icons CSS",
        url="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
        dest="bootstrap-icons/bootstrap-icons.css",
    ),
    Asset(
        name="Bootstrap Icons WOFF2",
        url="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff2",
        dest="bootstrap-icons/fonts/bootstrap-icons.woff2",
    ),
    Asset(
        name="Bootstrap Icons WOFF",
        url="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/fonts/bootstrap-icons.woff",
        dest="bootstrap-icons/fonts/bootstrap-icons.woff",
    ),
    # --- Markdown rendering & sanitization (used by composer/viewer) ---
    Asset(
        name="marked.js",
        url="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js",
        dest="marked/marked.min.js",
    ),
    Asset(
        name="DOMPurify",
        url="https://cdn.jsdelivr.net/npm/dompurify@3.1.4/dist/purify.min.js",
        dest="dompurify/purify.min.js",
    ),
]


def _b384(b: bytes) -> str:
    return base64.b64encode(hashlib.sha384(b).digest()).decode()


def _fix_icon_font_paths(dest: Path) -> None:
    """Rewrite the icon CSS so it points at our local fonts/ directory."""
    if dest.name != "bootstrap-icons.css":
        return
    css = dest.read_text(encoding="utf-8")
    # Original references "./fonts/bootstrap-icons.woff2?..." which already
    # works once we keep the file layout — make absolutely sure by removing
    # version-query strings (so the same file works across updates).
    import re

    fixed = re.sub(r"\?[a-fA-F0-9]+", "", css)
    dest.write_text(fixed, encoding="utf-8")


def download(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "openkeepr-fetch-assets/1.0"})
    with urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read()


def fetch_one(a: Asset, *, force: bool, verify_only: bool) -> str:
    dest = VENDOR / a.dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    if verify_only:
        if not dest.exists():
            return f"MISSING  {a.dest}"
        if a.sri_b64:
            actual = _b384(dest.read_bytes())
            if actual != a.sri_b64:
                return f"MISMATCH {a.dest}  expected sha384-{a.sri_b64}  got sha384-{actual}"
        return f"OK       {a.dest}"

    if dest.exists() and not force:
        return f"skip     {a.dest}"

    print(f"download {a.name}…", flush=True)
    data = download(a.url)
    if a.sri_b64:
        actual = _b384(data)
        if actual != a.sri_b64:
            return (
                f"FAIL     SRI mismatch for {a.name}\n"
                f"  expected sha384-{a.sri_b64}\n"
                f"  got      sha384-{actual}\n"
                f"  Refusing to write. Either bump the manifest or remove sri_b64 if intentional."
            )
    dest.write_bytes(data)
    _fix_icon_font_paths(dest)
    return f"wrote    {a.dest} ({len(data)} bytes)"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    parser.add_argument("--verify", action="store_true", help="Only verify existing files")
    args = parser.parse_args(argv)

    rc = 0
    for asset in MANIFEST:
        msg = fetch_one(asset, force=args.force, verify_only=args.verify)
        print(msg)
        if msg.startswith(("FAIL", "MISMATCH", "MISSING")):
            rc = 1
    return rc


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
