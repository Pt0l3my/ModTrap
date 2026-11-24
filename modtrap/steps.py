"""The steps of a demaster (DESIGN§14, MT18): everything it takes to get the ticked mods out of a modlist, worked
out from the modlist itself, the tools set up in MO2 and, once there is one, the dry run. Each step says who does
it, why it is needed, and whether the modlist's own files show it done.

Read-only. Beyond the plugin headers the model already holds, this module lists file names in the ticked mods'
folders, and looks into small settings files of other mods for a ticked plugin's name (WHY§35).
"""

from __future__ import annotations

from collections import Counter

import json
import os
import re
import time
from pathlib import Path

from . import census, dryrun, logbook, model, plugin, toolmade, tools
from .instance import GAME, OVERWRITE, Instance, Mod, fold

log = logbook.get("steps")

WALK_FILES = 60_000            # file names listed in one mod's folder at most
WALK_SECONDS = 4.0
OVERLAP_SHARE = 0.8            # a mod this much made of files the ticked mod also has is "only a replacement" of it

# What a mod's loose files say, by path (lower case, forward slashes). First match wins.
KINDS = (
    ("animations", re.compile(r"(^|/)(animations|behaviors|behaviours|animationdatasinglefile|animationsetdatasinglefile)/|\.hkx$|(^|/)fnis_[^/]*_list\.txt$|^(nemesis_engine|pandora_engine)/")),
    ("face data", re.compile(r"^(meshes|textures)/actors/character/facegendata/")),
    ("lod", re.compile(r"(^|/)lod/|_lod(_\d)?\.nif$|^lodsettings/|^meshes/terrain/|^textures/terrain/|^dyndolod/|\.btr$|\.bto$")),
    ("grass cache", re.compile(r"^grass/|\.cgid$")),
    ("scripts", re.compile(r"^scripts/.*\.pex$")),
    ("script extender plugin", re.compile(r"^skse/plugins/[^/]*\.dll$")),
    ("settings for a script extender plugin", re.compile(r"^skse/plugins/.*\.(ini|json|toml|yaml|yml|txt)$|_(distr|kid|swap|flm|ench|desc|cid)\.ini$")),
    ("sequence file", re.compile(r"^seq/.*\.seq$")),
    ("voice or sound", re.compile(r"^sound/")),
    ("menus", re.compile(r"^(interface|mcm)/")),
    ("bodyslide data", re.compile(r"^calientetools/")),
    ("archive", re.compile(r"^[^/]*\.(bsa|ba2)$")),
    ("meshes", re.compile(r"^meshes/")),
    ("textures", re.compile(r"^textures/")),
)
# The tools a kind of file feeds, by words in the executable's name or program file (lower case).
TOOLS_FOR = {
    "animations": ("pandora", "nemesis", "fnis"),
    "lod": ("dyndolod", "texgen", "xlodgen", "lodgen"),
    "grass cache": ("grass",),
    "bodyslide data": ("bodyslide",),
}
# What a behaviour tool reads of a mod (TL01§12): an animation list beside the mod's animations, with the graph
# file that goes with it, and a patch folder with its info file. Never a plain animation file: the game, or an
# animation framework, loads those as they are.
ANIM_LIST = re.compile(r"(?:^|/)animations/([^/]+)/fnis_([^/]+)_list\.txt$")
ANIM_GRAPH = re.compile(r"(?:^|/)behaviou?rs/fnis_[^/]+_behavior\.hkx$")
ANIM_PATCH = re.compile(r"^(nemesis_engine|pandora_engine)/mod/([^/]+)/")
ANIM_FOLDER = re.compile(r"(?:^|/)animations/([^/]+)/[^/]")
ANIM_READS = {"Pandora Behaviour Engine": ("lists", "nemesis_engine", "pandora_engine"),
              "Nemesis": ("lists", "nemesis_engine"), "FNIS": ("lists",)}
ANIM_SEARCH_SECONDS = 4.0
ANIM_SEARCH_FILE = 64 * 1024 * 1024
CONFIG_NAME = re.compile(r"\.(ini|json|toml|yaml|yml|txt)$", re.IGNORECASE)


def walk(folder: Path, limit: int = WALK_FILES, seconds: float = WALK_SECONDS) -> tuple[list[str], bool]:
    """The files under `folder` as paths relative to it (forward slashes), and whether the listing was cut short.
    Names only; links are not followed."""
    out: list[str] = []
    stop = time.monotonic() + seconds
    stack = [("", folder)]
    while stack:
        rel, d = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            name = rel + e.name
            try:
                if e.is_dir(follow_symlinks=False):
                    stack.append((name + "/", Path(e.path)))
                elif e.is_file(follow_symlinks=False):
                    out.append(name)
            except OSError:
                continue
        if len(out) >= limit or time.monotonic() > stop:
            return out[:limit], True
    return out, False


def contents(folder: Path) -> dict:
    """What kinds of files a mod's folder holds: counts by kind, and a few examples of each."""
    files, cut = walk(folder)
    kinds: dict[str, dict] = {}
    for f in files:
        low = f.lower()
        if low in ("meta.ini",) or low.endswith((".esp", ".esm", ".esl")) and "/" not in low:
            continue
        kind = next((k for k, rx in KINDS if rx.search(low)), "other files")
        entry = kinds.setdefault(kind, {"count": 0, "examples": []})
        entry["count"] += 1
        if len(entry["examples"]) < 3:
            entry["examples"].append(f)
    return {"files": len(files), "cut": cut, "kinds": kinds, "paths": {f.lower() for f in files}}


def _has_file(folder: Path, rel_low: str) -> bool:
    """Is there a file at this path under `folder`, letter case aside (as the game sees it)?"""
    if os.name == "nt":
        return (folder / rel_low).is_file()             # Windows' own file names ignore case
    here = folder
    parts = rel_low.split("/")
    for i, part in enumerate(parts):
        try:
            with os.scandir(here) as it:
                hit = next((e for e in it if e.name.lower() == part), None)
        except OSError:
            return False
        if hit is None:
            return False
        if i == len(parts) - 1:
            return hit.is_file()
        here = Path(hit.path)
    return False


def animation_feed(inst: Instance, paths_low: set[str], skip_mods: set[str]) -> dict:
    """What the mods' loose files give a behaviour tool to read (TL01§12), and whether the files such a tool made
    name one of the mods' own animation folders. Names and a search for those names only."""
    lists, graphs, plain = [], [], 0
    patches: dict[str, set[str]] = {"nemesis_engine": set(), "pandora_engine": set()}
    folders: set[str] = set()
    for p in sorted(paths_low):
        kind = next((k for k, rx in KINDS if rx.search(p)), "")
        if kind != "animations":
            continue
        got = ANIM_LIST.search(p)
        patch = ANIM_PATCH.search(p)
        if got and (got.group(2) == got.group(1) or got.group(2).startswith(got.group(1) + "_")):
            lists.append(p)
            folders.add(got.group(1))
        elif patch:
            patches[patch.group(1)].add(patch.group(2))
        elif ANIM_GRAPH.search(p):
            graphs.append(p)
        else:
            plain += 1
        own = ANIM_FOLDER.search(p)
        if own:
            folders.add(own.group(1))
    # A folder of animations is named in what a behaviour tool writes only if the tool took the mod's animations
    # in: as "animations\<folder>\" in a project file, or by the graph file's name.
    needles = sorted({("animations\\%s\\" % f).encode("utf-8") for f in folders} |
                     {("animations/%s/" % f).encode("utf-8") for f in folders} |
                     {g.rsplit("/", 1)[1].encode("utf-8") for g in graphs})
    searched = []
    binaries = {e.title: e.binary for e in inst.executables}
    until = time.monotonic() + ANIM_SEARCH_SECONDS
    seen: set[str] = set()
    for title, target in sorted(inst.output_mods.items()):
        tool = tools.of_executable(title, binaries.get(title, ""))[0]
        out_mod = inst.mod(target)
        if tool not in ANIM_READS or out_mod is None or out_mod.folder is None or fold(target) in seen \
                or fold(target) in skip_mods:
            continue
        seen.add(fold(target))
        listing, cut = walk(out_mod.folder)
        hits, read = [], 0
        for rel in sorted(listing):
            if not needles or not rel.lower().endswith((".hkx", ".txt", ".xml")):
                continue
            if time.monotonic() > until:
                cut = True
                break
            try:
                f = out_mod.folder / rel
                if f.stat().st_size > ANIM_SEARCH_FILE:
                    cut = True
                    continue
                data = f.read_bytes().lower()
            except OSError:
                cut = True
                continue
            read += 1
            found = [n.decode("utf-8") for n in needles if n in data]
            if found:
                hits.append({"file": rel, "names": found[:4]})
        searched.append({"tool": tool, "mod": target, "files": read, "hits": hits[:DETAILS], "hit_count": len(hits),
                         "cut": cut})
    # Pandora takes a list in only where the graph file that goes with it is in the game's behaviour folder too
    # (TL01§12): in the mod itself, or in any other enabled mod. A list without it is passed over.
    with_graph, without_graph = [], []
    for p in lists:
        got = ANIM_LIST.search(p)
        graph = "%s/behaviors/fnis_%s_behavior.hkx" % (p[:p.rindex("/animations/")], got.group(2))
        alt = graph.replace("/behaviors/", "/behaviours/")
        there = graph in paths_low or alt in paths_low
        if not there:
            for x in inst.mods:
                try:
                    if x.kind == "mod" and x.enabled and x.folder is not None and fold(x.name) not in skip_mods \
                            and (_has_file(x.folder, graph) or _has_file(x.folder, alt)):
                        there = True
                        break
                except OSError:
                    continue
        (with_graph if there else without_graph).append(p)
    return {"lists": lists, "lists_with_graph": with_graph, "lists_without_graph": without_graph,
            "graphs": graphs, "nemesis_engine": sorted(patches["nemesis_engine"]),
            "pandora_engine": sorted(patches["pandora_engine"]), "folders": sorted(folders), "plain": plain,
            "searched": searched}


def tools_for(inst: Instance, kind: str) -> list[str]:
    words = TOOLS_FOR.get(kind, ())
    out = []
    for e in inst.executables:
        hay = (e.title + " " + Path(e.binary.replace("\\", "/")).name).lower()
        if any(w in hay for w in words):
            out.append(e.title)
    return out


