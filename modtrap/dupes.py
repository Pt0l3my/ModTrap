"""The same mod twice, and mods that do nothing where they stand (MT65, DESIGN§25).

Two looks at a whole modlist, both reading only:

- `quick`, when a modlist is opened: from the mods' own records and a look at a few pairs. Obsolete mods (disabled,
  with a newer version enabled), redundant ones (enabled, wholly inside their newer version), and two copies of
  one mod both in the game (MT68).
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
DEEP_FILES = 2_000_000                # files of one mod listed at most in the scan of every mod: a tool's output can hold hundreds of thousands
DEEP_ONE = 60.0                       # seconds for the listing of one mod's folder
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
    return {"mod": row["mod"], "version": row.get("version") or adding.version_in(row["mod"]), "enabled": bool(row.get("enabled")), "priority": mod.priority if mod is not None else -1}


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
        elif stem and len(stem) >= 4 and stem in (letters(r["mod"]), letters(COPY_MARK.sub("", r["mod"])), letters(adding.title_of(r["mod"], r.get("version") or ""))) and (not said["mod_id"] or not r.get("mod_id") or r.get("mod_id") == said["mod_id"]):
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


def _file(folder: Path, rel: str) -> Path | None:
    """A file of a mod by its path in another mod, whatever case its folders and its name are written in there."""
    direct = folder / rel
    if direct.is_file():
        return direct
    *dirs, name = rel.lower().split("/")
    at = _find(folder, *dirs)
    if at is None:
        return None
    try:
        with os.scandir(at) as it:
            return next((Path(e.path) for e in it if e.name.lower() == name and e.is_file(follow_symlinks=False)), None)
    except OSError:
        return None


def _finding(key: str, level: str, title: str, text: str, items: list[str], mods: list[str]) -> dict:
    return {"key": key, "level": level, "title": title, "text": text, "items": items[:evaluate.ITEMS], "more": max(0, len(items) - evaluate.ITEMS), "mods": mods[:evaluate.ITEMS]}


def _told(e: dict) -> str:
    return "“%s”%s, %s, priority %d" % (e["mod"], " version %s" % e["version"] if e["version"] else "", "enabled" if e["enabled"] else "disabled", e["priority"])


def base_title(name: str, version: str = "") -> str:
    """A mod's title as two mods are compared by it: without a copy's mark and without a version at its end, its
    letters and digits alone. Two mods are "the same title" only where these are equal: "Lantern" and "Lantern 2.1"
    are, "Lantern" and "Lantern Patch" are not."""
    bare = COPY_MARK.sub("", name)
    return letters(adding.title_of(bare, version))


def _inside(lower, higher, seconds: float = 4.0) -> tuple[int, int]:
    """How many of the lower mod's files the higher mod has too, and how many the lower has: (shared, all).
    Papers and the mod's own record do not count."""
    stop = time.monotonic() + seconds
    files, cut = steps.walk(lower.folder)
    real = [f for f in files if f.lower() != "meta.ini" and not evaluate.PAPERS.search(f.lower())]
    if cut or not real:
        return 0, 0
    found, cut2 = adding.shared_files(higher.folder, adding._trie(real), stop)
    return (0, 0) if cut2 else (len(found), len(real))


