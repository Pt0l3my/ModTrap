"""Changing a profile's lists the way MO2 itself writes them (MO01§2, WHY§16, WHY§26): enabling and disabling mods
in `modlist.txt`, activating and deactivating plugins in `plugins.txt`, putting a new mod at the top, and putting
a mod and its plugins at a chosen place (DESIGN§16.8).

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


def place_mod(profile_dir: Path, name: str, before: str = "", enabled: bool = True,
              expect: str | None = None) -> Change:
    """Puts a mod at a place in the list and enables it: directly before the mod `before` as MO2 shows the list
    by priority (one priority lower than it), or with the highest priority when `before` is "". A mod already
    listed is moved there; one that is not is added (MO2 would add an unlisted folder at the top itself, MO01§2).
    The file lists the highest priority first, so "before" in MO2's list is the line after `before`'s here."""
    if not name.strip() or any(c in name for c in "\r\n") or name[0] in "+-*#":
        raise Refused("that is not a name a mod can have in the list")
    if before and fold(before) == fold(name):
        raise Refused("a mod cannot be placed before itself")
    path = profile_dir / "modlist.txt"
    old = _read(path)
    lines = _split(old)
    end = b"\r\n" if not lines or lines[0].endswith(b"\r\n") else b"\n"
    if lines and not lines[-1].endswith((b"\n", b"\r")):
        lines[-1] += end

    def listed() -> list[tuple[int, str, str]]:
        out = []
        for i, ln in enumerate(lines):
            body = _body(ln)
            if body and not body.startswith(b"#"):
                sign, nm = (chr(body[0]), body[1:]) if body[:1] in (b"+", b"-", b"*") else ("+", body)
                out.append((i, sign, _decode(nm).strip()))
        return out

    was_sign, was_priority = "", None
    rows = listed()
    for rank, (i, sign, nm) in enumerate(rows):
        if fold(nm) == fold(name):
            if sign == "*":
                raise Refused("'%s' is not managed by MO2 and cannot be moved here" % name)
            was_sign, was_priority = sign, len(rows) - 1 - rank
            del lines[i]
            break
    rows = listed()
    if before:
        hit = next((i for i, _, nm in rows if fold(nm) == fold(before)), None)
        if hit is None:
            raise Refused("'%s' is not in this profile's mod list" % before)
        at = hit + 1
    else:
        at = rows[0][0] if rows else len(lines)
    lines.insert(at, ("+" if enabled else "-").encode("ascii") + name.encode("utf-8") + end)
    rows = listed()
    rank = next(r for r, (i, _, _nm) in enumerate(rows) if i == at)
    change = Change(file="modlist.txt", before="", after="",
                    lines=[{"mod": name, "from": was_sign, "to": "+" if enabled else "-",
                            "priority": len(rows) - 1 - rank, "was": was_priority}])
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


def place_plugins(profile_dir: Path, placements: list[tuple[str, str]]) -> list[Change]:
    """Puts plugins at their places in the load order and activates them: each directly before the plugin named
    with it, or at the end when that is "". Both of MO2's lists are written, in agreement (MO2 takes the order
    from the newer one, MO01§2): `loadorder.txt`, which names every plugin, and `plugins.txt`, which leaves the
    game's own out and marks the active ones. A plugin already listed is moved."""
    lo_path, pl_path = profile_dir / "loadorder.txt", profile_dir / "plugins.txt"
    lo_old, pl_old = _read(lo_path), _read(pl_path)
    lo, pl = _split(lo_old), _split(pl_old)

    def fix_end(lines: list[bytes]) -> bytes:
        end = b"\r\n" if not lines or lines[0].endswith(b"\r\n") else b"\n"
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            lines[-1] += end
        return end

    lo_end, pl_end = fix_end(lo), fix_end(pl)
    try:
        pl_old.decode("utf-8")
        pl_coding = "utf-8"
    except UnicodeDecodeError:
        pl_coding = "cp1252"

    def name_of(line: bytes, starred: bool) -> str | None:
        body = _body(line)
        if not body.strip() or body.lstrip().startswith(b"#"):
            return None
        if starred and body.startswith(b"*"):
            body = body[1:]
        return _decode(body).strip()

    def find(lines: list[bytes], name: str, starred: bool) -> int | None:
        return next((i for i, ln in enumerate(lines) if (n := name_of(ln, starred)) is not None
                     and fold(n) == fold(name)), None)

    lo_change = Change(file="loadorder.txt", before="", after="")
    pl_change = Change(file="plugins.txt", before="", after="")
    for name, before in placements:
        if not name.strip() or any(c in name for c in "\r\n") or name[0] in "*#":
            raise Refused("that is not a name a plugin can have in the list")
        if before and fold(before) == fold(name):
            raise Refused("a plugin cannot be placed before itself")
        try:
            pl_name = name.encode(pl_coding)
        except UnicodeEncodeError:
            raise Refused("the name '%s' cannot be written in the plugin list's text encoding" % name) from None
        hit = find(lo, name, False)
        if hit is not None:
            del lo[hit]
        if before:
            at = find(lo, before, False)
            if at is None:
                raise Refused("'%s' is not in this profile's load order" % before)
        else:
            at = len(lo)
        lo.insert(at, name.encode("utf-8") + lo_end)
        hit = find(pl, name, True)
        was = None
        if hit is not None:
            was = "active" if _body(pl[hit]).startswith(b"*") else "inactive"
            del pl[hit]
        # In plugins.txt: before the first plugin after it in the load order that this file names.
        pl_at = len(pl)
        for ln in lo[at + 1:]:
            later = name_of(ln, False)
            if later is not None and (j := find(pl, later, True)) is not None:
                pl_at = j
                break
        pl.insert(pl_at, b"*" + pl_name + pl_end)
        lo_change.lines.append({"plugin": name, "position": None, "before": before})
        pl_change.lines.append({"plugin": name, "from": was or "", "to": "active", "before": before})
    final = [fold(n) for n in (name_of(ln, False) for ln in lo) if n is not None]
    for ln in lo_change.lines:
        ln["position"] = final.index(fold(ln["plugin"]))        # where it ended up, once every plugin was placed
    lo_change.before, lo_change.after = _write(lo_path, lo_old, lo, None)
    pl_change.before, pl_change.after = _write(pl_path, pl_old, pl, None)
    return [lo_change, pl_change]


def remove_plugin_lines(profile_dir: Path, names: list[str]) -> list[Change]:
    """Takes plugins out of both plugin lists: only for plugins ModTrap itself put there (undoing an add). A name
    a list does not have is passed over."""
    out = []
    want = {fold(n) for n in names}
    for fname, starred in (("loadorder.txt", False), ("plugins.txt", True)):
        path = profile_dir / fname
        old = _read(path)
        lines = _split(old)
        change = Change(file=fname, before="", after="")
        keep = []
        for ln in lines:
            body = _body(ln)
            name = body[1:] if starred and body.startswith(b"*") else body
            if body.strip() and not body.lstrip().startswith(b"#") and fold(_decode(name).strip()) in want:
                change.lines.append({"plugin": _decode(name).strip(), "to": ""})
                continue
            keep.append(ln)
        change.before, change.after = _write(path, old, keep, None)
        out.append(change)
    return out


def checksum(path: Path) -> str:
    return _sha(_read(path))
