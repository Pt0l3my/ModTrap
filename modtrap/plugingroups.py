"""MO2's plugin groups (MT73, MO05).

Stock MO2 has no groups in its plugin list. A plugin manager extension for MO2 has them, and keeps them in the
profile's `plugingroups.txt`: a comment line, then one line for each plugin that is in a group, `name|group`. A
group has no record of its own: it is the run of neighbours in the load order that carry the same name (MO05§2),
so where a plugin stands decides what a group looks like, and a name carried by plugins apart shows as two groups.

ModTrap reads the file to show the Plugins tab as that MO2 shows it, and writes a line of it only for a plugin it
placed or moved itself, or at the owner's word, as part of a job with its safe copy. Where the file is not there,
there are no groups to keep: ModTrap never makes the file.
"""
from __future__ import annotations

from pathlib import Path

from . import instance
from .instance import fold

NAME = "plugingroups.txt"
NAME_CAP = 100


def parse(text: str) -> tuple[dict[str, str], int]:
    """The groups by folded plugin name, and how many lines were not understood. As the extension reads it (MO05§1):
    an empty line or one beginning with # says nothing; any other line is to be exactly `name|group`."""
    out: dict[str, str] = {}
    bad = 0
    for line in text.splitlines():
        if not line or line[0] == "#":
            continue
        parts = line.split("|")
        if len(parts) != 2 or not parts[0]:
            bad += 1
            continue
        if parts[1]:
            out[fold(parts[0])] = parts[1]
    return out, bad


def present(profile_dir: Path) -> bool:
    return (profile_dir / NAME).is_file()


def read(profile_dir: Path) -> dict[str, str] | None:
    """The groups by folded plugin name; None where this MO2 keeps none (there is no file) or it cannot be read."""
    path = profile_dir / NAME
    if not path.is_file():
        return None
    try:
        return parse(instance._decode(instance._read_bytes(path)))[0]
    except (OSError, instance.Unusable):
        return None


def separator_of(modlist: list[tuple[str, str]], mod: str) -> str:
    """The name of the separator a mod stands under, from the mod list's lines as (sign, name), highest priority
    first: the first separator below it. "" when it stands under none, or is not in the list."""
    f, found = fold(mod), False
    for _sign, name in modlist:
        if found and name.lower().endswith("_separator"):
            return name[:-len("_separator")]
        if fold(name) == f:
            found = True
    return ""


def _neighbours(order: list[str], name: str) -> tuple[str, str]:
    f = fold(name)
    i = next((k for k, n in enumerate(order) if fold(n) == f), None)
    if i is None:
        return "", ""
    return (order[i - 1] if i > 0 else ""), (order[i + 1] if i + 1 < len(order) else "")


def for_new(order: list[str], groups: dict[str, str], name: str, wanted: str) -> str:
    """The group of a plugin new to the load order, which names it already (MT73). Between two plugins of one
    group it is in that group. Otherwise it takes the name wanted for it (its mod's separator), unless plugins
    elsewhere carry that name already and none of them is its neighbour: MO2 would show a second group of the
    same name, so it is left without one, for the owner to say."""
    before, after = (groups.get(fold(n), "") if n else "" for n in _neighbours(order, name))
    if before and before == after:
        return before
    wanted = clean(wanted)
    if not wanted:
        return ""
    if wanted in (before, after):
        return wanted
    f = fold(name)
    if any(g == wanted for n, g in groups.items() if n != f):
        return ""
    return wanted


def after_move(was: list[str], now: list[str], groups: dict[str, str], name: str) -> str:
    """The group of a plugin moved from its place in `was` to its place in `now` (MT73). Between two plugins of
    one group it joins them. Otherwise it keeps its own where a new neighbour has it too, or where it stood alone
    in it (the group moves with it); taken out of the middle of its group, it is without one."""
    own = groups.get(fold(name), "")
    before, after = (groups.get(fold(n), "") if n else "" for n in _neighbours(now, name))
    if before and before == after:
        return before
    if not own:
        return ""
    if own in (before, after):
        return own
    left = any(n and groups.get(fold(n), "") == own for n in _neighbours(was, name))
    return "" if left else own


def clean(group: str) -> str:
    """A group's name as the file can hold it, or "" for none."""
    group = " ".join(group.replace("|", " ").split())
    return group[:NAME_CAP].strip()


def set_groups(profile_dir: Path, wanted: dict[str, str], expect: str | None = None):
    """Gives plugins their groups: each line wanted is changed, added at its place by name, or taken out for "".
    Every other line stays byte for byte. The file must be there (ModTrap never makes it). Returns the
    `profile.Change`, as the writers of MO2's other lists do; refusals are `profile.Refused`."""
    from . import profile                       # the writer of MO2's lists: loaded only where ModTrap may change them (MT8)
    path = profile_dir / NAME
    if not path.is_file():
        raise profile.Refused("this MO2 keeps no plugin groups (there is no %s in the profile)" % NAME)
    for name, group in wanted.items():
        if not name or "|" in name or "\n" in name or "\r" in name or name[0] == "#":
            raise profile.Refused("%s cannot be given a group: its name cannot stand in %s" % (name or "a plugin without a name", NAME))
        if group != clean(group):
            raise profile.Refused("“%s” cannot be a group's name" % group)
    old = profile._read(path)
    lines = profile._split(old)
    end = b"\r\n" if not lines or lines[0].endswith(b"\r\n") else b"\n"
    if lines and not lines[-1].endswith((b"\n", b"\r")):
        lines[-1] += end
    changed: list[dict] = []

    def named(line: bytes) -> str | None:
        body = profile._decode(profile._body(line))
        if not body or body[0] == "#" or body.count("|") != 1:
            return None
        return body.split("|")[0]

    for name, group in wanted.items():
        f = fold(name)
        at = [i for i, ln in enumerate(lines) if (n := named(ln)) is not None and fold(n) == f]
        was = profile._decode(profile._body(lines[at[0]])).split("|")[1] if at else ""
        new = ("%s|%s" % (name, group)).encode("utf-8") + end if group else None
        if at:
            if new is not None:
                keep_end = lines[at[0]][len(profile._body(lines[at[0]])):] or end
                new = new[:-len(end)] + keep_end
            if len(at) == 1 and new == lines[at[0]]:
                continue
            for i in reversed(at[1:]):                      # a name written twice: one line says it from now on
                del lines[i]
            if new is None:
                del lines[at[0]]
            else:
                lines[at[0]] = new
        elif new is not None:
            key = name.lower()
            i = next((k for k, ln in enumerate(lines) if (n := named(ln)) is not None and n.lower() > key), len(lines))
            lines.insert(i, new)
        else:
            continue
        changed.append({"plugin": name, "group": group, "was": was})
    before, after = profile._write(path, old, lines, expect)
    return profile.Change(NAME, before, after, changed)


__all__ = ["NAME", "after_move", "clean", "for_new", "parse", "present", "read", "separator_of", "set_groups"]