def quick(m: model.Model, rows: list[dict]) -> list[dict]:
    """What can be told from the mods' own records and a look at a few pairs of them (MT68). Three notes, each a
    list, none of them more than a note unless two copies of one mod are both in the game:

    - obsolete: a disabled mod whose newer version is enabled;
    - redundant: an enabled mod whose every file is in its own newer version (or its copy), which wins them;
    - twice: two mods of the same title, both enabled, where the higher does not replace the lower whole.

    Two mods are "the same mod" where their titles are the same (`base_title`), or where both were installed from
    the same file of the same Nexus page. A patch, a fix or a version of the list's author that carries another
    mod's name in its own is a different title, and is left alone; so is one file installed as two mods with
    different names, each holding part of it."""
    by_row = {r["mod"]: r for r in rows}
    groups: dict[tuple, list] = {}
    for x in m.instance.mods:
        if x.kind != "mod" or x.folder is None:
            continue
        r = by_row.get(x.name) or {}
        version = r.get("version") or adding.version_in(x.name)
        title = base_title(x.name, r.get("version") or "")
        if len(title) >= 3:
            groups.setdefault(("title", title), []).append((x, version, title))
        if r.get("host") == "nexus" and r.get("mod_id") and _stem(r.get("archive") or ""):
            groups.setdefault(("file", r.get("game"), r["mod_id"], _stem(r["archive"])), []).append((x, version, title))
    obsolete, redundant, twice, seen = [], [], [], set()
    told = lambda x, v: "“%s”%s (%s, priority %d)" % (x.name, " version %s" % v if v else "", "enabled" if x.enabled else "disabled", x.priority)      # noqa: E731
    for key, members in sorted(groups.items(), key=lambda kv: (kv[0][0] != "title", fold(kv[1][0][0].name))):
        live = [t for t in members if t[0].enabled]
        if len(members) < 2 or not live:
            continue                                    # alone, or none of them in the game
        keeper, kv, ktitle = max(live, key=lambda t: t[0].priority)
        for x, v, title in members:
            pair = frozenset((x.name, keeper.name))
            if x is keeper or pair in seen:
                continue
            same_title = title == ktitle
            if not x.enabled:
                if same_title or newer(kv, v) > 0:      # by its file alone, only where the enabled one is the newer
                    seen.add(pair)
                    obsolete.append((x, "%s: its %s is %s" % (told(x, v), "newer version" if newer(kv, v) > 0 else "other copy", told(keeper, kv))))
                continue
            shared, total = _inside(x, keeper)
            if total and shared == total:
                seen.add(pair)
                redundant.append((x, "%s: all %d of its files are in %s too" % (told(x, v), total, told(keeper, kv))))
            elif same_title:
                seen.add(pair)
                twice.append((x, keeper, "%s and %s: %s" % (told(x, v), told(keeper, kv), "%d of the lower one's %d files are not in the higher one, and still load" % (total - shared, total)
                                                         if total else "the lower one's files could not be compared")))
    out: list[dict] = []
    if twice:
        out.append(_finding("twice", "warn", "%d mod%s twice in the game" % (len(twice), " is" if len(twice) == 1 else "s are"),
                            "Two mods of the same title are both enabled, and the one with the higher priority does not replace the other whole: the files only the lower "
                            "one has are loaded together with the higher one's. If they are two versions of one mod, keep the newer one enabled.",
                            [t for _x, _k, t in twice], [n for x, k, _t in twice for n in (x.name, k.name)]))
    if redundant:
        out.append(_finding("redundant", "info", "Redundant: %d enabled mod%s wholly inside %s" % (len(redundant), "" if len(redundant) == 1 else "s", "its newer version" if len(redundant) == 1 else "their newer versions"),
                            "Each of these is enabled, but every file of it is in the other mod too, which has the higher priority: the game loads nothing of it. "
                            "Disabling it changes nothing in the game.", [t for _x, t in redundant], [x.name for x, _t in redundant]))
    if obsolete:
        out.append(_finding("obsolete", "info", "Obsolete: %d disabled mod%s a newer version enabled" % (len(obsolete), " has" if len(obsolete) == 1 else "s have"),
                            "Each of these is disabled, and the same mod is enabled in another version: nothing of the older one is in the game. It can stay, as the way "
                            "back, or be uninstalled.", [t for _x, t in obsolete], [x.name for x, _t in obsolete]))
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
    nothing, mostly, old_archives, wrong, unused = [], [], [], [], []
    game = evaluate.game_version(m.instance.game_dir)
    memo: dict = {}
    for i, x in enumerate(mods):
        if time.monotonic() > stop:
            cut = True
            break
        if progress is not None and i % 25 == 0:
            progress(i, len(mods))
        listed, c = steps.walk(x.folder, DEEP_FILES, DEEP_ONE)
        cut = cut or c
        real = [f for f in listed if f.lower() != "meta.ini" and not evaluate.PAPERS.search(f.lower())]
        files += len(listed)
        over: dict[int, int] = {}
        dlls: list[str] = []
        for f in real:
            lf = f.lower()
            mark = hash(lf)
            w = winner.setdefault(mark, i)
            if w != i:
                over[w] = over.get(w, 0) + 1
            elif "/" not in f and lf.endswith(".bsa"):
                h = evaluate._head(x.folder / f, 8)
                if h[:4] == b"BSA\0" and len(h) >= 8 and struct.unpack_from("<I", h, 4)[0] < 105:
                    old_archives.append((x.name, f))
            elif game is not None and lf.startswith("skse/plugins/") and lf.endswith(".dll") and lf.count("/") == 2:
                dlls.append(f)
        for f in dlls:                               # only a copy the game loads is judged
            try:
                data = (x.folder / f).read_bytes() if (x.folder / f).stat().st_size <= evaluate.COMPARE_ONE else b""
            except OSError:
                data = b""
            built = evaluate.extender_wrong(game, data)
            if not built:
                continue
            # What the scripts beside it say (WHY§146): the mod's own, and the copies the game loads of them.
            scripts = []
            for s in [s for s in real if s.lower().startswith("scripts/") and s.lower().endswith(".pex") and s.count("/") == 1][:evaluate.SCRIPTS]:
                w = winner.get(hash(s.lower()), i)
                loaded = _file(mods[w].folder, s) if w != i else x.folder / s
                scripts.append((s.lower(), x.folder / s, loaded or x.folder / s, mods[w].name if w != i and loaded is not None else ""))
            use = evaluate.plugin_use(data, scripts)
            line = "“%s”: %s, built for game version %s" % (x.name, f, built)
            if use is not None and not use["now"] and (use["own"] or use["taken_over"]):
                unused.append((x.name, line + "; " + evaluate.use_told(use)))
            else:
                above = sorted(over.items(), key=lambda kv: -kv[1])[:3]
                wrong.append((x.name, line + ("; " + evaluate.use_told(use) if use is not None and use["now"] else "")
                              + ("; %s of this mod's files, this plugin not among them" % ", ".join("“%s” replaces %d" % (mods[w].name, n) for w, n in above) if above else "")))
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
        out.append(_finding("does-nothing", "info", "Redundant: %d enabled mod%s wholly overwritten by the mods above %s" % (len(nothing), " is" if len(nothing) == 1 else "s are", "it" if len(nothing) == 1 else "them"),
                            "Every file of each of these is overwritten by mods above it, so the game loads none of it. Often it is an older version left enabled beside the "
                            "newer one, or a mod another mod has taken in whole. Disabling one changes nothing in the game.",
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
                            "This game is version %d.%d.%d. The script extender does not load a plugin built for another version, and what the mod does through it is missing. "
                            "A mod above that replaces the plugin itself, or the scripts that call it, is taken into account; one that replaces other files is not a fix for this."
                            % game, [t[1] for t in wrong], sorted({t[0] for t in wrong}, key=fold)))
    if unused:
        out.append(_finding("extender-unused", "info", "Script extender plugins for another version of the game, which nothing calls now",
                            "The script extender does not load these, but a mod above replaced the scripts that called them: as the game loads each mod's scripts, none "
                            "calls its plugin any more. The scripts of other mods were not read.",
                            [t[1] for t in unused], sorted({t[0] for t in unused}, key=fold)))
    return {"findings": out, "mods": len(mods), "files": files, "cut": cut, "seconds": round(time.monotonic() - started, 1)}


__all__ = ["base_title", "deep", "letters", "newer", "quick", "same_as"]
