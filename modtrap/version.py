"""ModTrap's version, and a mark of its own files (WHY§68).

The version is a number the owner can read and compare: it is raised with every change to ModTrap's files
(`tools/bump.py`; a test fails when a change was not followed by it). `version.json` holds it with a mark of the
files it belongs to. The mark is taken from the files' contents, not their dates, so unpacking the same version
again changes nothing, and line endings do not count.

A running ModTrap is the program as it was read at its start. The scripts for xEdit are read from disk at each
use. `STARTED` is the mark at the start; when the mark on disk differs later, the files were replaced while
ModTrap runs, and a new script would run under an old program."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
KINDS = (".py", ".pas", ".js", ".html", ".css", ".json")
RECORD = "version.json"


def recorded(root: Path = ROOT) -> tuple[str, str]:
    """The version written in ModTrap's folder, and the mark of the files it was written for."""
    try:
        data = json.loads((root / RECORD).read_text(encoding="utf-8"))
        version, mark = data["version"], data["mark"]
    except (OSError, ValueError, KeyError, TypeError):
        return "unknown", ""
    return (version, mark) if isinstance(version, str) and isinstance(mark, str) else ("unknown", "")


def code_mark(root: Path = ROOT) -> str:
    """A mark of ModTrap's own files as they are on disk now: the program, the page, the scripts, the data."""
    found = []
    try:
        for f in root.rglob("*"):
            rel = f.relative_to(root).as_posix()
            if f.suffix.lower() in KINDS and "__pycache__" not in f.parts and rel != RECORD and f.is_file():
                found.append((rel, f))
    except OSError:
        pass
    h = hashlib.sha256()
    for rel, f in sorted(found):                 # by name as text: the same order on every system
        try:
            data = f.read_bytes()
        except OSError:
            data = b"unreadable"
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(data.replace(b"\r", b"")).digest())
    return h.hexdigest()[:16]


VERSION, MARK = recorded()
STARTED = code_mark()
# The files this ModTrap started from are not the files its version was written for: an update unpacked over an
# older folder (files of the older one left behind), a copy cut short, or files edited by hand.
DIFFERS = STARTED != MARK


def raised(version: str) -> str:
    """The next version: the last number, one higher."""
    head, _, last = version.rpartition(".")
    return "%s.%d" % (head, int(last) + 1) if head and last.isdigit() else "0.3.1"
