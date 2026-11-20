"""Changing a profile's lists the way MO2 itself writes them (MO01§2, WHY§16, WHY§26): enabling and disabling mods
in `modlist.txt`, activating and deactivating plugins in `plugins.txt`, and putting a new mod at the top.

NOT USED YET. Nothing in ModTrap calls this module: it is groundwork for the demaster step (WHY§36), built and tested
ahead of it. When it is used, the rules are: MO2 must be closed (an open MO2 writes these files from memory); the
file must first be in the job's safe folder; and every change goes into the history.

A change touches only the lines it is about. Every other line is written back byte for byte: order, line ends,
comments and the text encoding stay exactly as MO2 left them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .instance import fold

READ_CAP = 32 * 1024 * 1024


class Refused(Exception):
    """The change cannot be made; the text says why, in words for the page. Nothing was written."""


@dataclass
class Change:
    """What one write did, for the history: the file, its checksum before and after, and each line changed."""
    file: str
    before: str
    after: str
    lines: list[dict] = field(default_factory=list)


def _read(path: Path) -> bytes:
    try:
        with open(path, "rb") as f:
            data = f.read(READ_CAP + 1)
    except OSError as e:
        raise Refused("%s could not be read (%s)" % (path.name, type(e).__name__)) from None
    if len(data) > READ_CAP:
        raise Refused("%s is larger than ModTrap handles" % path.name)
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _split(data: bytes) -> list[bytes]:
    """Lines with their own line ends kept, so that joining them gives the file back exactly."""
    return data.splitlines(keepends=True)


def _body(line: bytes) -> bytes:
    return line.rstrip(b"\r\n")


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def _write(path: Path, old: bytes, new_lines: list[bytes], expect: str | None) -> tuple[str, str]:
    """Writes the new lines, after checking that the file is still the one that was read (and, when `expect` is
    given, the one the caller planned against). Returns the checksums before and after."""
    now = _read(path)
    if now != old:
        raise Refused("%s changed while ModTrap was working on it; nothing was written" % path.name)
    if expect is not None and _sha(old) != expect:
        raise Refused("%s is not the file this change was planned for; read the modlist again" % path.name)
    new = b"".join(new_lines)
    if new == old:
        return _sha(old), _sha(old)
    try:
        paths.write_atomic(path, new)
    except OSError as e:
        raise Refused("%s could not be written (%s)" % (path.name, type(e).__name__)) from None
    if _read(path) != new:
        raise Refused("%s was written but does not read back as written" % path.name)
    return _sha(old), _sha(new)


# --- modlist.txt --------------------------------------------------------------------------------------------------

def set_mods(profile_dir: Path, wanted: dict[str, bool], expect: str | None = None) -> Change:
    """Enables (True) or disables (False) the named mods. Their places in the list, and so their priorities, do not
    change. A mod that is not in the list, or that MO2 does not manage (`*`), is refused; a mod already as wanted
    is left alone and not reported."""
    path = profile_dir / "modlist.txt"
    old = _read(path)
    lines = _split(old)
    want = {fold(k): v for k, v in wanted.items()}
    names = {fold(k): k for k in wanted}
    seen: set[str] = set()
    change = Change(file="modlist.txt", before="", after="")
    listed = [i for i, ln in enumerate(lines) if _body(ln) and not _body(ln).startswith(b"#")]
    for rank, i in enumerate(listed):
        body = _body(lines[i])
        sign, name = (chr(body[0]), body[1:]) if body[:1] in (b"+", b"-", b"*") else ("+", body)
        key = fold(_decode(name).strip())
        if key not in want or key in seen:
            continue
        seen.add(key)
        if sign == "*":
            raise Refused("'%s' is not managed by MO2 and cannot be enabled or disabled here" % names[key])
        new_sign = "+" if want[key] else "-"
        if new_sign == sign:
            continue
        end = lines[i][len(body):]
        lines[i] = new_sign.encode("ascii") + name + end
        change.lines.append({"mod": _decode(name).strip(), "from": sign, "to": new_sign,
                             "priority": len(listed) - 1 - rank})          # the list is highest first
    missing = [names[k] for k in want if k not in seen]
    if missing:
        raise Refused("not in this profile's mod list: %s" % ", ".join(sorted(missing)))
    change.before, change.after = _write(path, old, lines, expect)
    return change


def add_mod_on_top(profile_dir: Path, name: str, enabled: bool = True, expect: str | None = None) -> Change:
    """Adds a mod as the first line, which is the highest priority (MO01§2). Refused if it is already listed."""
    if not name.strip() or any(c in name for c in "\r\n") or name[0] in "+-*#":
        raise Refused("that is not a name a mod can have in the list")
    path = profile_dir / "modlist.txt"
    old = _read(path)
    lines = _split(old)
    for ln in lines:
        body = _body(ln)
        if body and not body.startswith(b"#"):
            listed = body[1:] if body[:1] in (b"+", b"-", b"*") else body
            if fold(_decode(listed).strip()) == fold(name):
                raise Refused("'%s' is already in this profile's mod list" % name)
    end = b"\r\n" if not lines or lines[0].endswith(b"\r\n") else b"\n"
    at = 0
    while at < len(lines) and _body(lines[at]).startswith(b"#"):
        at += 1                                                # after MO2's comment line
    if lines and not lines[-1].endswith((b"\n", b"\r")) and at == len(lines):
        lines[-1] += end
    lines.insert(at, ("+" if enabled else "-").encode("ascii") + name.encode("utf-8") + end)
    listed_count = sum(1 for ln in lines if _body(ln) and not _body(ln).startswith(b"#"))
    change = Change(file="modlist.txt", before="", after="",
                    lines=[{"mod": name, "from": "", "to": "+" if enabled else "-", "priority": listed_count - 1}])
    change.before, change.after = _write(path, old, lines, expect)
    return change


def remove_mod_line(profile_dir: Path, name: str, expect: str | None = None) -> Change:
    """Takes a mod's line out of the list: only for a mod ModTrap itself added (Revert). The mod's folder is not
    touched here."""
    path = profile_dir / "modlist.txt"
    old = _read(path)
    lines = _split(old)
    change = Change(file="modlist.txt", before="", after="")
    for i, ln in enumerate(lines):
        body = _body(ln)
        if body and not body.startswith(b"#") and body[:1] in (b"+", b"-"):
            if fold(_decode(body[1:]).strip()) == fold(name):
                change.lines.append({"mod": name, "from": chr(body[0]), "to": ""})
                del lines[i]
                break
    else:
        raise Refused("'%s' is not in this profile's mod list" % name)
    change.before, change.after = _write(path, old, lines, expect)
    return change


# --- plugins.txt --------------------------------------------------------------------------------------------------

def set_plugins(profile_dir: Path, wanted: dict[str, bool], expect: str | None = None) -> Change:
    """Activates (True) or deactivates (False) the named plugins: the star before the name (MO01§2). The order of
    the lines, which MO2 takes the load order from when this file is the newer one, does not change. A plugin the
    file does not list is refused (the game's own plugins are never listed)."""
    path = profile_dir / "plugins.txt"
    old = _read(path)
    lines = _split(old)
    want = {fold(k): v for k, v in wanted.items()}
    names = {fold(k): k for k in wanted}
    seen: set[str] = set()
    change = Change(file="plugins.txt", before="", after="")
    position = 0
    for i, ln in enumerate(lines):
        body = _body(ln)
        if not body.strip() or body.lstrip().startswith(b"#"):
            continue
        active = body.startswith(b"*")
        name = body[1:] if active else body
        key = fold(_decode(name).strip())
        position += 1
        if key not in want or key in seen:
            continue
        seen.add(key)
        if want[key] == active:
            continue
        end = ln[len(body):]
        lines[i] = (b"*" if want[key] else b"") + name + end
        change.lines.append({"plugin": _decode(name).strip(), "from": "active" if active else "inactive",
                             "to": "active" if want[key] else "inactive", "line": position})
    missing = [names[k] for k in want if k not in seen]
    if missing:
        raise Refused("not in this profile's plugin list: %s" % ", ".join(sorted(missing)))
    change.before, change.after = _write(path, old, lines, expect)
    return change


def checksum(path: Path) -> str:
    return _sha(_read(path))
