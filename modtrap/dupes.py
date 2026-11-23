"""The same mod twice, and mods that do nothing where they stand (MT65, DESIGN§25).

Two looks at a whole modlist, both reading only:

- `quick`, when a modlist is opened: from what is in memory and one listing per mod. The same file of the same mod
  at Nexus installed twice; a mod whose name is another's with a copy's mark; a plugin of the same name in two
  enabled mods; the same script extender plugin in two enabled mods.
- `deep`, when the owner asks for a scan: every enabled mod's files are listed once, from the highest priority
  down. A mod whose every file is overwritten does nothing where it stands; a mod most of whose files are in one
  other mod is likely that mod again. Archives of the older game and script extender plugins for another version of
  the game are named too.

`same_as` answers, for an archive about to be installed, which mods of the list are that mod already.

Findings have the shape `evaluate` gives them, with "mods": the mods a finding is about, for the page to link.
"""

from __future__ import annotations

import os
import re
import struct
import time
from pathlib import Path

from . import adding, evaluate, logbook, model, steps
from .instance import fold

log = logbook.get("scan")
DEEP_SECONDS = 240.0
COPY_MARK = re.compile(r"(\s*\(\d+\)|\s*-\s*copy(\s*\(\d+\))?|\s+copy)$", re.IGNORECASE)