def replacements(inst: Instance, trapped: Mod, paths_low: set[str]) -> list[dict]:
    """Other enabled mods made, for the most part, of files the trapped mod also has: a hotfix or an override of
    it. Such a mod names no master, so nothing else would find it (WHY§27, WHY§35)."""
    sample = sorted(p for p in paths_low if p != "meta.ini")[:40]
    if not sample or trapped.folder is None:
        return []
    out = []
    for m in inst.mods:
        if m.kind != "mod" or not m.enabled or m.folder is None or m.name == trapped.name:
            continue
        try:
            if not any((m.folder / s).is_file() for s in sample):
                continue
        except OSError:
            continue
        files, cut = walk(m.folder, limit=20_000, seconds=2.0)
        mine = [f.lower() for f in files if f.lower() != "meta.ini"]
        if not mine:
            continue
        shared = sum(1 for f in mine if f in paths_low)
        if shared / len(mine) >= OVERLAP_SHARE:
            out.append({"mod": m.name, "priority": m.priority, "files": len(mine), "shared": shared, "cut": cut,
                        "wins": m.priority > trapped.priority})
    return out


MENTION_LINES = 40             # lines of one file that are shown
MENTION_LINE = 260             # characters of one line that are shown


def mention_kinds() -> list[dict]:
    """The kinds of settings file ModTrap can read a line of (data, `mentions.json`, TL01§23)."""
    return census.data()["kinds"]


def where_named(line: str, plugin_low: str, layout: str) -> str:
    """Where a line of a settings file names a plugin (TL01§23): "comment" (the line is switched off), "gives" (the
    thing the line gives or changes comes from the plugin), "reaches" (the plugin's things are a condition for
    what the line reaches), "leaves out" (the line leaves the plugin's things out), "only with" and "only without"
    (the line is carried out only while the plugin is, or is not, active), or "" where the layout is not one
    ModTrap reads line by line."""
    text = line.strip()
    if layout == "conditions":
        return ""                                       # read by the file's structure (`_conditions_named`), not by one line
    if not text or text[0] in ";#" or text.startswith("//"):
        return "comment"
    if layout == "flm" and "=" in text:
        # FormList Manipulator (TL01§24): key = list|forms|filter, or Filter = name|conditions. A condition is a
        # plugin's name with + (only while it is active) or - (only while it is not), several joined by &.
        key, rest = text.split("=", 1)
        fields = rest.split("|")
        conditions = fields[1:] if key.strip().lower() == "filter" else fields[2:]
        found = ""
        for field in conditions:
            for item in re.split(r"[,&]", field):
                if plugin_low in item.lower():
                    if item.strip().startswith("-"):
                        return "only without"
                    found = "only with"
        if found:
            return found
        return "gives" if any(plugin_low in f.lower() for f in fields[:2]) else "only with"
    if layout != "pipes" or "=" not in text:
        return ""
    fields = text.split("=", 1)[1].split("|")
    if plugin_low in fields[0].lower():
        return "gives"
    found = ""
    for field in fields[1:]:
        for item in field.split(","):
            if plugin_low not in item.lower():
                continue
            # Conditions joined by + must all hold; each can be negated on its own.
            for part in item.split("+"):
                if plugin_low in part.lower():
                    if part.strip().startswith("-"):
                        return "leaves out"
                    found = "reaches"
    return found or "reaches"


def _conditions_named(text: str, lows: list[str], is_json: bool, kind: dict) -> dict[int, str]:
    """For an animation replacer's condition file (TL01§26): each line that names one of these plugins, with
    "condition" (a condition that does not hold once its thing is gone), "may hold" (one that can), or "" (a
    condition ModTrap does not know, or one it could not tell). The condition a mention belongs to is read from
    the file's own structure, never guessed from the line."""
    settled = {str(n).lower() for n in kind.get("settled", [])}
    unsettled = {str(n).lower() for n in kind.get("unsettled", {})}
    worst_first = ("", "may hold", "condition")

    def verdict(name: str) -> str:
        low = name.lower()
        return "condition" if low in settled else "may hold" if low in unsettled else ""

    hit = [n for n, line in enumerate(text.splitlines(), 1) if any(p in line.lower() for p in lows)]
    if not is_json:
        out = {}
        lines = text.splitlines()
        for n in hit:
            m = re.match(r"\s*(?:NOT\s+)?(\w+)\s*\(", lines[n - 1])
            out[n] = verdict(m.group(1)) if m else ""
        return out
    try:
        tree = json.loads(text)
    except ValueError:
        return {n: "" for n in hit}
    found: list[str] = []

    def walk(node, name: str) -> None:
        if isinstance(node, dict):
            own = node.get("condition")
            if isinstance(own, str):
                name = own
            plug = node.get("pluginName")
            if isinstance(plug, str) and plug.strip().lower() in lows:
                found.append(verdict(name) if name else "")
            for v in node.values():
                walk(v, name)
        elif isinstance(node, list):
            for v in node:
                walk(v, name)

    walk(tree, "")
    if not found:
        return {n: "" for n in hit}                     # named somewhere ModTrap does not know the meaning of
    if len(found) == len(hit):
        return dict(zip(hit, found))                    # one mention to a line, in the file's order
    worst = next(w for w in worst_first if w in found)
    return {n: worst for n in hit}


def read_mention(path: Path, mod_name: str, rel: str, plugin_names: list[str], installed: set[str] | None = None,
                 folder: bool = False) -> dict | None:
    """One settings file that names one of these plugins: the lines that do, and, where the file is of a kind
    ModTrap reads (`census.kind_of`, by its path inside the mod and the frameworks installed), where in the line
    (`where_named`). None when only lines that are switched off name one. A file that the scanner read and that
    cannot be opened now is given all the same, as one to look at. `folder`: it is a folder named after the
    plugin, where a framework reads that name (TL01§26). {"mod", "file", "names", "kind", "lines": [{"n", "text",
    "where"}], "count", "leaves_out", "unread", "path"}; a line's "n" is 0 where there is no line to point to."""
    lows = [n.lower() for n in plugin_names]
    kind = census.kind_of(rel + ("/config.json" if folder else ""), installed)
    label = kind["framework"] if kind else ""
    if folder:
        found = [n for n in plugin_names if n.lower() == path.name.lower()]
        if not found:
            return None
        where = "only with" if kind else ""
        return {"mod": mod_name, "file": rel + "/", "names": found, "kind": label, "count": 1, "leaves_out": 0, "unread": int(not kind),
                "lines": [{"n": 0, "text": "a folder named after the plugin: the animations in it are for one character of the plugin's",
                           "where": where}], "path": str(path)}
    try:
        with open(path, "rb") as f:
            raw = f.read(census.SETTINGS_BYTES)
    except OSError as e:
        log.warn("scanner: %s: %s named a ticked plugin when it was read, and cannot be opened now: %s", mod_name, rel, logbook.why(e))
        return {"mod": mod_name, "file": rel, "names": list(plugin_names), "kind": label, "count": 1, "leaves_out": 0, "unread": 1,
                "lines": [{"n": 0, "text": "the file could not be opened to read its lines (%s)" % logbook.why(e), "where": ""}],
                "path": str(path)}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    whole_low = text.lower()
    found = [plugin_names[i] for i, n in enumerate(lows) if n in whole_low]
    if not found:
        return None
    layout = str(kind.get("layout", "")) if kind else ""
    lines, count, leaves_out, unread = [], 0, 0, 0
    by_structure = _conditions_named(text, lows, path.name.lower().endswith(".json"), kind) if layout == "conditions" else None
    for n, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        hit = [p for p in lows if p in low]
        if not hit:
            continue
        if by_structure is not None:
            where = by_structure.get(n, "")
        else:
            wheres = {where_named(line, p, layout) for p in hit}
            where = next((w for w in ("leaves out", "", "only without", "gives", "reaches", "only with") if w in wheres), "comment")
        if where == "comment":
            continue                                    # a line that is switched off says nothing
        count += 1
        leaves_out += where == "leaves out"
        unread += where in ("", "may hold")
        if len(lines) < MENTION_LINES:
            lines.append({"n": n, "text": line.strip()[:MENTION_LINE], "where": where})
    if not count:
        return None                                     # named only in lines that are switched off
    return {"mod": mod_name, "file": rel, "names": found, "kind": label, "lines": lines,
            "count": count, "leaves_out": leaves_out, "unread": unread, "path": str(path)}


def mentions(inst: Instance, plugin_names: list[str], skip: set[str], scanned: dict | None = None) -> tuple[list[dict], bool]:
    """Settings files of other enabled mods that name one of these plugins: lines for a distributor or a patcher
    that runs in the game. Found by the scanner (`census.scan`, WHY§98): every settings file in force in the
    modlist, the winning one of each path, with no time limit. `scanned` is a scan already made; the second
    value says whether the look fell short of everything (`census.whole`)."""
    if scanned is None:
        scanned = census.scan(inst, census.known_plugins(inst) | set(plugin_names))
    wanted = {n.lower() for n in plugin_names}
    out: list[dict] = []
    for e in scanned["entries"]:
        if fold(e["mod"]) in skip or not (wanted & e["names"]):
            continue
        got = read_mention(e["path"], e["mod"], e["rel"], plugin_names, scanned.get("installed"), bool(e.get("folder")))
        if got is not None:
            out.append(got)
            log.info("scanner: %s: %s names %s: %d line(s)%s%s", e["mod"], got["file"], ", ".join(got["names"]), got["count"],
                     " (%s)" % got["kind"] if got["kind"] else " (a kind ModTrap does not read line by line)",
                     ", %d left to the owner" % (got["leaves_out"] + got["unread"]) if got["leaves_out"] + got["unread"] else ", none left to the owner")
    return out, not census.whole(scanned)


# --- compiling the steps ------------------------------------------------------------------------------------------

