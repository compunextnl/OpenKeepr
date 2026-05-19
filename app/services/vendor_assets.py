"""Vendor-asset bootstrapper — keeps `app/static/vendor/` populated at startup.

Mirrors the translations-sync pattern: on app boot, scan the manifest in
``scripts/fetch_assets.py`` and download anything that's missing. Failures are
logged (not fatal) so a temporary network blip never blocks the app from
starting — assets that were already on disk keep working.

This makes the app truly offline-friendly: a fresh checkout plus `python run.py`
is enough; no separate `scripts/fetch_assets.py` invocation needed.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from flask import Flask

log = logging.getLogger(__name__)


def _load_fetch_assets(project_root: Path):
    """Import scripts/fetch_assets.py as a module (it isn't on sys.path)."""
    path = project_root / "scripts" / "fetch_assets.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("fetch_assets", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fetch_assets"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def ensure_vendor_assets(app: Flask) -> None:
    """Download any vendored assets that are missing from disk.

    Quiet by design: skips assets that are already present, logs a warning
    (not an error) if a download fails, and never raises.
    """
    project_root = Path(app.root_path).parent
    try:
        mod = _load_fetch_assets(project_root)
    except Exception as exc:  # noqa: BLE001
        log.warning("vendor-assets bootstrap: could not load fetch_assets.py: %s", exc)
        return
    if mod is None:
        return

    manifest = getattr(mod, "MANIFEST", None)
    fetch_one = getattr(mod, "fetch_one", None)
    vendor_dir = getattr(mod, "VENDOR", None)
    if manifest is None or fetch_one is None or vendor_dir is None:
        log.warning("vendor-assets bootstrap: fetch_assets.py has unexpected layout")
        return

    missing = [a for a in manifest if not (vendor_dir / a.dest).exists()]
    if not missing:
        return

    log.info("Fetching %d missing vendor asset(s)…", len(missing))
    for asset in missing:
        try:
            msg = fetch_one(asset, force=False, verify_only=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("vendor-assets: %s failed (%s) — page may break until you run "
                        "scripts/fetch_assets.py manually", asset.name, exc)
            continue
        if str(msg).startswith(("FAIL", "MISMATCH", "MISSING")):
            log.warning("vendor-assets: %s", msg)
        else:
            log.info("vendor-assets: %s", msg)
