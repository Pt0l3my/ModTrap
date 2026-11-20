"""The steps of a demaster (DESIGN§14, MT18): everything it takes to get the ticked mods out of a modlist, worked
out from the modlist itself, the tools set up in MO2 and, once there is one, the dry run. Each step says who does
it, why it is needed, and whether the modlist's own files show it done.

Read-only. Beyond the plugin headers the model already holds, this module lists file names in the ticked mods'
folders, and looks into small settings files of other mods for a ticked plugin's name (WHY§35).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from . import model, tools
from .instance import GAME, OVERWRITE, Instance, Mod, fold

WALK_FILES = 60_000            # file names listed in one mod's folder at most
WALK_SECONDS = 4.0
CONFIG_BYTES = 512 * 1024      # a settings file larger than this is not looked into
CONFIG_FILES = 30_000          # settings files looked into at most, over all mods
CONFIG_SECONDS = 12.0
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


def mentions(inst: Instance, plugin_names: list[str], skip: set[str]) -> tuple[list[dict], bool]:
    """Settings files of other enabled mods that name one of these plugins: lines for a distributor or a patcher
    that runs in the game. Without the plugin those lines do nothing. Only small text files are looked into, in
    the places such files live: a mod's top folder and its SKSE/Plugins folder."""
    needles = [n.lower().encode("utf-8") for n in plugin_names]
    out: list[dict] = []
    looked, stop, cut = 0, time.monotonic() + CONFIG_SECONDS, False
    for m in inst.mods:
        if m.kind != "mod" or not m.enabled or m.folder is None or fold(m.name) in skip:
            continue
        cands: list[Path] = []
        try:
            with os.scandir(m.folder) as it:
                cands += [Path(e.path) for e in it if CONFIG_NAME.search(e.name) and e.name.lower() != "meta.ini"
                          and e.is_file(follow_symlinks=False)]
        except OSError:
            continue
        sk = m.folder / "SKSE" / "Plugins"
        if sk.is_dir():
            files, _ = walk(sk, limit=2_000, seconds=1.0)
            cands += [sk / f for f in files if CONFIG_NAME.search(f)]
        for path in cands:
            if looked >= CONFIG_FILES or time.monotonic() > stop:
                cut = True
                break
            try:
                if path.stat().st_size > CONFIG_BYTES:
                    continue
                with open(path, "rb") as f:
                    data = f.read(CONFIG_BYTES).lower()
            except OSError:
                continue
            looked += 1
            found = [plugin_names[i] for i, n in enumerate(needles) if n in data]
            if found:
                out.append({"mod": m.name, "file": path.relative_to(m.folder).as_posix(), "names": found})
        if cut:
            break
    return out, cut


# --- compiling the steps ------------------------------------------------------------------------------------------

