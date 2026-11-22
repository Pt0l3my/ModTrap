"""The scanner: every settings file that is in force in the modlist, and the frameworks that read them (MT34, WHY§98).

After a demaster ModTrap says whether any settings file of another mod still names the plugin that was taken out
(DESIGN§14). For that to be worth saying, the looking must be whole and it must be the right files:

- every enabled mod is looked through, the game's own Data folder below them and MO2's Overwrite folder above,
  with no time limit that cuts it short;
- beside each mod's top folder and the folders frameworks keep their files in, the whole `meshes` tree is walked
  for the folders of animation replacers, whose condition files can name a plugin (MT35, TL01§26);
- of several mods that carry a file of the same path only the winner counts, as in the game: the one MO2 loads
  last;
- each file is read once and remembered by its path, size and date, so a later look costs only a listing;
- a file is read to its end, however large, up to a size no settings file has;
- what could not be read is counted and named, never passed over in silence, and every look is written to the
  log: what was listed and read, how long it took, and each folder or file that failed, with the reason.

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

from . import logbook
from .instance import Instance

log = logbook.get("scanner")

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
_leaf: dict[tuple[str, int], bool] = {}                      # (folder, date): it held no folder when last listed
_last_failed: tuple | None = None                            # the failures of the last look, as logged
_data: dict | None = None
LOG_FAILURES = 300                   # failures written to the log one by one; beyond that, their number


def data() -> dict:
    """ModTrap's data on settings files (`mentions.json`): the kinds it can read a line of, the folders of a mod,
    beside its top folder, where frameworks keep theirs, and the trees searched for folders of a given name."""
    global _data
    if _data is None:
        try:
            with open(Path(__file__).with_name("data") / "mentions.json", "rb") as f:
                got = json.loads(f.read().decode("utf-8"))
            _data = {"kinds": [k for k in got["kinds"] if isinstance(k, dict) and k.get("pattern")],
                     "places": [str(x["folder"]) for x in got.get("places", []) if isinstance(x, dict) and x.get("folder")],
                     "trees": [{"under": str(x["under"]), "folders": [str(n).lower() for n in x["folders"]], "shown": [str(n) for n in x["folders"]],
                                "plugin_folders": [str(n).lower() for n in x.get("plugin_folders", [])]}
                               for x in got.get("trees", []) if isinstance(x, dict) and x.get("under") and x.get("folders")]}
        except (OSError, ValueError, KeyError, TypeError):
            _data = {"kinds": [], "places": ["SKSE/Plugins"], "trees": []}
    return _data


def kind_of(rel: str, installed: set[str] | None = None) -> dict | None:
    """The kind of settings file a path inside a mod is, of those ModTrap can read a line of. A kind marked
    "when_installed" counts only while its framework's program file is among `installed` (lower case): what
    ModTrap read is that framework's handling, not another's that uses the same files."""
    for k in data()["kinds"]:
        if re.search(k["pattern"], rel, re.IGNORECASE):
            if k.get("when_installed") and installed is not None and str(k.get("dll", "")).lower() not in installed:
                return None
            return k
    return None


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


def _rel(path: str, folder: Path) -> str:
    return os.path.relpath(path, folder).replace("\\", "/")


def _settings_files(folder: Path, places: list[str], trees: list[dict] | None = None) -> dict:
    """What one mod's folder holds for the scanner. {"files": [(path inside the mod, lower case; file)], "dlls":
    program files in SKSE/Plugins, "named": [(path inside the mod, lower case; folder)] folders that are named after
    a plugin where a framework reads the name, "failed": [(path inside the mod, reason)] folders that could not be
    listed to their end, "tree_folders": folders found by name in a searched tree, "listed": folders listed,
    "skipped": folders passed by because they held no folder when last listed and have not changed since}."""
    out = {"files": [], "dlls": [], "named": [], "failed": [], "tree_folders": 0, "listed": 0, "skipped": 0}
    files = out["files"]
    subs: dict[str, str] = {}
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.is_dir():
                    subs[e.name.lower()] = e.name
                elif SETTINGS_NAME.search(e.name) and e.name.lower() != "meta.ini":
                    files.append((e.name.lower(), Path(e.path)))
        out["listed"] += 1
    except OSError as e:
        out["failed"].append((".", logbook.why(e)))
        return out

    def whole(base: str, dlls_at_top: bool, plugin_folders: bool) -> None:
        """Every settings file under a folder, to its end."""
        n = 0

        def failed(e):
            out["failed"].append((_rel(getattr(e, "filename", None) or base, folder), logbook.why(e)))

        for here, dirs, names in os.walk(base, onerror=failed):
            dirs.sort()
            out["listed"] += 1
            rel_dir = _rel(here, folder)
            top = here == base
            if top and plugin_folders:
                for d in dirs:
                    if PLUGIN_END.search(d.encode("utf-8", "replace")[-4:]):
                        out["named"].append(((rel_dir + "/" + d).lower(), Path(here) / d))
            for name in names:
                n += 1
                if n > WALK_FILES:
                    out["failed"].append((_rel(base, folder), "more than %s files: not listed to the end" % format(WALK_FILES, ",")))
                    return
                if SETTINGS_NAME.search(name):
                    files.append(((rel_dir + "/" + name).lower(), Path(here) / name))
                elif top and dlls_at_top and name.lower().endswith(".dll"):
                    out["dlls"].append(name)

    def under(start: str, parts: list[str]) -> str | None:
        """The folder `parts` below `start`, whatever the case of its names; None when it is not there."""
        at = start
        for part in parts:
            try:
                with os.scandir(at) as it:
                    found = next((e.name for e in it if e.name.lower() == part.lower() and e.is_dir()), None)
            except OSError as e:
                out["failed"].append((_rel(at, folder), logbook.why(e)))
                return None
            if found is None:
                return None
            at = os.path.join(at, found)
        return at

    for place in places:
        parts = place.split("/")
        if parts[0].lower() not in subs:                        # most mods have none of these folders
            continue
        base = under(os.path.join(str(folder), subs[parts[0].lower()]), parts[1:])
        if base is not None:
            whole(base, place.lower() == "skse/plugins", False)

    for tree in trees or []:
        parts = tree["under"].split("/")
        if parts[0].lower() not in subs:
            continue
        root = under(os.path.join(str(folder), subs[parts[0].lower()]), parts[1:])
        if root is None:
            continue
        stack = [root]
        while stack:
            here = stack.pop()
            held_folder = False
            try:
                with os.scandir(here) as it:
                    for e in it:
                        try:
                            if not e.is_dir():
                                continue
                            held_folder = True
                            low = e.name.lower()
                            if low in tree["folders"]:
                                out["tree_folders"] += 1
                                whole(e.path, False, low in tree["plugin_folders"])
                                continue
                            key = (e.path, e.stat().st_mtime_ns)
                        except OSError as err:
                            out["failed"].append((_rel(e.path, folder), logbook.why(err)))
                            continue
                        if _leaf.get(key):
                            out["skipped"] += 1                 # it held no folder, and nothing was added or taken since
                        else:
                            stack.append(e.path)
                out["listed"] += 1
            except OSError as e:
                out["failed"].append((_rel(here, folder), logbook.why(e)))
                continue
            if not held_folder and here != root:
                try:
                    _leaf[(here, os.stat(here).st_mtime_ns)] = True
                except OSError:
                    pass
    return out


def scan(inst: Instance, known, progress=None) -> dict:
    """Looks through the whole modlist as described above, and writes what it did to the log (`report`). `known` is
    every plugin file name of the modlist (`known_plugins`).

    {"entries": [{"mod", "rel", "path", "names", "folder"}], "files", "read", "too_large", "unreadable", "cut_mods",
     "hidden", "mods", "places", "by_place", "kinds": [{"kind", "files", "read_by_modtrap", "framework"}],
     "frameworks": [{"dll", "mod", "framework", "read_by_modtrap"}], "installed", "seconds", "fresh", ...};
     "hidden" counts files a mod of higher priority replaces, "fresh" those read now and not remembered from an
     earlier look; "too_large", "unreadable" and "cut_mods" are lines of words, each naming the mod, the path
     inside it and the reason."""
    started = time.monotonic()
    names = known if isinstance(known, Names) else Names(known)
    kinds_known, places, trees = data()["kinds"], data()["places"], data()["trees"]
    winners: dict[str, tuple[str, Path, str, bool]] = {}
    dll_of: dict[str, tuple[str, str]] = {}
    cut_mods: list[str] = []
    hidden = mods = tree_folders = listed = skipped = 0
    # In the order the game sees them: its own Data folder, the enabled mods from the lowest priority, Overwrite.
    sources = [({"game": "the game's Data folder", "overwrite": "Overwrite"}.get(m.kind, m.name), m.folder) for m in inst.mods
               if m.folder is not None and ((m.kind == "mod" and m.enabled) or m.kind in ("game", "overwrite")) and m.folder.is_dir()]
    for i, (name, folder) in enumerate(sources):
        mods += 1
        got = _settings_files(folder, places, trees)
        tree_folders += got["tree_folders"]
        listed += got["listed"]
        skipped += got["skipped"]
        for where, reason in got["failed"]:
            cut_mods.append("%s: %s (%s)" % (name, where, reason))
        for is_folder, found in ((False, got["files"]), (True, got["named"])):
            for rel, path in found:
                hidden += rel in winners
                try:
                    shown = path.relative_to(folder).as_posix()
                except ValueError:
                    shown = rel
                winners[rel] = (name, path, shown, is_folder)
        for d in got["dlls"]:
            dll_of[d.lower()] = (d, name)
        if progress is not None and i % 200 == 0:
            progress(i, len(sources))
    listing = time.monotonic() - started
    installed = set(dll_of)
    entries: list[dict] = []
    read = fresh = size_read = 0
    too_large: list[str] = []
    unreadable: list[str] = []
    for rel, (name, path, shown, is_folder) in sorted(winners.items()):
        if is_folder:                                           # a folder named after a plugin: the name is the mention
            found = names_in(path.name.encode("utf-8", "replace"), names)
            if found:
                entries.append({"mod": name, "rel": shown, "path": path, "names": found, "folder": True})
            continue
        try:
            st = path.stat()
            if st.st_size > SETTINGS_BYTES:
                too_large.append("%s: %s (%s MB)" % (name, shown, format(st.st_size // (1024 * 1024), ",")))
                continue
            key = (str(path), st.st_size, st.st_mtime_ns, names.mark)
            found = _memo.get(key)
            if found is None:
                found = names_in_file(path, names)
                _memo[key] = found
                fresh += 1
                size_read += st.st_size
            read += 1
        except OSError as e:
            unreadable.append("%s: %s (%s)" % (name, shown, logbook.why(e)))
            continue
        if found:
            entries.append({"mod": name, "rel": shown, "path": path, "names": found, "folder": False})
    if len(_memo) > 400_000:
        _memo.clear()
    if len(_leaf) > 2_000_000:
        _leaf.clear()

    # What was found, by where it lies and by kind.
    tree_names = {n for t in trees for n in t["folders"]}
    by_place: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_known: dict[int, int] = {}
    n_files = n_folders = 0
    for rel, (_name, _path, _shown, is_folder) in winners.items():
        if is_folder:
            n_folders += 1
            continue
        n_files += 1
        parts = rel.split("/")
        if len(parts) == 1:
            place = "top folder"
        elif tree_names & set(parts[:-1]):
            place = "animation replacers' folders"
        else:
            place = next((p for p in places if rel.startswith(p.lower() + "/")), "elsewhere")
        by_place[place] = by_place.get(place, 0) + 1
        known_kind = next((i for i, k in enumerate(kinds_known) if re.search(k["pattern"], rel, re.IGNORECASE)), None)
        if known_kind is not None:
            by_known[known_kind] = by_known.get(known_kind, 0) + 1
        else:
            m = KIND.search(parts[-1])
            if m:
                by_kind[m.group(1).upper()] = by_kind.get(m.group(1).upper(), 0) + 1
    kinds = []
    for i, n in sorted(by_known.items(), key=lambda kv: (-kv[1], kv[0])):
        k = kinds_known[i]
        there = not k.get("when_installed") or str(k.get("dll", "")).lower() in installed
        kinds.append({"kind": str(k.get("label") or k["pattern"]), "files": n, "read_by_modtrap": there, "framework": k["framework"],
                      "why_not": "" if there else "its framework's program file (%s) is not installed" % k.get("dll", "")})
    for kind, n in sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0])):
        kinds.append({"kind": "…_%s.ini" % kind, "files": n, "read_by_modtrap": False, "framework": "", "why_not": ""})
    frameworks = []
    for low, (dll, mod_name) in sorted(dll_of.items()):
        reader = next((k for k in kinds_known if str(k.get("dll", "")).lower() == low), None)
        frameworks.append({"dll": dll, "mod": mod_name, "framework": reader["framework"] if reader else "",
                           "read_by_modtrap": reader is not None})
    out = {"entries": entries, "files": n_files, "named_folders": n_folders, "read": read, "too_large": too_large,
           "unreadable": unreadable, "cut_mods": cut_mods, "hidden": hidden, "mods": mods, "places": list(places),
           "trees": [{"under": t["under"], "folders": list(t["shown"])} for t in trees], "tree_folders": tree_folders,
           "by_place": by_place, "kinds": kinds, "frameworks": frameworks, "installed": installed,
           "listed": listed, "skipped": skipped, "listing_seconds": round(listing, 1), "bytes_read": size_read,
           "seconds": round(time.monotonic() - started, 1), "fresh": fresh, "failed": ""}
    report(out)
    return out


def failed(reason: str) -> dict:
    """The account of a look that could not be made at all: nothing was looked through, and it says so."""
    return {"entries": [], "files": 0, "named_folders": 0, "read": 0, "too_large": [], "unreadable": [], "cut_mods": [],
            "hidden": 0, "mods": 0, "places": list(data()["places"]), "trees": [], "tree_folders": 0, "by_place": {},
            "kinds": [], "frameworks": [], "installed": set(), "listed": 0, "skipped": 0, "listing_seconds": 0.0,
            "bytes_read": 0, "seconds": 0.0, "fresh": 0, "failed": reason}


def report(c: dict) -> None:
    """One look, written to the log: what was listed and read, the time it took, and whether it reached
    everything. Every folder and file that failed is written on a line of its own, with the reason, the first time
    and whenever the failures are not the same as at the last look."""
    global _last_failed
    accounted = c["read"] + len(c["too_large"]) + len(c["unreadable"])
    log.info("looked through %d source(s) (the game's Data folder, the enabled mods, Overwrite): %s folder(s) listed, %s passed "
             "by as unchanged, %d folder(s) of animation replacers found; listing took %.1f s",
             c["mods"], format(c["listed"], ","), format(c["skipped"], ","), c["tree_folders"], c["listing_seconds"])
    log.info("settings files in force: %s (%s), not counting %s hidden by a mod of higher priority; %s folder(s) named after a plugin",
             format(c["files"], ","), ", ".join("%s %s" % (format(n, ","), place) for place, n in sorted(c["by_place"].items())) or "none",
             format(c["hidden"], ","), format(c["named_folders"], ","))
    log.info("read: %s of %s to the end (%s now, %.1f MB; the rest remembered as unchanged); %d name a plugin of the modlist; "
             "the whole look took %.1f s", format(c["read"], ","), format(c["files"], ","), format(c["fresh"], ","),
             c["bytes_read"] / (1024 * 1024), len(c["entries"]), c["seconds"])
    if accounted != c["files"]:
        log.error("the scanner's own count does not add up: %d file(s) in force, %d accounted for; its answer is not to be relied on",
                  c["files"], accounted)
    lines = ([("could not be listed to the end", x) for x in c["cut_mods"]] + [("could not be opened", x) for x in c["unreadable"]]
             + [("too large to be a settings file, not read", x) for x in c["too_large"]])
    if not lines:
        log.info("the look is whole: every folder was listed to its end and every file read")
        _last_failed = ()
        return
    log.warn("the look is NOT whole: %d folder(s) could not be listed to the end, %d file(s) could not be opened, %d file(s) "
             "are too large", len(c["cut_mods"]), len(c["unreadable"]), len(c["too_large"]))
    if tuple(lines) == _last_failed:
        log.info("the same %d as at the last look, named in the log above", len(lines))
        return
    _last_failed = tuple(lines)
    for what, x in lines[:LOG_FAILURES]:
        log.warn("%s: %s", what, x)
    if len(lines) > LOG_FAILURES:
        log.warn("… and %d more that are not written out", len(lines) - LOG_FAILURES)


def whole(c: dict) -> bool:
    """Whether the look reached everything: it was made, no folder cut short, no file too large or unreadable."""
    return not (c.get("failed") or c["cut_mods"] or c["too_large"] or c["unreadable"])


def public(c: dict) -> dict:
    """The scan without its entries and paths: for the page."""
    return {"files": c["files"], "named_folders": c["named_folders"], "read": c["read"], "too_large": len(c["too_large"]),
            "too_large_examples": c["too_large"][:EXAMPLES], "unreadable": len(c["unreadable"]),
            "unreadable_examples": c["unreadable"][:EXAMPLES], "cut": len(c["cut_mods"]), "cut_mods": c["cut_mods"][:EXAMPLES],
            "hidden": c["hidden"], "mods": c["mods"], "places": c["places"], "trees": c["trees"], "tree_folders": c["tree_folders"],
            "by_place": c["by_place"], "kinds": c["kinds"][:60], "frameworks": c["frameworks"][:400], "seconds": c["seconds"],
            "naming": len(c["entries"]), "whole": whole(c), "failed": c.get("failed", "")}


def known_plugins(inst: Instance) -> set[str]:
    """Every plugin file name of the modlist, as written: those in the load order and those of every mod, enabled
    or not (a mod taken out is disabled, and its plugin is the one looked for)."""
    out = {n for n, _active in inst.load_order}
    for m in inst.mods:
        out |= set(m.plugins)
    return out


__all__ = ["Names", "data", "failed", "kind_of", "known_plugins", "names_in", "names_in_file", "public", "report", "scan", "whole"]