def letters(text: str) -> str:
    """A name as it is compared: its letters and digits alone, in lower case."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def newer(a: str, b: str) -> int:
    """1 when version `a` is the newer one, -1 when `b` is, 0 when they are the same or cannot be told apart."""
    def parts(v: str) -> list[int]:
        return [int(x) for x in re.findall(r"\d+", v or "")]
    x, y = parts(a), parts(b)
    if not x or not y:
        return 0
    n = max(len(x), len(y))
    x, y = x + [0] * (n - len(x)), y + [0] * (n - len(y))
    return 0 if x == y else 1 if x > y else -1


def _stem(archive: str) -> str:
    return letters(adding.from_archive_name(archive)["stem"]) if archive else ""


def _entry(m: model.Model, row: dict) -> dict:
    mod = m.instance.mod(row["mod"])
    return {"mod": row["mod"], "version": row.get("version") or "", "enabled": bool(row.get("enabled")), "priority": mod.priority if mod is not None else -1}


def same_as(m: model.Model, rows: list[dict], archive: str, name: str = "") -> list[dict]:
    """The mods of the list that are the mod in `archive` already: installed from a file of the same name at the
    same Nexus page, or carrying the name the new mod would get. Each with its version and how it was told."""
    said = adding.from_archive_name(archive)
    stem = letters(said["stem"])
    out, seen = [], set()
    for r in rows:
        how = ""
        if said["mod_id"] and r.get("host") == "nexus" and r.get("mod_id") == said["mod_id"] and stem and stem in (_stem(r.get("archive") or ""), letters(r["mod"])):
            how = "the same file of the same page at Nexus"
        elif stem and len(stem) >= 4 and stem in (letters(r["mod"]), letters(COPY_MARK.sub("", r["mod"]))) and (not said["mod_id"] or not r.get("mod_id") or r.get("mod_id") == said["mod_id"]):
            how = "it has the name this file gives its mod"
        elif stem and len(stem) >= 6 and stem == _stem(r.get("archive") or "") and not (said["mod_id"] and r.get("mod_id") and said["mod_id"] != r.get("mod_id")):
            how = "it was installed from a file of the same name"
        if how and r["mod"] not in seen:
            seen.add(r["mod"])
            e = _entry(m, r)
            e.update(how=how, mine=said["version"], newer=newer(said["version"], e["version"]))
            out.append(e)
    out.sort(key=lambda e: (not e["enabled"], -e["priority"]))        # the one in use first: the one an update would replace
    return out


def _find(folder: Path, *names: str) -> Path | None:
    """`folder/names…`, whatever case the names are written in on disk."""
    at = folder
    for want in names:
        try:
            with os.scandir(at) as it:
                hit = next((e.path for e in it if e.name.lower() == want and e.is_dir(follow_symlinks=False)), None)
        except OSError:
            return None
        if hit is None:
            return None
        at = Path(hit)
    return at


def _finding(key: str, level: str, title: str, text: str, items: list[str], mods: list[str]) -> dict:
    return {"key": key, "level": level, "title": title, "text": text, "items": items[:evaluate.ITEMS], "more": max(0, len(items) - evaluate.ITEMS), "mods": mods[:evaluate.ITEMS]}


def _told(e: dict) -> str:
    return "“%s”%s, %s, priority %d" % (e["mod"], " version %s" % e["version"] if e["version"] else "", "enabled" if e["enabled"] else "disabled", e["priority"])


def quick(m: model.Model, rows: list[dict]) -> list[dict]:
    """What can be told without listing every file."""
    out: list[dict] = []
    grouped: set[str] = set()
    # The same file of the same mod at Nexus, twice.
    by: dict[tuple, list[dict]] = {}
    for r in rows:
        if r.get("host") == "nexus" and r.get("mod_id") and _stem(r.get("archive") or ""):
            by.setdefault((r.get("game"), r["mod_id"], _stem(r["archive"])), []).append(r)
    for (_game, _mod_id, _s), rs in sorted(by.items(), key=lambda kv: fold(kv[1][0]["mod"])):
        if len(rs) < 2:
            continue
        es = sorted((_entry(m, r) for r in rs), key=lambda e: e["priority"])
        live = sum(e["enabled"] for e in es)
        grouped.update(e["mod"] for e in es)
        versions = {e["version"] for e in es if e["version"]}
        out.append(_finding("duplicate", "bad" if live > 1 else "info", "The same mod %s" % ("twice" if len(es) == 2 else "%d times" % len(es)),
                            "These were installed from the same file of the same page at Nexus%s. %s"
                            % (", in different versions" if len(versions) > 1 else "",
                               "More than one is enabled: they overwrite each other file for file, and of plugins with the same name only one is loaded. Keep the newer one enabled."
                               if live > 1 else "Only one of them is enabled, so nothing is doubled in the game."), [_told(e) for e in es], [e["mod"] for e in es]))
    # A name that is another mod's name with a copy's mark.
    names = {fold(x.name): x for x in m.instance.mods if x.kind == "mod"}
    for x in m.instance.mods:
        base = COPY_MARK.sub("", x.name)
        twin = names.get(fold(base)) if x.kind == "mod" and base != x.name else None
        if twin is None or (x.name in grouped and twin.name in grouped):
            continue
        both = x.enabled and twin.enabled
        out.append(_finding("copy-name", "warn" if both else "info", "A mod named as a copy of another",
                            "“%s” has the name of “%s” with a copy's mark. %s" % (x.name, twin.name, "Both are enabled." if both else "Only one of the two is enabled."),
                            ["“%s”, %s, priority %d" % (y.name, "enabled" if y.enabled else "disabled", y.priority) for y in (twin, x)], [twin.name, x.name]))
    # A plugin of the same name in two enabled mods: the lower one's is never loaded.
    hidden: dict[str, list[str]] = {}
    for x in m.instance.mods:
        if x.kind != "mod" or not x.enabled:
            continue
        for p in x.plugins:
            row = m.row(p)
            if row is not None and row.source not in (None, x.name):
                hidden.setdefault(row.source, []).append("%s: “%s” has it too, and its copy is not the one loaded" % (p, x.name))
                hidden.setdefault("\0" + row.source, []).append(x.name)
    for winner in sorted((k for k in hidden if not k.startswith("\0")), key=fold):
        out.append(_finding("plugin-twice", "warn", "A plugin of the same name in two enabled mods",
                            "MO2 loads the plugin of the mod with the higher priority, “%s”. The other mod's plugin of that name is never read: right for a patch or a "
                            "newer version made to replace it, a fault where two different mods happen to share a name." % winner,
                            hidden[winner], [winner] + sorted(set(hidden["\0" + winner]), key=fold)))
    # The same script extender plugin in two enabled mods.
    dlls: dict[str, list] = {}
    for x in m.instance.mods:
        if x.kind != "mod" or not x.enabled or x.folder is None:
            continue
        d = _find(x.folder, "skse", "plugins")
        if d is None:
            continue
        try:
            for n in os.listdir(d):
                if n.lower().endswith(".dll"):
                    dlls.setdefault(n.lower(), []).append(x)
        except OSError:
            continue
    for name, xs in sorted(dlls.items()):
        if len(xs) < 2:
            continue
        xs.sort(key=lambda y: y.priority)
        out.append(_finding("extender-twice", "warn", "The same script extender plugin in %d enabled mods" % len(xs),
                            "%s is in each of them; only the one of “%s” is loaded. Mostly this is one mod in two versions, or a mod and an older fix for it." % (name, xs[-1].name),
                            ["“%s”, priority %d%s" % (y.name, y.priority, ": loaded" if y is xs[-1] else "") for y in xs], [y.name for y in xs]))
    return out


def deep(m: model.Model, progress=None, seconds: float = DEEP_SECONDS) -> dict:
    """Every enabled mod's files, listed once from the highest priority down: {"findings", "mods", "files", "cut",
    "seconds"}."""
    started = time.monotonic()
    stop = started + seconds
    mods = sorted((x for x in m.instance.mods if x.kind == "mod" and x.enabled and x.folder is not None), key=lambda x: -x.priority)
    winner: dict[int, int] = {}                  # a path's mark -> the mod that wins it (its number in `mods`)
    out: list[dict] = []
    cut = False
    files = 0
    nothing, mostly, old_archives, wrong = [], [], [], []
    game = evaluate.game_version(m.instance.game_dir)
    memo: dict = {}
    for i, x in enumerate(mods):
        if time.monotonic() > stop:
            cut = True
            break
        if progress is not None and i % 25 == 0:
            progress(i, len(mods))
        listed, c = steps.walk(x.folder)
        cut = cut or c
        real = [f for f in listed if f.lower() != "meta.ini" and not evaluate.PAPERS.search(f.lower())]
        files += len(listed)
        over: dict[int, int] = {}
        for f in real:
            lf = f.lower()
            mark = hash(lf)
            w = winner.setdefault(mark, i)
            if w != i:
                over[w] = over.get(w, 0) + 1
            if "/" not in f and lf.endswith(".bsa"):
                h = evaluate._head(x.folder / f, 8)
                if h[:4] == b"BSA\0" and len(h) >= 8 and struct.unpack_from("<I", h, 4)[0] < 105:
                    old_archives.append((x.name, f))
            elif game is not None and lf.startswith("skse/plugins/") and lf.endswith(".dll") and lf.count("/") == 2 and w == i:
                try:
                    data = (x.folder / f).read_bytes() if (x.folder / f).stat().st_size <= evaluate.COMPARE_ONE else b""
                except OSError:
                    data = b""
                new, old = b"SKSEPlugin_Version\0" in data, b"SKSEPlugin_Query\0" in data
                if (game >= (1, 6, 0) and old and not new) or (game < (1, 6, 0) and new and not old):
                    wrong.append((x.name, f, "1.5" if old else "1.6"))
        lost = sum(over.values())
        if real and lost == len(real) and not adding.is_output_mod(m, x, memo):
            top = sorted(over.items(), key=lambda kv: -kv[1])[:3]
            nothing.append((x, len(real), [(mods[w].name, n) for w, n in top]))
        elif len(real) >= 5 and over:
            w, n = max(over.items(), key=lambda kv: kv[1])
            if n >= 0.9 * len(real):
                mostly.append((x, len(real), mods[w].name, n))
    if progress is not None:
        progress(len(mods), len(mods))
    if nothing:
        nothing.sort(key=lambda t: -t[1])
        out.append(_finding("does-nothing", "warn", "%d enabled mod%s nothing where %s" % (len(nothing), " does" if len(nothing) == 1 else "s do", "it stands" if len(nothing) == 1 else "they stand"),
                            "Every file of each of these is overwritten by mods above it, so the game loads none of it. Often it is an older version left enabled beside the "
                            "newer one, or a mod another mod has taken in whole. (A mod whose plugin alone matters has that plugin among its files, and is not listed here.)",
                            ["“%s” (priority %d, %d file%s): overwritten by %s" % (x.name, x.priority, n, "" if n == 1 else "s", ", ".join("“%s” (%d)" % t for t in top)) for x, n, top in nothing],
                            [x.name for x, _n, _t in nothing]))
    if mostly:
        mostly.sort(key=lambda t: -t[3])
        out.append(_finding("mostly-in-another", "info", "%d mod%s mostly inside another mod" % (len(mostly), " is" if len(mostly) == 1 else "s are"),
                            "Nine in ten or more of these mods' files are in one mod above them too, which wins them. That is what a base mod under its newer version, or under "
                            "a pack that carries it, looks like; what is left of the lower mod may still matter.",
                            ["“%s” (priority %d): %d of %d files are in “%s” too" % (x.name, x.priority, n, total, w) for x, total, w, n in mostly], [x.name for x, *_r in mostly]))
    if old_archives:
        out.append(_finding("archive-format", "bad", "Archives in the older game's format",
                            "Packed for the older Skyrim. Special Edition does not load such an archive and can stop at its start because of it.",
                            ["“%s”: %s" % t for t in old_archives], sorted({t[0] for t in old_archives}, key=fold)))
    if wrong:
        out.append(_finding("extender-version", "bad", "Script extender plugins for another version of the game",
                            "This game is version %d.%d.%d. The script extender does not load a plugin built for another version, and what the mod does through it is missing."
                            % game, ["“%s”: %s, built for game version %s" % t for t in wrong], sorted({t[0] for t in wrong}, key=fold)))
    return {"findings": out, "mods": len(mods), "files": files, "cut": cut, "seconds": round(time.monotonic() - started, 1)}


__all__ = ["deep", "letters", "newer", "quick", "same_as"]