def compile_steps(m: model.Model, mod_names: list[str], job: dict | None = None, deep: dict | None = None,
                  auto: bool = False, going: bool = False, tools_run: dict | None = None, self_run: bool = True,
                  checked: dict | None = None, left: dict | None = None) -> dict:
    """The steps for taking `mod_names` out. `job` is the dry run's public state for the same mods, if there is
    one; `deep` is what `look_deeper` found (it takes seconds on a large list, so it is worked out once). `auto`
    says that ModTrap may change the modlist (it was started with the switch): the steps that "Demaster Selected"
    carries out are then ModTrap's, not the owner's (WHY§57). `tools_run` names the tools ModTrap has started, with
    their output written, since the demaster in place was put in place ({title: {"when", "files"}}): that record
    is what makes a tool's step done (WHY§91); None when ModTrap may not change anything, and so starts no tool.
    `self_run` is the owner's setting that lets ModTrap run a tool by itself where the tool allows it (WHY§97).
    `checked` is a finished tool check through xEdit for these mods (`toolcheck.read_result`, MT23): where it looked
    at a plugin that is still the same file, its verdict stands in place of the one from reading bytes. `left` names
    the tools whose step the owner chose to leave until the tool's next run ({tool: when}, MT24)."""
    inst = m.instance
    mods = [x for x in (inst.mod(n) for n in mod_names) if x is not None and x.kind == "mod"]
    trapped = sorted({p for x in mods for p in x.plugins}, key=fold)            # by file, enabled or not
    tf = {fold(p) for p in trapped}
    steps: list[dict] = []

    def step(key: str, who: str, title: str, why: str, state: str, items: list | None = None, note: str = "",
             action: str = "") -> None:
        steps.append({"key": key, "who": who, "title": title, "why": why, "state": state, "items": items or [],
                      "note": note, "n": len(steps) + 1, "action": action if state == "to do" else ""})

    doer = "ModTrap" if auto else "you"                 # for what "Demaster Selected" carries out
    press = "demaster" if auto and not going else ""

    # Who else provides a trapped plugin: the plugin stays in the game while any of them is enabled.
    twins = []
    for p in trapped:
        r = m.plugins.get(fold(p))
        holders = ([r.source] if r and r.source else []) + (list(r.also_in) if r else [])
        for h in holders:
            if h not in mod_names and h not in (GAME, OVERWRITE):
                twins.append({"plugin": p, "mod": h})

    # What still depends on a trapped plugin, as the modlist is now.
    remaining = [r for f in m.order for r in [m.plugins[f]] if r.source and fold(r.name) not in tf
                 and any(fold(x) in tf for x in r.masters)]
    active_left = [r for r in remaining if r.active]
    result = job.get("result") if job and job.get("state") == "done" else None
    same_job = bool(job and sorted(job.get("plan", {}).get("trapped_mods", [])) == sorted(x.name for x in mods))
    verdict = {}
    if result and same_job:
        verdict = {fold(f["name"]): f for f in result["files"]}

    binaries = {e.title: e.binary for e in inst.executables}
    made: dict[str, list] = {}                # plugin (folded) -> the evidence for who made it (TL01§7)

    def makers(r: model.PluginRow) -> list:
        if fold(r.name) not in made:
            made[fold(r.name)] = tools.identify(r.name, r.author, r.source or "", inst.output_mods, binaries)
        return made[fold(r.name)]

    def brief(r: model.PluginRow) -> dict:
        v = verdict.get(fold(r.name))
        return {"plugin": r.name, "mod": r.source, "position": r.position, "active": r.active,
                "verdict": v["reading"] if v else "", "own": v["own"] if v else None,
                "entries": v["entries"] if v else None, "needs_you": v["needs_you"] if v else None,
                "tool_title": next((t for t, mod in inst.output_mods.items() if mod == r.source and t in binaries), ""),
                "made_by": [e.tool + ("" if e.strong else " (probably)") for e in makers(r)],
                "how": "; ".join(e.how for e in makers(r))}

    # 1. The dry run.
    if not mods:
        return {"mods": [], "trapped": [], "steps": [], "complete": False, "summary": "Tick the mods to take out."}
    if result and same_job:
        dry_state, dry_note = "done", "Read %d dependant(s); nothing was changed." % len(result["files"])
    elif job and same_job and job.get("state") not in ("failed", "stopped", "done"):
        dry_state, dry_note = "going", "The dry run is going: see the Dry run tab."
    elif active_left:
        dry_state, dry_note = "to do", "Press “Dry run through xEdit” on the Selection tab."
    else:
        dry_state, dry_note = "not needed", "Nothing depends on these plugins any more."
    need_dry = dry_state in ("to do", "going")
    step("dry", "ModTrap", "Dry run: find out exactly what each dependant takes from the mod",
         "Until xEdit has read the dependants, ModTrap knows only which plugins list the mod as a master, not what "
         "they take from it. The dry run tells a patch made only for the mod from a plugin that must be demastered.",
         dry_state, note=dry_note, action=press if need_dry else "")
    if need_dry:
        # Nothing is foretold (WHY§86): what is to be done with each dependant, and which tools are to run again,
        # follows from what xEdit reads. Until then the steps say only that, and how many plugins are concerned.
        step("after-dry", "ModTrap", "The steps after the dry run",
             "What is to be done with each of the %d active plugin(s) that list the mod as a master, which tools are "
             "to run again and which are not, all follows from what the dry run reads in them. ModTrap states those "
             "steps once the dry run is done, from what it found; it does not guess them beforehand.%s" % (
                 len(active_left), " “Demaster Selected” makes the dry run itself, shows its plan and asks before it "
                                   "changes anything." if auto else ""),
             "waiting for the dry run", [brief(r) for r in active_left])
        if going:
            steps[0]["action"] = ""
        for s_ in steps:
            s_["manual"] = False
        return {"mods": [x.name for x in mods], "trapped": trapped, "steps": steps, "complete": False,
                "deep": bool(deep), "contents": {k: v["count"] for k, v in (deep or {}).get("kinds", {}).items()},
                "contents_cut": bool((deep or {}).get("cut")), "needs_dry": True,
                "summary": "A dry run comes first. The steps after it are stated once it is done."}

    # 2-4. The dependants, sorted by what is to be done with them: by the dry run's reading where there is one
    # (as "Demaster Selected" sorts them), else by what made them.
    def reading(r: model.PluginRow) -> str:
        return verdict.get(fold(r.name), {}).get("reading", "")

    patch_only = [r for r in active_left if reading(r) == "patch only"]
    can = [r for r in active_left if reading(r) == "can be demastered"]
    others = [r for r in active_left if r not in patch_only and r not in can]
    regen = [r for r in others if makers(r) and tools.proposal(makers(r)) != "demaster"]    # a tool makes it again
    needs = [r for r in others if r not in regen]
    to_demaster = can + needs
    known = bool(result and same_job) or not active_left      # the dry run has sorted the dependants, or none is left
    by_hand = [r for r in needs if reading(r) == "needs you"]

    step("switch-off", doer, "Switch off the patches made only for the mod",
         "A patch made for the mod (by its name and its few masters), or a plugin in which every record belongs to "
         "the mod, has no purpose without it. It is deactivated, and a mod that holds nothing but such patches is "
         "disabled whole; nothing in them is changed." + (
             " ModTrap does this when you press “Demaster Selected”." if auto else
             " Deactivate each on MO2's Plugins tab. (Started with --allow-changes, ModTrap does this itself.)"),
         "waiting for the dry run" if not known else "to do" if patch_only else "done",
         [brief(r) for r in patch_only],
         note="" if known else "The dry run shows which dependants are patches of this kind.", action=press)
    step("demaster", doer, "Demaster the plugins that must go on working without the mod",
         "Each of these needs the mod only in places: its copies of the mod's records, entries pointing at them, "
         "and parts it only carries on from the mod. The dry run lists exactly what would be taken out or put "
         "back." + (" ModTrap does this in the same “Demaster Selected”: it works on copies in a mod of its own, "
                    "checks each, and leaves the originals untouched." if auto else
                    " By hand these are the guide's Master Removal steps in xEdit, then Clean Masters. (Started "
                    "with --allow-changes, ModTrap does this itself.)"),
         "waiting for the dry run" if not known else "to do" if to_demaster else "done",
         [brief(r) for r in to_demaster],
         note=("%d of these need you: ModTrap leaves them as they are, and the mod then stays enabled until they "
               "no longer list it as a master. The Dry run tab shows what in them." % len(by_hand)) if by_hand else
         "Done when the plugin no longer lists the mod as a master (press Rescan to check).", action=press)
    if regen:
        items = [brief(r) for r in regen]
        step("regenerate", "both" if any(i["tool_title"] for i in items) else "you",
             "Run again the tools whose output depends on the mod",
             "These plugins were made by a tool, from the load order as it was. Once the mod and its patches are "
             "switched off, running the tool again rebuilds them without it. Do this after the steps above.",
             "to do", items,
             note="Done when the rebuilt plugin no longer lists the mod as a master.")

    # 5. The mods themselves, and what exists only for them.
    blockers = len(active_left)
    disable = [{"mod": x.name, "priority": x.priority, "enabled": x.enabled, "why": "ticked"} for x in mods]
    deep = deep or {}
    for rep in deep.get("replacements", []):
        mm = inst.mod(rep["mod"])
        disable.append({"mod": rep["mod"], "priority": rep["priority"], "enabled": bool(mm and mm.enabled),
                        "why": "%d of its %d files are files of a ticked mod: it only replaces them" % (rep["shared"], rep["files"])})
    for t in twins:
        mm = inst.mod(t["mod"])
        disable.append({"mod": t["mod"], "priority": mm.priority if mm else None, "enabled": bool(mm and mm.enabled),
                        "why": "it also provides %s" % t["plugin"]})
    all_off = all(not d["enabled"] for d in disable)
    step("disable", doer, "Disable the mod%s in MO2" % ("s" if len(disable) > 1 else ""),
         "Disabled, never removed: the mod stays in MO2's list and can be enabled again." + (
             " ModTrap does it at the end of “Demaster Selected”, once nothing active needs its plugins any more."
             if auto else " Do it only when nothing active needs its plugins any more, or MO2 will warn of missing "
             "masters."),
         "done" if all_off else "to do" if not blockers else "waiting",
         disable, note="" if not blockers or all_off else "%d active plugin(s) still list a ticked plugin as a master." % blockers)

    # 6. The tools: one verdict for each, from every kind of evidence there is (WHY§63, WHY§64). A tool is to
    # run again if any evidence says its output holds something of the mod; it needs no run if none does.
    known = {t["tool"]: t for t in tools.load()}
    verdict: dict[str, dict] = {}

    def entry(tool: str) -> dict:
        return verdict.setdefault(tool, {"run": [], "clear": [], "details": []})

    def titles_of(tool: str) -> list[str]:
        return [e.title for e in inst.executables if tools.of_executable(e.title, e.binary)[0] == tool]

    for kind, info in sorted(deep.get("kinds", {}).items()):          # (a) files of a kind that a tool feeds on
        if kind not in TOOLS_FOR:
            continue
        names = tools_for(inst, kind)
        if not names and kind == "animations" and deep.get("animation") is not None and not (
                deep["animation"]["lists"] or deep["animation"]["nemesis_engine"] or deep["animation"]["pandora_engine"]):
            continue                                   # plain animation files: nothing a behaviour tool reads
        if not names:
            step("tool:" + kind, "you", "Run the tool that handles %s again" % kind,
                 "The mod carries %d file(s) of %s (for example %s). A tool builds its output from all such files in "
                 "the modlist, and that output still has the mod's in it until the tool runs again. No tool of that "
                 "kind is set up in this MO2; if you use one outside MO2, run it." % (
                     info["count"], kind, ", ".join(info["examples"][:2])), "to do")
            continue
        feed = deep.get("animation") if kind == "animations" else None
        if feed is not None:
            # A behaviour tool reads lists and patch folders, not animation files (TL01§12, WHY§69).
            for title in names:
                tool = tools.of_executable(title, binaries.get(title, ""))[0]
                e = entry(tool)
                reads = ANIM_READS.get(tool, ("lists", "nemesis_engine", "pandora_engine"))
                # Pandora wants the graph file beside the list; the older engines make that file themselves.
                wants_graph = tool == "Pandora Behaviour Engine" and "lists_with_graph" in feed
                lists_read = feed["lists_with_graph"] if wants_graph else feed["lists"]
                passed_over = feed["lists_without_graph"] if wants_graph else []
                inputs = (lists_read if "lists" in reads else []) + [
                    "%s/mod/%s" % (eng, code) for eng in ("nemesis_engine", "pandora_engine") if eng in reads
                    for code in feed[eng]]
                named_in = [x for x in feed["searched"] if x["tool"] == tool]
                if passed_over and "lists" in reads:
                    e["clear"].append("the mod's %d animation list(s) have no graph file with them "
                                      "(FNIS_…_Behavior.hkx in the behaviour folder, in this mod or any enabled "
                                      "one), and this tool passes such a list over" % len(passed_over))
                    e["details"].append({"summary": "Animation list(s) without their graph file: %d" % len(passed_over),
                                         "lines": passed_over[:DETAILS]})
                if inputs:
                    e["run"].append("the mod carries %d animation list(s) or behaviour patch folder(s), which this "
                                    "tool reads and builds into its output; they stay in it until the tool runs "
                                    "again" % len(inputs))
                    e["details"].append({"summary": "What this tool reads of the mod: %d list(s) or patch folder(s)"
                                         % len(inputs), "lines": inputs[:DETAILS] + feed["graphs"][:4]})
                elif not passed_over:
                    e["clear"].append("the mod's %d animation file(s) are plain files: it has no animation list "
                                      "(FNIS_…_List.txt) and no behaviour patch folder (Nemesis_Engine or "
                                      "Pandora_Engine), which is all this tool reads of a mod" % info["count"])
                    e["details"].append({"summary": "The mod's %d file(s) of animations: none is a list or a patch "
                                         "folder" % info["count"], "lines": list(info["examples"])})
                for x in named_in:
                    if x["hit_count"]:
                        e["run"].append("%d file(s) of its output in “%s” name a folder of the mod's animations"
                                        % (x["hit_count"], x["mod"]))
                    elif feed["folders"] and x["files"] and not x["cut"]:
                        e["clear"].append("none of the %d file(s) read in its output “%s” names a folder of the "
                                          "mod's animations" % (x["files"], x["mod"]))
                    if feed["folders"]:
                        e["details"].append({
                            "summary": "Output “%s”: %d file(s) read for the names of the mod's animation folders "
                                       "(%s), %d naming one%s" % (x["mod"], x["files"], ", ".join(feed["folders"][:4]),
                                                                  x["hit_count"], "; not all could be read" if x["cut"] else ""),
                            "lines": ["%s names %s" % (h["file"], ", ".join(h["names"])) for h in x["hits"]]
                            or ["No file read there names one of them."]})
            continue
        for title in names:
            e = entry(tools.of_executable(title, binaries.get(title, ""))[0])
            e["run"].append("the mod carries %d file(s) of %s, which this tool builds its output from; the output "
                            "has them in it until the tool runs again" % (info["count"], kind))
            e["details"].append({"summary": "The mod's %d file(s) of %s" % (info["count"], kind),
                                 "lines": list(info["examples"]) + (
                                     ["… and %d more" % (info["count"] - len(info["examples"]))]
                                     if info["count"] > len(info["examples"]) else [])})
    for o in deep.get("outputs", []):                                  # (b) records in a plugin the tool made
        e = entry(o["tool"])
        if o.get("names_mod"):
            # A fact that needs no dry run and holds before the demaster as after it (WHY§86): the tool made this
            # plugin with the mod in the load order, and it names the mod as a master.
            e["run"].append("%s, which %s made, names %s as a master: it was made from the mod's own records. The "
                            "demaster takes those out of a copy to keep the load order whole; only the tool's own run "
                            "makes the plugin as it is without the mod" % (o["plugin"], o["tool"], ", ".join(o["names_mod"])))
            e["details"].append({"summary": "%s (%s) names the mod as a master" % (o["plugin"], o["how"]),
                                 "lines": ["Its masters include %s." % ", ".join(o["names_mod"])]})
            continue
        if not o.get("judged", True):
            e.setdefault("wait", []).append(o["plugin"])
            continue
        about = []                                      # what this plugin is, before what it holds of the mod
        mb = o.get("made_by")
        if mb:
            about.append("Made by the patchers of the group “%s”, in order: %s (from %s's own settings file)" % (
                mb["group"], ", ".join(p["name"] + ("" if p["on"] else " (switched off)") for p in mb["patchers"]) or "none listed",
                o["tool"]))
        if o.get("kinds"):
            about.append("Its %d record(s) by kind: %s%s" % (o["records"], " · ".join("%s %d" % (k, n) for k, n in o["kinds"]),
                                                             " · and %d more kind(s)" % o["kinds_more"] if o.get("kinds_more") else ""))
            about.append("The mod has a stake in records of kinds this plugin works on: %s" % ", ".join(
                "%s %d (this plugin holds %d of them)" % (k, n, h) for k, n, h in o["stake_kinds"])
                if o.get("stake_kinds") else "The mod has no stake in any kind of record this plugin holds.")
        if o["mod"].startswith("ModTrap - "):
            # It named the mod as a master: it held records of the mod's own. ModTrap's copy keeps the load order
            # whole until the tool's run, which writes the plugin anew in the copy's place (WHY§77, WHY§95).
            ran_since = o["tool"] in {tools.of_executable(t, binaries.get(t, ""))[0] for t in (tools_run or {})}
            if ran_since:
                e["run"].append("%s named the mod as a master, so it was made from the mod's own records. ModTrap took those "
                                "out of a copy to keep the load order whole, and the tool's run since has written the plugin "
                                "anew, in that copy's place in “%s” (MO2 writes to the file that wins)" % (o["plugin"], o["mod"]))
            else:
                e["run"].append("%s named the mod as a master, so it was made from the mod's own records. ModTrap took "
                                "those out of a copy, in “%s”, to keep the load order whole; the tool's run makes the plugin "
                                "anew without the mod, and writes it in that copy's place" % (o["plugin"], o["mod"]))
            e["details"].append({"summary": "%s in “%s”: %s" % (o["plugin"], o["mod"],
                                 "written anew by this tool's run since the demaster" if ran_since
                                 else "ModTrap's demastered copy of a plugin this tool made, until the tool runs"),
                                 "lines": about})
            continue
        if o.get("left_out"):
            # The framework was told to keep the mod's plugin out of this output: nothing of the mod went into it.
            e["clear"].append("%s was made with %s left out: the group “%s” has it in its own list of plugins to leave "
                              "out" % (o["plugin"], ", ".join(o["left_out"]), mb["group"] if mb else ""))
            e["details"].append({"summary": "%s (%s): the mod's plugin was left out when it was made" % (o["plugin"], o["how"]),
                                 "lines": about})
            continue
        # Checked through xEdit (MT23)? Then what xEdit found, by what the fields mean, is the verdict for this
        # plugin, as long as the plugin is still the file that was checked.
        xe = (checked or {}).get("files", {}).get(fold(o["plugin"]))
        if xe is not None:
            row_now = m.plugins.get(fold(o["plugin"]))
            try:
                st_now = os.stat(row_now.path) if row_now is not None and row_now.path is not None else None
            except OSError:
                st_now = None
            if st_now is None or [st_now.st_size, st_now.st_mtime_ns] != list(xe.get("stamp", [])):
                xe = None                               # written anew since (the tool ran): that check is of another file
        if xe is not None:
            e["checked"] = e.get("checked", 0) + 1
            mine = xe["held"] - xe["last_else"]
            xlines = ["%s %s of %s · %s has the last word, next in line is %s · as the mod: %s · of its own: %s · as the next in line: %s" % (
                r_["kind"], r_["form"], r_["owner"], r_["by"], r_["next_by"] or "no other plugin", ", ".join(r_["mod"][:8]) or "nothing",
                ", ".join(r_["own"][:8]) or "nothing", ", ".join(r_["next"][:8]) or "nothing") for r_ in xe["rows"][:DETAILS]]
            if xe.get("rows_more") or len(xe["rows"]) > DETAILS:
                xlines.append("… and %d more record(s)" % (xe.get("rows_more", 0) + max(0, len(xe["rows"]) - DETAILS)))
            xlines += ["    %s %s (%s) · this plugin: %s · the mod: %s · next in line: %s" % (
                v["form"], v["part"], "the mod's value" if v["what"] == "mod" else "a value of its own", v["tool"], v["mod"], v["next"])
                for v in xe["values"][:2 * DETAILS]]
            if xe["verdict"] == "mod":
                e["run"].append("%s holds, in %d record(s), what the mod says where the next in line says something else: "
                                "xEdit compared them by what the fields mean, so it has that from the mod" % (o["plugin"], xe["mod"]))
                e.setdefault("values", []).extend(dict(v, plugin=o["plugin"]) for v in xe["values"] if v["what"] == "mod")
            elif xe["verdict"] == "own":
                e["run"].append("%s holds %d record(s) on which the mod has the last word with a value that is neither the mod's "
                                "nor the next in line's (xEdit compared them by what the fields mean). The tool worked that value "
                                "out, and nothing shows from which of the two" % (o["plugin"], xe["own"]))
                e["unsure"] = e.get("unsure", 0) + 1
            else:
                e["clear"].append("%s, compared through xEdit by what the fields mean: %s" % (o["plugin"], (
                    "it holds no record on which the mod has the last word" if not mine else
                    "in each of the %d record(s) on which the mod has the last word it says what the next in line says, or the two say the same" % mine)))
            e["details"].append({"summary": "%s (%s), checked through xEdit (%s): of %d record(s) the mod's plugins hold too, the mod has "
                                            "the last word on %d; %d with the mod's value, %d with a value of the tool's own" % (
                                     o["plugin"], o["how"], (checked or {}).get("when", "").replace("T", " "), xe["held"], mine, xe["mod"], xe["own"]),
                                 "lines": about + (xlines or ["No record of it holds anything to tell the mod's version from the next in line's."])})
            continue
        if o["shared"] or o["cut"]:
            e["by_bytes"] = e.get("by_bytes", 0) + 1         # judged by reading bytes: xEdit could say more (MT23)
        lines = ["%s %s of %s · %s has a stake in %s · %s" % (
            d["kind"], d["id"], d["owner"], ", ".join(d["by"]), ", ".join(d["changed"][:8]),
            ("this plugin holds the same " + ", ".join(d["carried"][:8])) if d["carried"]
            else "this plugin holds none of it") for d in o["details"]]
        lines += ["    %s · the mod: %s · this plugin: %s · next in line (%s): %s" % (x["field"], x["mod"], x["tool"], x["next_by"], x["next"])
                  for d in o["details"] for x in d.get("values", [])]
        lines += ["%s %s of %s · no stake of the mod's after all: %s" % (x["kind"], x["id"], x["owner"], x["why"])
                  for x in o.get("no_stake", [])]
        if o["carried"]:
            e["run"].append("%s holds, in %d record(s), a value it has from the mod: without the mod the load order "
                            "says something else there" % (o["plugin"], o["carried"]))
        elif o["cut"]:
            e["run"].append("%s could not be read to the end in the time ModTrap allows itself, so ModTrap cannot "
                            "say that nothing of the mod is in it" % o["plugin"])
        elif o["shared"] and known.get(o["tool"], {}).get("kind") == "patcher" \
                and known.get(o["tool"], {}).get("writes") == "own":
            # A patcher works its values out from the versions that win, and this one writes records in a form of
            # its own: neither "the same bytes" nor "other bytes" says where a value came from (WHY§73).
            e["run"].append("%s holds %d record(s) in which the mod has a stake. A patcher builds its copy of a "
                            "record from the version that wins, and %s writes records in its own form, so reading "
                            "them cannot show whether a value in them comes from the mod. ModTrap cannot rule it "
                            "out" % (o["plugin"], o["shared"], o["tool"]))
            e["unsure"] = e.get("unsure", 0) + 1
        elif o["shared"]:
            e["clear"].append("%s holds %d record(s) in which the mod has a stake, but none of the mod's values in "
                              "them" % (o["plugin"], o["shared"]))
        else:
            e["clear"].append("%s holds no record in which the mod has a stake" % o["plugin"])
        e["details"].append({"summary": "%s (%s): %d record(s) in which the mod has a stake, %d with the mod's "
                                        "value in them" % (o["plugin"], o["how"], o["shared"], o["carried"]),
            "lines": about + (lines or ["Of its %d record(s), none is one in which the mod or its patches have a stake."
                                        % o["records"]])})
    for x in deep.get("tool_settings", []):                            # (b2) a patcher's own settings name the plugin
        e = entry(x["tool"])
        e["run"].append("a settings file of one of its patchers names the mod's plugin (%s): that patcher was set up "
                        "with the mod in mind" % x["file"])
        e["details"].append({"summary": "Settings of %s's patchers that name the mod's plugin" % x["tool"],
                             "lines": ["%s names %s" % (x["file"], ", ".join(x["names"]))]})
    for o in deep.get("output_files", []):                             # (c) files in the tool's output mod
        e = entry(o["tool"])
        if o["shared"]:
            e["run"].append("its output mod “%s” holds %d file(s) at the path of a file of the mod: made from the "
                            "mod's files" % (o["mod"], o["shared"]))
        else:
            e["clear"].append("none of the %d file(s)%s in its output mod “%s” lies at the path of a file of the mod" % (
                o["files"], " that could be listed" if o["cut"] else "", o["mod"]))
        e["details"].append({"summary": "Output mod “%s”: %d file(s), %d at a path of the mod" % (
            o["mod"], o["files"], o["shared"]), "lines": o["examples"] or ["No file there lies at the path of one of the mod's files."]})

    st = deep.get("stakes")
    stake_note = "" if not st else (
        " By xEdit's dry run, the mod and the patches made for it change %d record(s) of other plugins and have a "
        "stake in %d: records where their version wins and the next in line says something else, or where they "
        "say what no plugin that stays says. Only those can leave a mark in what a tool made."
        % (st["changed"], st["stake"]))
    clear_items: list[dict] = []
    wait_items: list[dict] = []
    seen_by_run: set[str] = set()          # tool steps whose state is a record of ModTrap's, not a tick of the owner's
    for tool in sorted(verdict, key=fold):
        e = verdict[tool]
        names = titles_of(tool)
        does = known.get(tool, {}).get("does", "")
        evidence = [{"details": d} for d in e["details"]]
        if e.get("wait") and not e["run"]:
            # Its plugins could carry something of the mod, and only the dry run can say what the mod changes.
            wait_items.append({"text": "%s: %s %s built from the whole load order and %s not name the mod as a master.%s" % (
                tool, ", ".join(e["wait"]), "was" if len(e["wait"]) == 1 else "were",
                "does" if len(e["wait"]) == 1 else "do", (" " + does) if does else ""), "evidence": e["details"]})
            continue
        if e["run"]:
            also = (" What speaks against it: " + "; ".join(e["clear"]) + ".") if e["clear"] else ""
            when = known.get(tool, {}).get("reads_if", "")
            # Proof, or only "cannot be ruled out"? The title says which (WHY§73).
            to_be_sure = bool(e.get("unsure")) and e["unsure"] == len(e["run"])
            ran = [(n, tools_run[n]) for n in names if n in (tools_run or {})]
            # Who does it, as it is (WHY§97): ModTrap alone where it runs the tool by the tool's own switches or
            # button; ModTrap and the owner where it can only start it; the owner where it is not in MO2's list.
            by_modtrap = bool(names) and tools_run is not None and self_run and isinstance(known.get(tool, {}).get("self_run"), dict)
            is_left = tool in (left or {}) and not ran
            step("tool:" + tool, "ModTrap" if by_modtrap else "both" if names else "you", "Run %s again%s" % (tool, ", to be sure" if to_be_sure else ""),
                 (does + " " if does else "") + "Why for this mod: " + "; ".join(e["run"]) + "." + also + (
                     " A run of a patcher is short and changes nothing but its own output: when in doubt, run it."
                     if to_be_sure else "") + (
                     " A new run matters " + when + "; the evidence below shows which records these are."
                     if when else ""),
                 "done" if ran else "not needed" if is_left else "to do", [{"tool": n} for n in names] + evidence,
                 note=("It ran after this demaster was put in place: “%s”, %s, %d file(s) of its output written." % (
                           ran[0][0], ran[0][1].get("when", "").replace("T", " "), ran[0][1].get("files", 0))) if ran else
                 ("Left by you (%s) until the tool's next run: what it made keeps what it has from the mod until then. The game "
                  "loads it as it is; ModTrap does not run the tool for this. Take that back to have it run." % (left or {})[tool].replace("T", " "))
                 if is_left else
                 ("ModTrap runs it by itself after the demaster (%s), and the step is done when it has written its "
                  "output. A Revert, or a new demaster, asks for a new run." % (
                      "by pressing its own run button and closing it when its log says the run is over"
                      if isinstance(known[tool]["self_run"].get("press"), dict) else "by the tool's own switches to run and close")
                  if by_modtrap else
                  "ModTrap starts it through MO2; running it and closing it is yours. The step is done when it has written "
                  "its output after the demaster was put in place. A Revert, or a new demaster, asks for a new run."
                  if names and tools_run is not None else
                  "Run it after the demaster. ModTrap was started without --allow-changes and starts no tool: tick it "
                  "off when you have run it." if names else
                  "It is not in this MO2's list of tools; run it the way the modlist's own guide says, and tick it off."))
            if names and tools_run is not None:
                seen_by_run.add("tool:" + tool)
            # For the page (MT23, MT24): the tool's name, whether the owner left it, the values it holds of the mod as
            # xEdit told them, and whether a check through xEdit could say more than reading bytes did.
            mods_in = all(x.enabled for x in mods)
            steps[-1].update(tool=tool, left=is_left, leave=not ran,
                             values=[{k: v[k] for k in ("plugin", "form", "part", "tool", "mod", "next")} for v in e.get("values", [])[:12]],
                             check=("" if ran else "offer" if e.get("by_bytes") and mods_in else "needs the mod" if e.get("by_bytes")
                                    else "done" if e.get("checked") else ""))
        else:
            clear_items.append({"text": "%s: %s.%s" % (tool, "; ".join(e["clear"]), (" (" + does + ")") if does else ""),
                                "evidence": e["details"]})
    if wait_items:
        mod_off = all(not x.enabled for x in mods)
        step("tools-wait", "ModTrap", "Tools ModTrap can judge only from a dry run",
             "Whether such a tool's plugin carries anything of the mod depends on which records the mod really "
             "changes. Only xEdit can tell that (a name kept as text or in a strings file, a list saved in another "
             "order and the like look like changes to anything that only reads the bytes), and it tells it in the "
             "dry run. " + ("The mod is disabled now, so no dry run can be made of it: to have these tools judged, "
                            "Revert the demaster and press “Demaster Selected” again; or go by the modlist's own "
                            "guide for this mod." if mod_off else
                            "No dry run made with this version of ModTrap is at hand for this mod: press “Dry run "
                            "through xEdit”, or “Demaster Selected”, which makes one."),
             "not needed" if mod_off else "waiting for the dry run", wait_items)
    if clear_items:
        step("tools-clear", "ModTrap", "Tools that need no new run for this mod",
             "ModTrap looked at what each of these tools made and found nothing of the mod in it: no file the tool "
             "feeds on, no record with a value only the mod supplies, no file made from the mod's. Each tool has "
             "one verdict: it is either here or among the steps above, never both. This is evidence, not proof: "
             "what a tool would make without the mod is only known for certain by running it; a tool that left "
             "something out because of the mod leaves no trace to find." + stake_note, "not needed", clear_items)

    # 7. Settings files of other mods that name a ticked plugin: read by ModTrap, line by line (WHY§95). The step is
    # the owner's only where a line leaves the mod's things out, or the file is of a kind ModTrap does not read.
    named = deep.get("mentions", [])
    mentions_by_modtrap = False
    scan = deep.get("scan")
    looked, short = "", ""
    if scan:
        looked = ("ModTrap's scanner looked through every settings file in force in the modlist: %s file(s) in the game's "
                  "folder, the %s enabled mod(s) and Overwrite, the folders of animation replacers among them, the winning "
                  "copy of each as the game sees it%s. " % (
                      format(scan["files"], ","), format(max(0, scan["mods"] - 2), ","),
                      ", not counting %s hidden by a mod of higher priority" % format(scan["hidden"], ",") if scan["hidden"] else ""))
        missed = ([("the scanner itself failed (%s) and looked through nothing" % scan["failed"])] if scan.get("failed") else []) \
            + ([("%d folder(s) could not be listed to the end (%s)" % (scan["cut"], "; ".join(scan["cut_mods"])))] if scan["cut_mods"] else []) \
            + ([("%d file(s) could not be opened (%s)" % (scan["unreadable"], "; ".join(scan["unreadable_examples"])))] if scan["unreadable"] else []) \
            + ([("%d file(s) are too large to be a settings file and were not read (%s)" % (scan["too_large"], "; ".join(scan["too_large_examples"])))] if scan["too_large"] else [])
        short = (" Not reached by the scanner: " + "; ".join(missed) + ". Whether one of these names the plugin is not known.") if missed else ""
    if scan and not named:
        if short:
            step("mentions", "you", "Look at what the scanner could not read",
                 looked + "None of those it read names a ticked plugin." + short + " Open what is named there, or let "
                 "ModTrap read it again once it can be opened (Rescan).", "to do",
                 note="A judgement, not a fault: tick it off when you have looked.")
        else:
            mentions_by_modtrap = True
            step("mentions", "ModTrap", "Settings files of other mods: none names the mod's plugin",
                 looked + "Each was read to its end. None names a ticked plugin, so no distributor or patcher that works "
                 "while the game runs has a line about the mod.", "done")
    if named:
        WHERE = {"gives": "what the line gives or changes comes from the mod: without the mod it has nothing to give",
                 "reaches": "the mod's things are a condition for what the line reaches: without the mod it reaches nothing of them, and nothing else changes",
                 "only with": "the line is carried out only while the mod's plugin is active: without the mod it is passed over",
                 "only without": "the line was written for a modlist without the mod: it was held back while the mod was there, and is carried out now, as its author meant",
                 "condition": "a condition about one of the mod's things, for when an animation is used: without the mod the thing is not there, so the condition does not hold (or, where it is turned round, always holds), as for anyone who never had it",
                 "may hold": "a condition about one of the mod's things that can hold once the thing is gone, so the animation it is for may be used where it was not meant",
                 "leaves out": "the line leaves the mod's things out of something meant for everything else",
                 "": "ModTrap has not read how this kind of file is used"}
        TODO = {"leaves out": "Open the file in a text editor and go to this line. The part that begins with - and names the "
                              "plugin is the exclusion. To be sure the line goes on working for everything else, take that part "
                              "out (and the comma or + beside it); if you would rather not change the file, leave it and look "
                              "in the framework's own log after starting the game: it says whether it passed the line over.",
                "may hold": "Open the file in a text editor and go to this line: it belongs to a condition about a scene or an "
                            "enchantment of the mod you took out. If the animations of that folder were only for the mod, "
                            "switch the folder's entry off in the animation replacer's own menu in the game, or disable the "
                            "mod the file belongs to; if they are for more than the mod, take the condition out of the file.",
                "": "Open the file in a text editor and go to this line. See what the line is for, by the page of the mod "
                    "the file belongs to; a line that only does something for the mod you took out can stay as it is."}

        def said(x: dict) -> dict:
            lines = x.get("lines") or []
            open_lines = x.get("leaves_out", 0) + x.get("unread", 0)
            return {"mod": x["mod"], "file": x["file"], "names": x["names"], "kind": x.get("kind", ""),
                    "count": x.get("count", len(lines)), "open": open_lines, "path": x.get("path", "") if open_lines else "",
                    "verdict": ("%d line(s) to look at" % open_lines) if open_lines else "nothing to do",
                    # What is left to the owner is said in full, not folded away: the line, what it means, what to do.
                    "look": [{"n": ln["n"], "text": ln["text"], "means": WHERE.get(ln["where"], ln["where"]),
                              "todo": TODO.get(ln["where"], "")} for ln in lines if ln["where"] in ("leaves out", "", "may hold")],
                    "evidence": {"summary": "%s: %d line(s) name the plugin%s" % (
                        x["file"], x.get("count", len(lines)), (" (" + x["kind"] + ")") if x.get("kind") else ""),
                        "lines": [("line %d · " % ln["n"] if ln["n"] else "") + "%s · %s" % (WHERE.get(ln["where"], ln["where"]), ln["text"]) for ln in lines]
                        + (["… and %d more line(s)" % (x["count"] - len(lines))] if x.get("count", 0) > len(lines) else [])}}

        items = sorted((said(x) for x in named), key=lambda i: (not i["open"], fold(i["mod"]), fold(i["file"])))
        to_look = [i for i in items if i["open"]]
        cut_note = short or (" The search was cut short; there may be more files." if deep.get("mentions_cut") else "")
        if to_look or deep.get("mentions_cut"):
            step("mentions", "you", "Look at %d settings file(s) with lines only you can judge" % len(to_look) if to_look else
                 "Look at the settings files that name the mod's plugin",
                 looked + "It read every one that names a ticked plugin, line by line. Where a line "
                 "gives something of the mod's, reaches only the mod's things, or is written to depend on the mod being "
                 "there or not, the framework it is written for deals with it by itself once the mod is gone. Left to "
                 "you are only the lines named below, each with its file, its line number and what to do: lines that "
                 "leave the mod's things out of something meant for everything else (what the framework does with such "
                 "a line once the mod is gone depends on its version: it may go on without the exclusion, or drop the "
                 "whole line), and files of a kind ModTrap has not read the use of.",
                 "to do", items, note="A judgement, not a fault: tick it off when you have looked." + cut_note)
        else:
            mentions_by_modtrap = True
            step("mentions", "ModTrap", "Settings files that name the mod's plugin: read, nothing to do",
                 looked + "It read every one that names a ticked plugin, line by line: %d line(s) "
                 "in %d file(s). Each gives something of the mod's, reaches only the mod's things, or is written to "
                 "depend on the mod being there or not. The frameworks these files are written for deal with such a "
                 "line by themselves once the mod is gone (they note it in their own log), and nothing else they do "
                 "changes. The evidence under each file says which line is which." % (sum(i["count"] for i in items), len(items)),
                 "done", items)

    # 8. The health check, and playing.
    missing = [i for i in m.issues if fold(i.master) in tf]
    other = len(m.issues) - len(missing)
    step("health", "ModTrap", "Check the load order: no missing or inactive masters",
         "The same check as MO2's warning triangle, done on the modlist as it is on disk now.",
         "done" if all_off and not m.issues else "waiting" if not all_off else "to do",
         [{"plugin": i.plugin, "master": i.master, "what": i.what} for i in m.issues[:50]],
         note=("%d problem(s) were there before and have nothing to do with these mods." % other) if other else "")
    scripts = deep.get("kinds", {}).get("scripts")
    step("play", "you", "Start the game and look for anything odd",
         "What no file can show: whether the game plays well. " + (
             "This mod carries %d compiled script(s): a save made while it was enabled can keep traces of them. "
             "A new game is the clean way; on an existing save, expect oddities from that, not from the demaster. "
             % scripts["count"] if scripts else "") + "If something is off, the Log tab's lines help to find out why.",
         "to do" if all_off else "waiting")
    if going:                                           # a demaster is in hand: its steps say so (WHY§61)
        for st in steps:
            if st["key"] in ("switch-off", "demaster", "disable") and st["state"] in ("to do", "waiting"):
                st["state"], st["action"] = "going", ""
    # Ticked off by the owner: only what no record can show. A tool ModTrap starts is not among them (WHY§91).
    manual = ({"play"} | (set() if mentions_by_modtrap else {"mentions"})
              | {s["key"] for s in steps if s["key"].startswith("tool:") and s["key"] not in seen_by_run})
    for s in steps:
        s["manual"] = s["key"] in manual
    open_steps = [s for s in steps if s["state"] not in ("done", "not needed") and not s["manual"]]
    # The checks after the demaster, as one account (WHY§95): each a fact ModTrap read or recorded, none a tick.
    checks = []
    by_key = {s["key"]: s for s in steps}
    if "health" in by_key:
        checks.append({"text": "The load order has no missing or inactive master", "ok": by_key["health"]["state"] == "done"})
    if "disable" in by_key:
        checks.append({"text": "The mod%s disabled, with the patches made only for it" % (" is" if len(mods) == 1 else "s are"),
                       "ok": by_key["disable"]["state"] == "done"})
    for st in steps:
        if st["key"].startswith("tool:") and not st["manual"]:
            checks.append({"text": st["title"].replace("Run ", "", 1).replace(" again", "").replace(", to be sure", "")
                           + " has had its run since the demaster, and wrote its output", "ok": st["state"] == "done"})
    if "mentions" in by_key and not by_key["mentions"]["manual"]:
        checks.append({"text": ("Every settings file in force in the modlist was looked through (%s): " % format(scan["files"], ",") if scan else "")
                       + ("the ones that name the mod's plugin were read line by line, and nothing in them is left to do" if named else
                          "none names the mod's plugin"), "ok": True})
    left_to_owner = [s["title"] for s in steps if s["manual"] and s["state"] not in ("done", "not needed")]
    return {"mods": [x.name for x in mods], "trapped": trapped, "steps": steps, "complete": not open_steps,
            "checks": checks, "checked": bool(checks) and all(c["ok"] for c in checks) and not open_steps,
            "left_to_owner": left_to_owner,
            "deep": bool(deep), "contents": {k: v["count"] for k, v in deep.get("kinds", {}).items()},
            "contents_cut": bool(deep.get("cut")),
            "summary": ("Every step that files can prove is done." if not open_steps else
                        "%d step(s) to go." % len(open_steps))}


