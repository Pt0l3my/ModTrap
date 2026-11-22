"""What a tool's own log says about the run ModTrap started (WHY§88).

ModTrap judges a tool's run by its output files. When a tool also keeps a log of its own, that log says why a run
came to nothing, in the tool's words. Which tools keep one, where, and which lines in it mean what, is data
(`tools.json`, "log"): each sign a pattern and a sentence, with its source in the research note. Nothing is
guessed from a log: a sign counts lines that match, or lists the values a pattern captured, and the sentence
says that.

The log is only read. A copy of it goes into the session's folder, so that a saved session file holds it (cleaned
of the owner's folders and name there, as every text in that file is).
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
from pathlib import Path

from . import logbook, tools

log = logbook.get("tool")
READ_CAP = 16 * 1024 * 1024        # of a tool's log, the last part of this size is read
KEEP_CAP = 64 * 1024 * 1024        # a larger log is not copied into the session
LINE_CAP = 4000                    # characters of one line that are looked at
VALUES = 8                         # distinct values listed for one sign


def spec_for(title: str, binary: str) -> dict | None:
    name, _kind = tools.of_executable(title, binary)
    entry = next((t for t in tools.load() if t["tool"] == name), {})
    spec = entry.get("log")
    return spec if isinstance(spec, dict) and spec.get("folder") is not None else None


def newest(folder: Path, pattern: str, since: float) -> Path | None:
    """The log file written last in the tool's log folder, if it was written since the run began."""
    best, when = None, since - 5.0
    try:
        with os.scandir(folder) as it:
            for e in it:
                if not e.is_file() or not fnmatch.fnmatch(e.name.lower(), pattern.lower()):
                    continue
                t = e.stat().st_mtime
                if t >= when:
                    best, when = Path(e.path), t
    except OSError:
        return None
    return best


def read(path: Path) -> str:
    with open(path, "rb") as f:
        size = f.seek(0, os.SEEK_END)
        f.seek(max(0, size - READ_CAP))
        data = f.read(READ_CAP)
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("cp1252", "replace")


class _Blank(dict):
    def __missing__(self, key: str) -> str:
        return ""


def findings(text: str, signs: list) -> list[dict]:
    """Each sign that shows in the text, as {"level", "text", "n"}. A sign of kind "count" (the default) counts the
    lines its pattern matches and words the last match; one of kind "values" lists, in the order they first came,
    the distinct values its pattern captured, and has a second sentence for when there was more than one."""
    compiled = []
    for sign in signs:
        try:
            compiled.append((sign, re.compile(sign["find"])))
        except (re.error, KeyError, TypeError):
            continue
    counts = [0] * len(compiled)
    last: list[dict | None] = [None] * len(compiled)
    values: list[list[str]] = [[] for _ in compiled]
    for line in text.split("\n"):
        line = line[:LINE_CAP]
        for i, (sign, rx) in enumerate(compiled):
            m = rx.search(line)
            if m is None:
                continue
            counts[i] += 1
            last[i] = m.groupdict()
            if sign.get("kind") == "values":
                v = str(sign.get("value", "")).format_map(_Blank(m.groupdict())).strip()
                if v and v not in values[i]:
                    values[i].append(v)
    out = []
    for i, (sign, _rx) in enumerate(compiled):
        if not counts[i]:
            continue
        fields = _Blank(last[i] or {})
        fields["n"] = counts[i]
        says = str(sign.get("says", ""))
        if sign.get("kind") == "values":
            if not values[i]:
                continue
            shown = values[i][:VALUES] + (["…"] if len(values[i]) > VALUES else [])
            fields.update(values=", then ".join(shown), first=values[i][0], last=values[i][-1])
            if len(values[i]) > 1 and sign.get("says_changed"):
                says = str(sign["says_changed"])
        try:
            sentence = says.format_map(fields)
        except (ValueError, IndexError):
            continue
        if sentence:
            out.append({"level": "error" if sign.get("level") == "error" else "note", "text": sentence, "n": counts[i]})
    return out


def after_run(title: str, binary: str, started: float, keep_in: Path | None) -> dict | None:
    """After a tool has closed: what its own log of this run says. {"file", "findings", "kept"}, or None for a tool
    whose log ModTrap does not know, or that wrote none since it was started. Never raises."""
    try:
        spec = spec_for(title, binary)
        if spec is None:
            return None
        folder = Path(binary.replace("\\", "/")).parent / str(spec["folder"])
        path = newest(folder, str(spec.get("pattern", "*.log")), started)
        if path is None:
            return None
        found = findings(read(path), list(spec.get("signs", [])))
        kept = False
        if keep_in is not None and path.stat().st_size <= KEEP_CAP:
            dst = keep_in / re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:60]
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dst / path.name)
            kept = True
        log.info("“%s” kept a log of this run (%s)%s; ModTrap read it:%s", title, path.name,
                 ", a copy of which is in the session's folder" if kept else "",
                 "" if found else " none of the signs it knows shows in it")
        for f in found:
            (log.warn if f["level"] == "error" else log.info)("  %s", f["text"])
        return {"file": path.name, "findings": found, "kept": kept}
    except Exception as e:
        log.warn("“%s”'s own log could not be read: %s", title, logbook.why(e))
        return None


__all__ = ["after_run", "findings", "newest", "read", "spec_for"]
