"""What MO2's own columns say of a mod (MT70): Conflicts, Installation, Notes. The rules are MO2's, read in its
source (MO04); nothing of MO2 is run or copied.

- Installation: when the mod's folder was made (MO04§2).
- Notes: the "comments" of the mod's own record, meta.ini (MO04§3). A separator has them too.
- Conflicts: for every enabled mod, whether loose files of it win over other mods' files, lose to them, both, or
  whether every file of it loses (MO04§1). MO2 knows this from the one tree of files it builds of all enabled
  mods; ModTrap lists every enabled mod's files once, from the highest priority down, to know the same. Files
  inside archives are not looked at, as in MO2 unless its archive parsing is switched on.

Reading only. The listing takes a while on a large modlist the first time, so it runs off the page's requests and
keeps each mod's list in memory for as long as the mod's folder looks the same from above.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from . import logbook, model, sources
from .instance import OVERWRITE, Mod

log = logbook.get("columns")
HIDDEN = ".mohidden"                    # MO2's mark of a file or a folder hidden from the game (MO04§1)
SKIP_FILES = ("meta.ini", "readme.txt")     # at a mod's top: MO2 takes them out of its tree
SKIP_DIRS = ("fomod",)
STATES = ("overwrite", "overwritten", "mixed", "redundant")
SECONDS = 900.0


def unquote(value: str) -> str:
    """A value as MO2's settings files write a text: in quotes where it holds a comma or the like, with \\n, \\"
    and \\xNNNN for what cannot stand as it is."""
    v = value.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]

    def one(m: re.Match) -> str:
        s = m.group(0)
        if s[1] == "x":
            try:
                return chr(int(s[2:], 16))
            except ValueError:
                return s
        return {"n": "\n", "r": "", "t": " ", '"': '"', "\\": "\\"}.get(s[1], s[1])
    return re.sub(r"\\x[0-9a-fA-F]{1,4}|\\.", one, v).strip()


def info(inst) -> dict[str, dict]:
    """Every mod's and separator's Installation and Notes: {name: {"installed": seconds since 1970 or None,
    "notes": text}}."""
    out: dict[str, dict] = {}
    for x in inst.mods:
        if x.kind not in ("mod", "separator") or x.folder is None:
            continue
        made = None
        try:
            st = os.stat(x.folder)
            made = getattr(st, "st_birthtime", None) or (st.st_ctime if os.name == "nt" else st.st_mtime)
        except OSError:
            pass
        try:
            notes = unquote(sources._ini(x.folder / "meta.ini").get("general", {}).get("comments", ""))
        except Exception:
            notes = ""
        out[x.name] = {"installed": int(made) if made else None, "notes": notes[:400]}
    return out


def _stamp(folder: Path) -> tuple:
    """How a mod's folder looks from above: its top entries and when each was last changed."""
    try:
        with os.scandir(folder) as it:
            return tuple(sorted((e.name, e.stat(follow_symlinks=False).st_mtime_ns) for e in it))
    except OSError:
        return ()


def listing(folder: Path) -> tuple[int, ...]:
    """The mod's files as MO2's tree of files holds them: every file under the folder but the mod's own record, a
    read-me and an installer's folder at its top, and nothing that is hidden. A number for each path."""
    out: list[int] = []
    stack = [("", folder)]
    while stack:
        rel, d = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            low = e.name.lower()
            if low.endswith(HIDDEN):
                continue
            try:
                if e.is_dir(follow_symlinks=False):
                    if not (rel == "" and low in SKIP_DIRS):
                        stack.append((rel + low + "/", Path(e.path)))
                elif e.is_file(follow_symlinks=False):
                    if not (rel == "" and low in SKIP_FILES):
                        out.append(hash(rel + low))
            except OSError:
                continue
    return tuple(out)


def conflicts(m: model.Model, cache: dict | None = None, progress=None, seconds: float = SECONDS) -> dict:
    """Each enabled mod's state as MO2's Conflicts column shows it for loose files: {"mods": {name: state},
    "listed", "files", "cut", "seconds"}; a mod without a state is not named."""
    started = time.monotonic()
    cache = cache if cache is not None else {}
    order: list[Mod] = [x for x in m.instance.mods if x.kind == "overwrite" and x.folder is not None]
    order += sorted((x for x in m.instance.mods if x.kind == "mod" and x.enabled and x.folder is not None), key=lambda x: -x.priority)
    first: dict[int, int] = {}                # a path -> the mod that wins it
    more: dict[int, list[int]] = {}           # a path -> the further mods that have it, each overwritten by those before
    over = [False] * len(order)
    states: dict[str, str] = {}
    files = listed = 0
    cut = False
    for i, x in enumerate(order):
        if time.monotonic() - started > seconds:
            cut = True
            break
        if progress is not None and i % 20 == 0:
            progress(i, len(order))
        key = str(x.folder)
        stamp = _stamp(x.folder)
        kept = cache.get(key)
        if kept is None or kept[0] != stamp:
            kept = cache[key] = (stamp, listing(x.folder))
            listed += 1
        hs = kept[1]
        files += len(hs)
        provides = under = False
        for h in hs:
            w = first.get(h)
            if w is None:
                first[h] = i
                provides = True
            else:
                under = True
                over[w] = True
                others = more.get(h)
                if others is None:
                    more[h] = [i]
                else:
                    for p in others:
                        over[p] = True
                    others.append(i)
        x_state = "" if not hs else "redundant" if not provides else "overwritten" if under else ""
        states[x.name] = x_state
    for i, x in enumerate(order[:len(states)]):
        s = states[x.name]
        if s != "redundant" and over[i]:
            s = "mixed" if s == "overwritten" else "overwrite"
        if s:
            states[x.name] = s
        else:
            del states[x.name]
    if progress is not None:
        progress(len(order), len(order))
    for gone in [k for k in cache if k not in {str(x.folder) for x in order}]:
        del cache[gone]
    return {"mods": states, "enabled": len(order), "listed": listed, "files": files, "cut": cut, "seconds": round(time.monotonic() - started, 1)}


__all__ = ["HIDDEN", "STATES", "conflicts", "info", "listing", "unquote"]