def look_deeper(m: model.Model, mod_names: list[str], touched: dict | None = None) -> dict:
    """The part of the steps that reads folders: what the ticked mods carry, which mods only replace their files,
    and which settings files name their plugins. Seconds on a large list."""
    inst = m.instance
    mods = [x for x in (inst.mod(n) for n in mod_names) if x is not None and x.kind == "mod" and x.folder is not None]
    kinds: dict[str, dict] = {}
    reps: list[dict] = []
    cut = False
    paths_all: set[str] = set()
    for x in mods:
        c = contents(x.folder)
        paths_all |= c["paths"]
        cut = cut or c["cut"]
        for k, v in c["kinds"].items():
            e = kinds.setdefault(k, {"count": 0, "examples": []})
            e["count"] += v["count"]
            e["examples"] = (e["examples"] + v["examples"])[:3]
        reps += [r for r in replacements(inst, x, c["paths"]) if r["mod"] not in mod_names
                 and r["mod"] not in [q["mod"] for q in reps]]
    trapped = sorted({p for x in mods for p in x.plugins}, key=fold)
    skip = {fold(x.name) for x in mods} | {fold(r["mod"]) for r in reps}
    try:
        scanned = census.scan(inst, census.known_plugins(inst) | set(trapped))
    except Exception as e:                              # whatever it is: said, and never taken for "nothing found"
        log.error("the scanner failed and looked through nothing: %s", logbook.why(e))
        scanned = census.failed(logbook.why(e))
    named, mcut = mentions(inst, trapped, skip, scanned) if trapped else ([], False)
    counts = (touched or {}).get("")               # how many records each looked-through plugin changes at all
    told = {k: v for k, v in (touched or {}).items() if k} if touched is not None else None
    outputs, output_files = tool_outputs(m, mods, trapped, paths_all, told)
    out = {"kinds": kinds, "replacements": reps, "mentions": named, "mentions_cut": mcut, "cut": cut,
           "outputs": outputs, "output_files": output_files, "scan": census.public(scanned)}
    log.info("scanner: %d file(s) or folder(s) of other mods name a ticked plugin (%s)", len(named), ", ".join(trapped) or "none ticked")
    if "animations" in kinds:
        out["animation"] = animation_feed(inst, paths_all, {fold(x.name) for x in mods})
    named_by = toolmade.named_in_settings(toolmade.tool_folders(inst, "Synthesis"), trapped) if trapped else []
    if named_by:
        out["tool_settings"] = [{"tool": "Synthesis", **x} for x in named_by]
    if told is not None and isinstance(counts, dict):
        out["stakes"] = {"changed": sum(int(v) for v in counts.values()), "stake": sum(len(v) for v in told.values()),
                         "plugins": len(told)}
    return out


