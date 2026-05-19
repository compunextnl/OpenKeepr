"""Translation sync — keeps PO/MO files current without manual scripts.

On app startup (when AUTO_COMPILE_TRANSLATIONS is true) this:
  1. Extracts source strings from `app/**.py` and `app/templates/**.html`
     into a fresh `messages.pot`.
  2. Initialises any missing language catalogs.
  3. Merges the new POT into each `messages.po` — existing translations
     are preserved.
  4. Compiles any `.po` that is newer than its `.mo` (or where `.mo` is
     missing).

Failures are logged but never block startup.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from flask import Flask

log = logging.getLogger(__name__)


def sync_translations(app: Flask) -> None:
    project_root = Path(app.root_path).parent
    translations_dir = Path(app.root_path) / "translations"
    translations_dir.mkdir(parents=True, exist_ok=True)
    babel_cfg = project_root / "babel.cfg"
    pot_path = translations_dir / "messages.pot"

    if not babel_cfg.exists():
        log.debug("No babel.cfg found at %s; skipping translation sync", babel_cfg)
        return

    languages: list[str] = list(app.config["AVAILABLE_LANGUAGES"])

    # 1) extract → POT (relative to project root)
    rc = _pybabel(
        ["extract", "-F", str(babel_cfg), "-k", "_l", "-o", str(pot_path), "."],
        cwd=project_root,
    )
    if rc != 0 or not pot_path.exists() or pot_path.stat().st_size == 0:
        log.warning("pybabel extract produced an empty POT; aborting sync to avoid wiping translations")
        return

    # 2/3) init missing catalogs, update existing
    for lang in languages:
        po_path = translations_dir / lang / "LC_MESSAGES" / "messages.po"
        if not po_path.exists():
            po_path.parent.mkdir(parents=True, exist_ok=True)
            _pybabel(
                ["init", "-i", str(pot_path), "-d", str(translations_dir), "-l", lang],
                cwd=project_root,
            )
        else:
            _pybabel(
                ["update", "-i", str(pot_path), "-d", str(translations_dir), "-l", lang,
                 "--ignore-pot-creation-date"],
                cwd=project_root,
            )

    # 3b) seed canonical translations from scripts/seed_translations.py
    # (idempotent — only fills empty msgstrs, never overwrites human edits)
    try:
        _seed_translations(project_root, translations_dir, languages)
    except Exception as exc:  # noqa: BLE001
        log.warning("translation seeding skipped: %s", exc)

    # 4) compile stale .mo files
    for lang in languages:
        po_path = translations_dir / lang / "LC_MESSAGES" / "messages.po"
        mo_path = po_path.with_suffix(".mo")
        if not po_path.exists():
            continue
        if not mo_path.exists() or po_path.stat().st_mtime > mo_path.stat().st_mtime:
            _pybabel(
                ["compile", "-d", str(translations_dir), "-l", lang, "-f"],
                cwd=project_root,
            )


def _seed_translations(project_root: Path, translations_dir: Path, languages: list[str]) -> None:
    """Run the canonical-translation seeder if it's present in scripts/."""
    seeder = project_root / "scripts" / "seed_translations.py"
    if not seeder.exists():
        return
    import importlib.util

    spec = importlib.util.spec_from_file_location("seed_translations", seeder)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    total = 0
    for lang in languages:
        po = translations_dir / lang / "LC_MESSAGES" / "messages.po"
        if po.exists():
            try:
                total += module.apply(po, lang)
            except Exception as exc:  # noqa: BLE001
                log.warning("seeder apply(%s) failed: %s", lang, exc)
    if total:
        log.info("seeded %d translation(s) from scripts/seed_translations.py", total)


def _pybabel(args: list[str], *, cwd: Path) -> int:
    """Invoke pybabel as a subprocess, returning the exit code (0 = OK)."""
    cmd = [sys.executable, "-m", "babel.messages.frontend"] + args
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            log.warning("pybabel %s failed (rc=%s): %s", args[0], proc.returncode, proc.stderr.strip())
        elif proc.stderr.strip():
            log.debug("pybabel %s: %s", args[0], proc.stderr.strip())
        return proc.returncode
    except Exception as exc:  # noqa: BLE001
        log.warning("pybabel %s raised %s", args[0], exc)
        return -1
