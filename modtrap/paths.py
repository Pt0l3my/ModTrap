"""ModTrap's own work folder: its settings now, its safe folders and history later (DESIGN§11, DESIGN§12). Never
inside an instance, the game's folder or ModTrap's own program folder."""

from __future__ import annotations

import json
import itertools
import os
import threading
import time
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


_writes = itertools.count()


def write_atomic(path: Path, data: bytes) -> None:
    """Written beside the file, flushed, then swapped in: a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # A name of its own for every write: two threads saving the same file at once must not share one.
    tmp = path.with_name(path.name + ".%d.%d.%d.tmp" % (os.getpid(), threading.get_ident(), next(_writes)))
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    # Windows refuses to swap a file in while anything has the old one open (another thread reading it, a virus
    # scanner looking at it): that passes in a moment, so it is tried again before it is given up.
    for attempt in range(12):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 11:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            time.sleep(0.05 * (attempt + 1))


def load_settings() -> dict:
    try:
        with open(home() / "settings.json", "rb") as f:
            data = json.loads(f.read(1024 * 1024).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    write_atomic(home() / "settings.json", (json.dumps(settings, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