def compile_steps(m: model.Model, mod_names: list[str], job: dict | None = None, deep: dict | None = None) -> dict:
    """The steps for taking `mod_names` out. `job` is the dry run's public state for the same mods, if there is
    one; `deep` is what `look_deeper` found (it takes seconds on a large list, so it is worked out once)."""
    inst = m.instance
    mods = [x for x in (inst.mod(n) for n in mod_names) if x is not None and x.kind == "mod"]
    trapped = sorted({p for x in mods for p in x.plugins}, key=fold)            # by file, enabled or not
    tf = {fold(p) for p in trapped}
    steps: list[dict] = []

    def step(key: str, who: str, title: str, why: str, state: str, items: list | None = None, note: str = "") -> None:
        steps.append({"key": key, "who": who, "title": title, "why": why, "state": state, "items": items or [],
                      "note": note, "n": len(steps) + 1})

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
    step("dry", "ModTrap", "Dry run: find out exactly what each dependant takes from the mod",
         "Until xEdit has read the dependants, ModTrap knows only which plugins list the mod as a master, not what "
         "they take from it. The dry run tells a patch made only for the mod from a plugin that must be demastered.",
         dry_state, note=dry_note)

    # 2-4. The dependants, sorted by what is to be done with them.
    outputs = [r for r in active_left if makers(r)]
    regen = [r for r in outputs if tools.proposal(makers(r)) != "demaster"]
    editors = [r for r in outputs if r not in regen]          # written through an editor: cannot be made again
    rest = [r for r in active_left if r not in outputs]
    patch_only = [r for r in rest if verdict.get(fold(r.name), {}).get("reading") == "patch only"]
    to_demaster = [r for r in rest if r not in patch_only] + editors
    known = bool(result and same_job) or not active_left      # the dry run has sorted the dependants, or none is left

    step("switch-off", "you", "Switch off the patches made only for the mod",
         "A plugin in which every record belongs to the mod has nothing left without it. Deactivate it on MO2's "
         "Plugins tab (or disable its mod, if every plugin of that mod is listed here). ModTrap will do this itself "
         "once its demaster step is built.",
         "waiting for the dry run" if not known else "to do" if patch_only else "done",
         [brief(r) for r in patch_only],
         note="" if known else "The dry run shows which dependants are patches of this kind.")
    step("demaster", "you", "Demaster the plugins that must go on working without the mod",
         "Each of these needs the mod only in places: its copies of the mod's records, and entries pointing at "
         "them. Those are taken out in xEdit (the guide's Master Removal steps), then Clean Masters. ModTrap will do "
         "this itself once its demaster step is built; the dry run lists exactly what would go.",
         "waiting for the dry run" if not known else "to do" if to_demaster else "done",
         [brief(r) for r in to_demaster],
         note="Done when the plugin no longer lists the mod as a master (press Rescan to check).")
    if regen:
        step("regenerate", "you", "Run again the tools whose output depends on the mod",
             "These plugins were made by a tool, from the load order as it was. Once the mod and its patches are "
             "switched off, running the tool again rebuilds them without it. Do this after the steps above.",
             "to do", [brief(r) for r in regen],
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
    step("disable", "you", "Disable the mod%s in MO2" % ("s" if len(disable) > 1 else ""),
         "Disabled, never removed: the mod stays in MO2's list and can be enabled again. Do it only when nothing "
         "active needs its plugins any more, or MO2 will warn of missing masters.",
         "done" if all_off else "to do" if not blockers else "waiting",
         disable, note="" if not blockers or all_off else "%d active plugin(s) still list a ticked plugin as a master." % blockers)

    # 6. Tools fed by the mod's loose files.
    for kind, info in sorted(deep.get("kinds", {}).items()):
        names = tools_for(inst, kind)
        if kind in TOOLS_FOR:
            step("tool:" + kind, "you",
                 "Run %s again" % (" or ".join("“%s”" % n for n in names) if names else "the tool that handles " + kind),
                 "The mod carries %d file(s) of %s (for example %s). A tool built its output from them, and that "
                 "output still has them in it until the tool runs again. No plugin's master list shows this." % (
                     info["count"], kind, ", ".join(info["examples"][:2])),
                 "to do", [{"tool": n} for n in names],
                 note="Only you can tell when this is done: tick it off." if names else
                 "No tool of that kind is set up in this MO2; if you use one outside MO2, run it.")
    # 7. Settings files of other mods that name a ticked plugin.
    named = deep.get("mentions", [])
    if named:
        step("mentions", "you", "Look at the settings files that name the mod's plugin",
             "These files of other mods name a ticked plugin: lines for something that works while the game runs "
             "(a distributor, a patcher, a swapper). With the plugin gone such a line simply does nothing, which is "
             "usually fine; look if one of them matters to you.",
             "to do", named, note="A judgement, not a fault: tick it off when you have looked."
             + (" The search was cut short; there may be more." if deep.get("mentions_cut") else ""))

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
    manual = {"mentions", "play"} | {s["key"] for s in steps if s["key"].startswith("tool:")}
    for s in steps:
        s["manual"] = s["key"] in manual           # nothing on disk can prove these: the owner ticks them off
    open_steps = [s for s in steps if s["state"] not in ("done", "not needed") and not s["manual"]]
    return {"mods": [x.name for x in mods], "trapped": trapped, "steps": steps, "complete": not open_steps,
            "deep": bool(deep), "contents": {k: v["count"] for k, v in deep.get("kinds", {}).items()},
            "contents_cut": bool(deep.get("cut")),
            "summary": ("Every step that files can prove is done." if not open_steps else
                        "%d step(s) to go." % len(open_steps))}


def look_deeper(m: model.Model, mod_names: list[str]) -> dict:
    """The part of the steps that reads folders: what the ticked mods carry, which mods only replace their files,
    and which settings files name their plugins. Seconds on a large list."""
    inst = m.instance
    mods = [x for x in (inst.mod(n) for n in mod_names) if x is not None and x.kind == "mod" and x.folder is not None]
    kinds: dict[str, dict] = {}
    reps: list[dict] = []
    cut = False
    for x in mods:
        c = contents(x.folder)
        cut = cut or c["cut"]
        for k, v in c["kinds"].items():
            e = kinds.setdefault(k, {"count": 0, "examples": []})
            e["count"] += v["count"]
            e["examples"] = (e["examples"] + v["examples"])[:3]
        reps += [r for r in replacements(inst, x, c["paths"]) if r["mod"] not in mod_names
                 and r["mod"] not in [q["mod"] for q in reps]]
    trapped = sorted({p for x in mods for p in x.plugins}, key=fold)
    skip = {fold(x.name) for x in mods} | {fold(r["mod"]) for r in reps}
    named, mcut = mentions(inst, trapped, skip) if trapped else ([], False)
    return {"kinds": kinds, "replacements": reps, "mentions": named, "mentions_cut": mcut, "cut": cut}


__all__ = ["compile_steps", "look_deeper", "contents", "replacements", "mentions", "walk"]