def show_field(ftype: str, data: bytes) -> str:
    """A short field in words or bytes, for the evidence: what the mod, the tool's plugin and the plugin next in
    line each say. Only what is needed to judge; a long field is told by its length."""
    if ftype == "XCLC" and len(data) in (8, 12):
        x, y = int.from_bytes(data[0:4], "little", signed=True), int.from_bytes(data[4:8], "little", signed=True)
        return "cell (%d, %d), land flags %s" % (x, y, "0x%02X" % data[8] if len(data) == 12 else "none")
    if not data:
        return "nothing"
    if len(data) <= 16:
        return " ".join("%02X" % c for c in data)
    return "%d bytes" % len(data)


WHOLE_ORDER_SECONDS = 60.0     # looking through the whole load order for a few records, at most


def _whole_order(m: model.Model, wanted: dict, gone: set[str], made: set[str], held, until: float) -> tuple[dict, bool]:
    """For a few records, in the whole load order (not only what xEdit loaded): does a leaving plugin have the last
    word among the plugins no tool made, and in which of the fields named does the plugin next in line (the last
    one that stays) say the same as the leaving plugin? {key: {"wins", "by", "same": set of field types}}, and
    whether the look was cut short. A record no staying plugin holds counts as won by the mod, with nothing the
    same."""
    kinds = frozenset(ch["kind"] for ch in wanted.values() if ch.get("kind"))
    owners = {k[0] for k in wanted}
    place = {f: i for i, f in enumerate(m.order)}
    last_gone = {k: max((place.get(fold(n), -1) for n in ch["by"]), default=-1) for k, ch in wanted.items()}
    out = {k: {"wins": True, "by": "", "same": set(), "at": -1, "next": {}} for k in wanted}
    cut = False
    for f in m.order:
        r = m.plugins[f]
        if not r.active or r.path is None or f in gone or f in made:
            continue
        if fold(r.name) not in owners and not any(fold(x) in owners for x in r.masters):
            continue                                     # it cannot hold a record of those plugins
        left = until - time.monotonic()
        if left <= 0:
            cut = True
            break
        try:
            with plugin.Records(r.path, min(left, OUTPUT_FILE_SECONDS), kinds or None) as there:
                cut = cut or there.cut
                for key in there.index.keys() & wanted.keys():
                    theirs = there.fields(key) or []
                    # Every field xEdit named, not only those that differ from the mod's own master by bytes: a
                    # field can differ from that master in nothing that counts and still be told (WHY§78).
                    mine = wanted[key].get("all") or wanted[key]["fields"]
                    out[key].update(by=r.name, at=place[f],
                                    same={t for (t, b, src) in mine if held((t, b), src, theirs, there)},
                                    next={t: b for t, b in theirs if any(t == x[0] for x in mine)})
        except (plugin.Unreadable, OSError):
            cut = True
    for key, v in out.items():
        v["wins"] = v["at"] < last_gone[key]
        if not v["wins"]:
            v["same"] = set()
    return out, cut


