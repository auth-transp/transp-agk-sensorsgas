"""Runtime setup for the frozen Gas Sensor Monitor.

The source program uses a relative ``settings.json`` path. In a one-file
PyInstaller bundle, bundled files live in a temporary extraction directory,
which is not writable or persistent. This hook creates a persistent per-user
data folder and installs the settings that were present at build time on the
first run of this corrected build.
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def _bundle_directory() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _prepare_runtime() -> None:
    if not getattr(sys, "frozen", False):
        return

    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home()
    app_dir = base / "GasSensorMonitor"
    app_dir.mkdir(parents=True, exist_ok=True)

    bundled_settings = _bundle_directory() / "settings.json"
    user_settings = app_dir / "settings.json"

    # The previous build kit did not create this marker and could therefore
    # leave a different/default settings file behind. Install the settings
    # bundled with this corrected build once, then preserve future client edits.
    marker = app_dir / ".corrected_build_v2_defaults_installed"
    if not marker.exists():
        if bundled_settings.exists():
            shutil.copy2(bundled_settings, user_settings)
        marker.write_text(
            datetime.now().isoformat(timespec="seconds"),
            encoding="utf-8",
        )

    os.chdir(app_dir)

    # Windowed executables do not show a console. Keep a persistent diagnostic
    # log without preventing the application from opening if logging fails.
    try:
        log = open(
            app_dir / "GasSensorMonitor.log",
            "a",
            encoding="utf-8",
            buffering=1,
        )
        sys.stdout = log
        sys.stderr = log
        print(f"\n--- Application started {datetime.now().isoformat(timespec='seconds')} ---")
        print(f"Bundle directory: {_bundle_directory()}")
        print(f"Working directory: {Path.cwd()}")
        print(f"Settings file exists: {user_settings.exists()}")
    except Exception:
        pass


_prepare_runtime()
