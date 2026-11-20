"""ModTrap's log: a ring of numbered lines the page fetches with "lines after N" (WHY§9), also printed to the
console window. Every line is masked before it is kept: the owner's folders become placeholders, so that a log can
be copied and shared.

Our own, small; the idea (a numbered ring, masking, errors named by type only) is DataPiler's.
"""

from __future__ import annotations

import os
import re
import sys
import threading
import time
from collections import deque

RING = 5000
_lock = threading.Lock()
_ring: deque[dict] = deque(maxlen=RING)
_seq = 0
_masks: list[tuple[re.Pattern, str]] = []
_console = True


def set_console(on: bool) -> None:
    global _console
    _console = on


def set_masks(folders: dict[str, str | None]) -> None:
    """`folders` maps a placeholder such as "<modlist>" to a folder to hide. Longest folders are replaced first,
    with either slash and without regard to case; then the user's home folder, whatever is left of it."""
    global _masks
    out: list[tuple[int, re.Pattern, str]] = []
    items = dict(folders)
    items.setdefault("<home>", os.path.expanduser("~"))
    for label, folder in items.items():
        if not folder or len(folder) < 4:
            continue
        parts = [re.escape(p) for p in re.split(r"[\\/]+", folder.rstrip("\\/")) if p != ""]
        lead = r"[\\/]+" if folder.startswith(("/", "\\")) else ""
        out.append((len(folder), re.compile(lead + r"[\\/]+".join(parts), re.IGNORECASE), label))
    out.sort(key=lambda t: -t[0])
    with _lock:
        _masks = [(rx, label) for _, rx, label in out]


def mask(text: str) -> str:
    with _lock:
        masks = list(_masks)
    for rx, label in masks:
        text = rx.sub(lambda m, label=label: label, text)
    return text


def why(e: BaseException) -> str:
    """An error in words for the page and the log: its type, and the system's own short reason for a file error.
    Never the full text of an exception, which may hold paths."""
    if isinstance(e, OSError) and e.strerror:
        return "%s (%s)" % (type(e).__name__, e.strerror)
    return type(e).__name__


def add(level: str, source: str, text: str) -> None:
    global _seq
    text = mask(text)
    with _lock:
        _seq += 1
        line = {"seq": _seq, "t": time.strftime("%H:%M:%S"), "level": level, "source": source, "text": text}
        _ring.append(line)
    if _console:
        try:
            print("%s %-5s %-8s %s" % (line["t"], level, source, text), file=sys.stderr, flush=True)
        except (OSError, ValueError):
            pass


class Log:
    def __init__(self, source: str):
        self.source = source

    def info(self, text: str, *args: object) -> None:
        add("info", self.source, text % args if args else text)

    def warn(self, text: str, *args: object) -> None:
        add("warn", self.source, text % args if args else text)

    def error(self, text: str, *args: object) -> None:
        add("error", self.source, text % args if args else text)


def get(source: str) -> Log:
    return Log(source)


def lines_after(seq: int, limit: int = 1000) -> tuple[list[dict], int]:
    """The lines numbered above `seq`, oldest first, at most `limit`; and the newest number."""
    with _lock:
        lines = [ln for ln in _ring if ln["seq"] > seq][:limit]
        return lines, _seq


def clear() -> None:
    """For tests."""
    global _seq
    with _lock:
        _ring.clear()
        _seq = 0