OUTPUT_SECONDS = 60.0          # all the reading of plugins for one look at the tools, at most
OUTPUT_FILE_SECONDS = 12.0     # and of one plugin
DETAILS = 40                   # records named in one plugin's evidence, at most


def tool_outputs(m: model.Model, mods: list[Mod], trapped: list[str], paths_low: set[str],
                 touched: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Which tools' outputs carry something of the mods being taken out, by evidence (WHY§63 to WHY§66).

    A patcher builds its plugin from the whole load order. Its output need not name the mod as a master to carry
    what the mod did: it may have copied a value from the mod's version of a record. Holding the same record is
    not enough to say so: a mod often holds a record it does not change (a cell it only puts things into), and
    how a plugin writes a record says little about what it means (a name kept as text or in a strings file, a
    list saved in another order, a pointer numbered by the plugin's own masters). So:

    1. What the mod changes is not judged here. xEdit, which knows what every field means, tells it in the dry
       run (`touched`, XE01§18): for each plugin of the mod, and each patch made for it, the records it really
       changes and the fields that differ from what its author had before them. Without a dry run that told
       this, no tool is judged by records: each such plugin is returned as not judged.
    2. What a tool's plugin carries. For each plugin a tool made that does not depend on the mod, and each record
       it holds that the mod changes: does it hold one of the changed fields as the mod wrote it, and not as the
       plugin's last master had it? Then it carries the mod's change, and the tool is to run again. Read with
       ModTrap's own reader, each plugin's numbering of its masters in mind (plugin.same_field).

    A generator that works on files is judged by files: how many files of its output mod lie at the path of one
    of the mod's own loose files."""
    inst = m.instance
    tf = {fold(p) for p in trapped}
    names = [x.name for x in mods]
    binaries = {e.title: e.binary for e in inst.executables}
    data = {t["tool"]: t for t in tools.load()}
    until = time.monotonic() + OUTPUT_SECONDS
    opened: dict[str, plugin.Records | None] = {}

    def records_of(path: Path | None) -> plugin.Records | None:
        if path is None:
            return None
        key = str(path)
        if key not in opened:
            left = until - time.monotonic()
            try:
                opened[key] = plugin.Records(path, min(left, OUTPUT_FILE_SECONDS)) if left > 0 else None
            except (plugin.Unreadable, OSError):
                opened[key] = None
        return opened[key]

    def path_of(plugin_name: str) -> Path | None:
        r = m.plugins.get(fold(plugin_name))
        if r is not None and r.path is not None:
            return r.path
        for x in inst.mods:                               # a plugin of a disabled mod: where its mod keeps it
            if x.folder is not None and any(fold(p) == fold(plugin_name) for p in x.plugins) \
                    and (x.folder / plugin_name).is_file():
                return x.folder / plugin_name
        return None

    def held(field: tuple[str, bytes], src: plugin.Records, others: list[tuple[str, bytes]], there: plugin.Records) -> bool:
        """Is this field, as `src` wrote it, among `others`, as `there` wrote them? (plugin.same_field, WHY§65)"""
        return any(t == field[0] and plugin.same_field(plugin.canonical(t, field[1]), src, plugin.canonical(t, b), there)
                   for t, b in others)

    # 1. What the mods' plugins, and the patches made for them, change: as xEdit told it in the dry run.
    # record -> {"by", "kind", "fields": [(type, bytes, the plugin that wrote them so)], "named": the fields' types}
    changes: dict[tuple[str, int], dict] = {}
    judged = touched is not None and any(fold(k) in tf for k in touched)
    unsure = False
    try:
        for name, rows in (touched or {}).items() if judged else ():
            src = records_of(path_of(name))
            if src is None:
                unsure = True
                continue
            unsure = unsure or src.cut
            masters = [x for x in src.masters if x not in tf]
            for row in rows:
                try:
                    form = int(row["form"], 16)
                except (KeyError, ValueError):
                    continue
                key = (fold(row["owner"]), form & 0xFFF if form >> 24 == 0xFE else form & 0xFFFFFF)
                mine = src.fields(key)
                if mine is None:
                    continue
                wanted = set(row.get("fields", []))
                before, base = [], None
                for master in reversed(masters):          # what the author had before them, to leave untouched
                    base = records_of(path_of(master))    # fields of a changed list out
                    if base is not None and key in base.index:
                        before = base.fields(key) or []
                        break
                changed = [fd for fd in mine if fd[0] in wanted and (base is None or not held(fd, src, before, base))]
                entry = changes.setdefault(key, {"by": [], "kind": row.get("kind", ""), "fields": [], "named": set()})
                entry["by"].append(name)
                entry["fields"] += [(t, b, src) for t, b in changed]
                entry.setdefault("all", []).extend((t, b, src) for t, b in mine if t in wanted)
                entry["named"] |= wanted

        # 2. What each tool-made plugin carries of that. With it: what kinds of record the plugin holds at all, and
        # for the patcher framework which patchers made it and which plugins it was told to leave out (WHY§74).
        outputs = []
        tool_plugins = []
        naming = outputs            # tool-made plugins that name the mod as a master come first, said as they are (WHY§86)
        for f in m.order:
            r = m.plugins[f]
            if not r.active or r.source is None or r.path is None or fold(r.name) in tf:
                continue
            ev = [e for e in tools.identify(r.name, r.author, r.source, inst.output_mods, binaries) if e.kind != "editor"]
            if not ev or "plugins" not in data.get(ev[0].tool, {}).get("reads", ["plugins"]):
                continue
            if any(fold(x) in tf for x in r.masters):   # a dependant: the demaster deals with it, the tool makes it anew
                naming.append({"plugin": r.name, "mod": r.source, "tool": ev[0].tool, "strong": ev[0].strong,
                               "how": ev[0].how, "names_mod": [x for x in r.masters if fold(x) in tf], "judged": True})
                continue
            tool_plugins.append((r, ev))
        # A stake is told from the plugins xEdit loaded for the dry run: the mod, what depends on it and their
        # masters. The rest of the load order was not there, and any plugin of it may have the last word on a
        # record, or say the same as the mod. So for the records a tool's plugin holds, the whole load order is
        # looked through (WHY§77): the leaving plugin must be the last of the plugins no tool made that holds the
        # record, and only the fields in which the plugin next in line says something else are the mod's stake.
        dropped: dict[tuple[str, int], dict] = {}
        held_by_tools: set = set()
        if judged:
            for r, _ev in tool_plugins:
                out = records_of(r.path)
                if out is not None:
                    held_by_tools |= out.index.keys() & changes.keys()
        if held_by_tools:
            made_names = {fold(r.name) for r, _ev in tool_plugins} | {
                fold(r.name) for r in m.plugins.values() if r.source is not None and any(
                    e.kind != "editor" for e in tools.identify(r.name, r.author, r.source, inst.output_mods, binaries))}
            gone = {fold(k) for k in (touched or {})} | tf
            verdicts, cut = _whole_order(m, {k: changes[k] for k in held_by_tools}, gone, made_names, held,
                                         time.monotonic() + WHOLE_ORDER_SECONDS)
            for key, v in verdicts.items():
                ch = changes[key]
                if cut:
                    continue                             # not looked through to the end: the stake stands as told
                ch["next"] = (v["by"], v["next"])
                if not v["wins"]:
                    ch["why_not"] = "%s, which loads after the mod and stays, has the last word on this record" % v["by"]
                else:
                    ch["fields"] = [(t, b, src) for t, b, src in ch.get("all", []) if t not in v["same"]]
                    ch["named"] = {t for t, _b, _s in ch["fields"]}
                    if not ch["fields"]:
                        ch["why_not"] = "the plugin next in line, %s, says the same there as the mod" % (v["by"] or "the record's own plugin")
                if "why_not" in ch:
                    dropped[key] = changes.pop(key)
            if dropped or cut:
                log.info("tools: looked through the whole load order for %d record(s) that tools' plugins hold: %d %s "
                         "the mod's stake%s", len(held_by_tools), len(held_by_tools) - len(dropped),
                         "is" if len(held_by_tools) - len(dropped) == 1 else "are", " (not to the end)" if cut else "")
                for key, ch in list(dropped.items())[:20]:
                    log.info("tools:   %s %06X of %s is no stake: %s", ch["kind"], key[1], key[0], ch["why_not"])
        stake_kinds = Counter(ch["kind"] for ch in changes.values())
        groups = toolmade.synthesis_groups(toolmade.tool_folders(inst, "Synthesis"))
        if any(tools.of_executable(e.title, e.binary)[0] == "Synthesis" for e in inst.executables):
            log.info("tools: Synthesis's own settings file %s", ("names %d group(s) of patchers: %s" % (
                len(groups), "; ".join("%s (%d patcher(s), %d plugin(s) left out)" % (g["group"], len(g["patchers"]), len(g["left_out"]))
                                       for g in groups[:12]))) if groups else "was not found beside its program")
        for r, ev in tool_plugins:
            out = records_of(r.path) if judged else None
            row = {"plugin": r.name, "mod": r.source, "tool": ev[0].tool, "strong": ev[0].strong, "how": ev[0].how,
                   "records": 0, "shared": 0, "carried": 0, "cut": out is None or out.cut or unsure, "details": [],
                   "judged": judged}
            g = toolmade.group_of(r.name, groups) if ev[0].tool == "Synthesis" else None
            if g is not None:
                row["made_by"] = {"group": g["group"], "patchers": g["patchers"]}
                row["left_out"] = sorted(x for x in g["left_out"] if fold(x) in tf)
            if not judged:
                outputs.append(row)
                continue
            if out is not None:
                kinds = Counter(v[3] for v in out.index.values())
                row["kinds"] = [[k, n] for k, n in kinds.most_common(14)]
                row["kinds_more"] = max(0, len(kinds) - 14)
                # the mod's stakes among the kinds this plugin works on, and how many of those it holds
                held_kinds = Counter(changes[key]["kind"] for key in out.index.keys() & changes.keys())
                row["stake_kinds"] = [[k, n, held_kinds.get(k, 0)] for k, n in stake_kinds.most_common() if k in kinds]
                row["records"] = len(out.index)
                row["no_stake"] = [{"kind": dropped[k]["kind"], "owner": k[0], "id": "%06X" % k[1], "why": dropped[k]["why_not"]}
                                   for k in sorted(out.index.keys() & dropped.keys())][:DETAILS]
                for key in out.index.keys() & changes.keys():
                    ch = changes[key]
                    theirs = out.fields(key) or []
                    same = sorted({t for (t, b, src) in ch["fields"] if held((t, b), src, theirs, out)})
                    row["shared"] += 1
                    row["carried"] += bool(same)
                    if len(row["details"]) < DETAILS or same:
                        det = {"kind": ch["kind"], "owner": key[0], "id": "%06X" % key[1],
                               "by": sorted(set(ch["by"])), "carried": same, "changed": sorted(ch["named"])}
                        if same:
                            # The values themselves, so that the finding can be judged at a glance (WHY§78).
                            by_next, next_fields = ch.get("next", ("", {}))
                            det["values"] = [{"field": t,
                                              "mod": show_field(t, next((b for x, b, _s in ch["fields"] if x == t), b"")),
                                              "tool": show_field(t, next((b for x, b in theirs if x == t), b"")),
                                              "next": show_field(t, next_fields[t]) if t in next_fields else "nothing",
                                              "next_by": by_next or "no other plugin"} for t in same[:4]]
                        row["details"].append(det)
                row["details"].sort(key=lambda d: (not d["carried"], d["kind"], d["owner"], d["id"]))
                del row["details"][DETAILS:]
            outputs.append(row)
            # Into the log too, so that a saved session shows what a verdict rests on (WHY§65).
            log.info("tools: %s (%s): holds %d record(s) in which the mod has a stake, %d with the mod's value in them%s",
                     r.name, ev[0].tool, row["shared"], row["carried"], " (not read to the end)" if row["cut"] else "")
            for d in row["details"][:12]:
                log.info("tools:   %s %s of %s, a stake of %s in %s: %s", d["kind"], d["id"], d["owner"],
                         ", ".join(d["by"]), ", ".join(d["changed"][:8]),
                         ("carries " + ", ".join(d["carried"][:8])) if d["carried"] else "none of it carried")
                for x in d.get("values", []):
                    log.info("tools:     %s: the mod has %s; this plugin has %s; next in line (%s) has %s",
                             x["field"], x["mod"], x["tool"], x["next_by"], x["next"])
    finally:
        for rec in opened.values():
            if rec is not None:
                rec.close()

    # By files: every mod that MO2 sends a tool's new files to (whatever the tool, known to ModTrap or not),
    # and the mod that holds the plugin of a tool known to work on files.
    output_files = []
    seen: set[str] = set()
    targets = [(tools.of_executable(title, binaries.get(title, ""))[0], title, target)
               for title, target in sorted(inst.output_mods.items())
               if tools.of_executable(title, binaries.get(title, ""))[1] != "editor"]     # an editor makes nothing by itself
    for f in m.order:
        r = m.plugins[f]
        if r.source is None:
            continue
        for e in tools.identify(r.name, r.author, r.source, {}, binaries):
            if set(data.get(e.tool, {}).get("reads", [])) & {"meshes", "textures", "lod"}:
                targets.append((e.tool, "", r.source))
    for tool, title, target in targets:
        out_mod = inst.mod(target)
        if fold(target) in seen or out_mod is None or out_mod.folder is None or target in names \
                or target.startswith("ModTrap - "):          # ModTrap's own mod is no tool's output mod (WHY§97)
            continue
        seen.add(fold(target))
        listing, cut = walk(out_mod.folder)
        shared = sorted(p for p in listing if "/" in p and p.lower() in paths_low)
        output_files.append({"tool": tool, "title": title, "mod": target, "files": len(listing),
                             "shared": len(shared), "examples": shared[:DETAILS], "cut": cut})
    return outputs, output_files


__all__ = ["compile_steps", "look_deeper", "contents", "replacements", "mentions", "walk"]
