"""The scanner: every settings file that is in force in the modlist, and the frameworks that read them (MT34, WHY§98).

After a demaster ModTrap says whether any settings file of another mod still names the plugin that was taken out
(DESIGN§14). For that to be worth saying, the looking must be whole and it must be the right files:

- every enabled mod is looked through, the game's own Data folder below them and MO2's Overwrite folder above,
  with no time limit that cuts it short;
- of several mods that carry a file of the same path only the winner counts, as in the game: the one MO2 loads
  last;
- each file is read once and remembered by its path, size and date, so a later look costs only a listing;
- a file is read to its end, however large, up to a size no settings file has;
- what could not be read is counted and named, never passed over in silence.

For each file it keeps which plugins of the modlist the file names (by file name), not the file's text. It also
lists the frameworks that work while the game runs, by their program files in SKSE/Plugins, and the kinds of
settings file found (by the ending of their names), each with whether ModTrap knows how such a file is read
(`mentions.json`, TL01§23, TL01§24).
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from .instance import Instance, fold

SETTINGS_NAME = re.compile(r"\.(ini|json|toml|yaml|yml|txt)$", re.IGNORECASE)
SETTINGS_BYTES = 64 * 1024 * 1024    # a file larger than this is no settings file: not read, counted and named
CHUNK = 1024 * 1024
PLUGIN_END = re.compile(rb"\.es[pml]", re.IGNORECASE)
NAME_MAX = 260                       # the longest plugin file name looked for, in bytes
TAIL = 6                             # the last bytes of a name its patterns are filed under ("x.esp" has 5)
KIND = re.compile(r"_([A-Za-z]{2,12})\.ini$")
WALK_FILES = 200_000                 # files of one folder of one mod listed at most
EXAMPLES = 12

_memo: dict[tuple[str, int, int, int], frozenset[str]] = {}  # (path, size, date, the names looked for) -> names found
_data: dict | None = None


def data() -> dict:
    """ModTrap's data on settings files (`mentions.json`): the kinds it can read a line of, and the folders of a
    mod, beside its top folder, where frameworks keep theirs."""
    global _data
    if _data is None:
        try:
            with open(Path(__file__).with_name("data") / "mentions.json", "rb") as f:
                got = json.loads(f.read().decode("utf-8"))
            _data = {"kinds": [k for k in got["kinds"] if isinstance(k, dict) and k.get("pattern")],
                     "places": [str(x["folder"]) for x in got.get("places", []) if isinstance(x, dict) and x.get("folder")]}
        except (OSError, ValueError, KeyError):
            _data = {"kinds": [], "places": ["SKSE/Plugins"]}
    return _data


class Names:
    """The plugin names looked for, filed so that a text is searched in one pass: by their last bytes, and under
    those by their length, so that many names with one ending ("… - Patch.esp") cost no more than a few.

    A name is looked for as its bytes in UTF-8 and in Windows' western code page, without case for the letters
    a to z; a name with other letters is looked for both as given and in lower case."""

    def __init__(self, names):
        self.pats: dict[bytes, str] = {}
        tails: dict[bytes, set[int]] = {}
        for name in names:
            low = name.lower()
            for form in {name, low}:
                for enc in ("utf-8", "cp1252"):
                    try:
                        pat = form.encode(enc).lower()
                    except UnicodeEncodeError:
                        continue
                    if pat in self.pats or len(pat) < 5 or len(pat) > NAME_MAX:
                        continue
                    self.pats[pat] = low
                    tails.setdefault(pat[-TAIL:], set()).add(len(pat))
        # The lengths of the names that end so, longest first: the longest name that ends there is the one meant.
        self.lengths = {tail: sorted(ns, reverse=True) for tail, ns in tails.items()}
        self.mark = hash(frozenset(self.pats))

    def ending_at(self, low: bytes, end: int) -> str | None:
        for tail in (low[max(0, end - TAIL):end], low[max(0, end - 5):end]):
            for n in self.lengths.get(tail, ()):
                if n <= end:
                    got = self.pats.get(low[end - n:end])
                    if got is not None:
                        return got
        return None


def names_in(text: bytes, known) -> frozenset[str]:
    """The plugins of `known` (a `Names`, or file names in any case) that the text names, in lower case. Found from
    each ".esp", ".esm" or ".esl" backwards: the longest known name that ends there."""
    names = known if isinstance(known, Names) else Names(known)
    out: set[str] = set()
    low = text.lower()
    for m in PLUGIN_END.finditer(low):
        got = names.ending_at(low, m.end())
        if got is not None:
            out.add(got)
    return frozenset(out)


def names_in_file(path: Path, names: Names) -> frozenset[str]:
    """As `names_in`, of a file read piece by piece to its end."""
    out: set[str] = set()
    kept = b""
    with open(path, "rb") as f:
        while True:
            piece = f.read(CHUNK)
            if not piece:
                break
            text = kept + piece
            out |= names_in(text, names)
            kept = text[-(NAME_MAX + 4):]                       # a name cut by the end of a piece is whole next time
    return frozenset(out)


def _settings_files(folder: Path, places: list[str]) -> tuple[list[tuple[str, Path]], list[str], bool]:
    """A mod's settings files, as (path inside the mod, lower case; file), its program files in SKSE/Plugins, and
    whether the listing was cut short or failed."""
    files: list[tuple[str, Path]] = []
    dlls: list[str] = []
    cut = False
    subs: dict[str, str] = {}
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.is_dir():
                    subs[e.name.lower()] = e.name
                elif SETTINGS_NAME.search(e.name) and e.name.lower() != "meta.ini":
                    files.append((e.name.lower(), Path(e.path)))
    except OSError:
        return files, dlls, True
    for place in places:
        parts = place.split("/")
        if parts[0].lower() not in subs:                        # most mods have none of these folders
            continue
        base = folder / subs[parts[0].lower()]
        for part in parts[1:]:
            try:
                with os.scandir(base) as it:
                    found = next((e.name for e in it if e.name.lower() == part.lower() and e.is_dir()), None)
            except OSError:
                found, cut = None, True
            if found is None:
                base = None
                break
            base = base / found
        if base is None:
            continue
        n = 0

        def failed(_e):
            nonlocal cut
            cut = True

        for here, dirs, names in os.walk(base, onerror=failed):
            dirs.sort()
            rel_dir = os.path.relpath(here, folder).replace("\\", "/")
            top = Path(here) == base
            for name in names:
                n += 1
                if n > WALK_FILES:
                    cut = True
                    break
                if SETTINGS_NAME.search(name):
                    files.append(((rel_dir + "/" + name).lower(), Path(here) / name))
                elif top and place.lower() == "skse/plugins" and name.lower().endswith(".dll"):
                    dlls.append(name)
            if n > WALK_FILES:
                break
    return files, dlls, cut


def scan(inst: Instance, known, progress=None) -> dict:
    """Looks through the whole modlist as described above. `known` is every plugin file name of the modlist
    (`known_plugins`).

    {"entries": [{"mod", "rel", "path", "names"}], "files", "read", "too_large", "unreadable", "cut_mods", "hidden",
     "mods", "places", "kinds": [{"kind", "files", "read_by_modtrap", "framework"}], "frameworks": [{"dll", "mod",
     "framework", "read_by_modtrap"}], "seconds", "fresh"}; "hidden" counts files a mod of higher priority replaces,
     "fresh" those read now and not remembered from an earlier look."""
    started = time.monotonic()
    names = known if isinstance(known, Names) else Names(known)
    kinds_known, places = data()["kinds"], data()["places"]
    winners: dict[str, tuple[str, Path, str]] = {}
    dll_of: dict[str, tuple[str, str]] = {}
    cut_mods: list[str] = []
    hidden = mods = 0
    # In the order the game sees them: its own Data folder, the enabled mods from the lowest priority, Overwrite.
    sources = [({"game": "the game's Data folder", "overwrite": "Overwrite"}.get(m.kind, m.name), m.folder) for m in inst.mods
               if m.folder is not None and ((m.kind == "mod" and m.enabled) or m.kind in ("game", "overwrite")) and m.folder.is_dir()]
    for i, (name, folder) in enumerate(sources):
        mods += 1
        files, dlls, cut = _settings_files(folder, places)
        if cut:
            cut_mods.append(name)
        for rel, path in files:
            hidden += rel in winners
            try:
                shown = path.relative_to(folder).as_posix()
            except ValueError:
                shown = rel
            winners[rel] = (name, path, shown)
        for d in dlls:
            dll_of[d.lower()] = (d, name)
        if progress is not None and i % 200 == 0:
            progress(i, len(sources))
    entries: list[dict] = []
    read = fresh = 0
    too_large: list[str] = []
    unreadable: list[str] = []
    for rel, (name, path, shown) in sorted(winners.items()):
        try:
            st = path.stat()
            if st.st_size > SETTINGS_BYTES:
                too_large.append("%s: %s" % (name, shown))
                continue
            key = (str(path), st.st_size, st.st_mtime_ns, names.mark)
            found = _memo.get(key)
            if found is None:
                found = names_in_file(path, names)
                _memo[key] = found
                fresh += 1
            read += 1
        except OSError:
            unreadable.append("%s: %s" % (name, shown))
            continue
        if found:
            entries.append({"mod": name, "rel": shown, "path": path, "names": found})
    if len(_memo) > 400_000:
        _memo.clear()

    def reader_of(file_name: str) -> dict | None:
        return next((k for k in kinds_known if re.search(k["pattern"], file_name, re.IGNORECASE)), None)

    by_kind: dict[str, int] = {}
    for rel in winners:
        m = KIND.search(rel.rsplit("/", 1)[-1])
        if m:
            by_kind[m.group(1).upper()] = by_kind.get(m.group(1).upper(), 0) + 1
    kinds = []
    for kind, n in sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])):
        reader = reader_of("x_%s.ini" % kind)
        kinds.append({"kind": "_%s.ini" % kind, "files": n, "read_by_modtrap": reader is not None,
                      "framework": reader["framework"] if reader else ""})
    frameworks = []
    for low, (dll, mod_name) in sorted(dll_of.items()):
        reader = next((k for k in kinds_known if str(k.get("dll", "")).lower() == low), None)
        frameworks.append({"dll": dll, "mod": mod_name, "framework": reader["framework"] if reader else "",
                           "read_by_modtrap": reader is not None})
    return {"entries": entries, "files": len(winners), "read": read, "too_large": too_large, "unreadable": unreadable,
            "cut_mods": cut_mods, "hidden": hidden, "mods": mods, "places": list(places), "kinds": kinds,
            "frameworks": frameworks, "seconds": round(time.monotonic() - started, 1), "fresh": fresh}


def whole(c: dict) -> bool:
    """Whether the look reached everything: no folder cut short, no file too large or unreadable."""
    return not (c["cut_mods"] or c["too_large"] or c["unreadable"])


def public(c: dict) -> dict:
    """The scan without its entries and paths: for the page."""
    return {"files": c["files"], "read": c["read"], "too_large": len(c["too_large"]), "too_large_examples": c["too_large"][:EXAMPLES],
            "unreadable": len(c["unreadable"]), "unreadable_examples": c["unreadable"][:EXAMPLES],
            "cut_mods": c["cut_mods"][:EXAMPLES], "hidden": c["hidden"], "mods": c["mods"], "places": c["places"],
            "kinds": c["kinds"][:60], "frameworks": c["frameworks"][:400], "seconds": c["seconds"],
            "naming": len(c["entries"]), "whole": whole(c)}


def known_plugins(inst: Instance) -> set[str]:
    """Every plugin file name of the modlist, as written: those in the load order and those of every mod, enabled
    or not (a mod taken out is disabled, and its plugin is the one looked for)."""
    out = {n for n, _active in inst.load_order}
    for m in inst.mods:
        out |= set(m.plugins)
    return out


__all__ = ["Names", "data", "known_plugins", "names_in", "names_in_file", "public", "scan", "whole"]
