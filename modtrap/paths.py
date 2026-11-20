"""ModTrap's own work folder: its settings now, its safe folders and history later (DESIGN§11, DESIGN§12). Never
inside an instance, the game's folder or ModTrap's own program folder."""

from __future__ import annotations

import json
import os
from pathlib import Path


def home() -> Path:
    """%LOCALAPPDATA%\\ModTrap on Windows, ~/.local/share/ModTrap elsewhere; MODTRAP_HOME overrides (tests)."""
    over = os.environ.get("MODTRAP_HOME")
    if over:
        return Path(over)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "ModTrap"
    return Path(os.path.expanduser("~")) / ".local" / "share" / "ModTrap"


def write_atomic(path: Path, data: bytes) -> None:
    """Written beside the file, flushed, then swapped in: a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_settings() -> dict:
    try:
        with open(home() / "settings.json", "rb") as f:
            data = json.loads(f.read(1024 * 1024).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    write_atomic(home() / "settings.json", (json.dumps(settings, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
