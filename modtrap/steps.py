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

from . import dryrun, model, plugin, tools
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

def compile_steps(m: model.Model, mod_names: list[str], job: dict | None = None, deep: dict | None = None,
                  auto: bool = False, going: bool = False) -> dict:
    """The steps for taking `mod_names` out. `job` is the dry run's public state for the same mods, if there is
    one; `deep` is what `look_deeper` found (it takes seconds on a large list, so it is worked out once). `auto`
    says that ModTrap may change the modlist (it was started with the switch): the steps that "Demaster Selected"
    carries out are then ModTrap's, not the owner's (WHY§57)."""
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
    step("dry", "ModTrap", "Dry run: find out exactly what each dependant takes from the mod",
         "Until xEdit has read the dependants, ModTrap knows only which plugins list the mod as a master, not what "
         "they take from it. The dry run tells a patch made only for the mod from a plugin that must be demastered.",
         dry_state, note=dry_note)

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
        if not names:
            step("tool:" + kind, "you", "Run the tool that handles %s again" % kind,
                 "The mod carries %d file(s) of %s (for example %s). A tool builds its output from all such files in "
                 "the modlist, and that output still has the mod's in it until the tool runs again. No tool of that "
                 "kind is set up in this MO2; if you use one outside MO2, run it." % (
                     info["count"], kind, ", ".join(info["examples"][:2])), "to do")
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
        lines = ["%s %s of %s · changed by %s in %s · %s" % (
            d["kind"], d["id"], d["owner"], ", ".join(d["by"]), ", ".join(d["changed"][:8]),
            ("this plugin holds the same " + ", ".join(d["carried"][:8])) if d["carried"]
            else "this plugin holds none of those changes") for d in o["details"]]
        if o["carried"]:
            e["run"].append("%s carries what the mod changed in %d record(s)" % (o["plugin"], o["carried"]))
        elif o["cut"]:
            e["run"].append("%s could not be read to the end in the time ModTrap allows itself, so ModTrap cannot "
                            "say that nothing of the mod is in it" % o["plugin"])
        elif o["shared"]:
            e["clear"].append("%s holds %d record(s) the mod changes, but none of the mod's changes to them" % (
                o["plugin"], o["shared"]))
        else:
            e["clear"].append("%s holds no record the mod changes" % o["plugin"])
        e["details"].append({"summary": "%s (%s): %d record(s) the mod changes, %d with the mod's changes in them" % (
            o["plugin"], o["how"], o["shared"], o["carried"]),
            "lines": lines or ["Of its %d record(s), none is one the mod or its patches change." % o["records"]]})
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

    clear_items: list[dict] = []
    for tool in sorted(verdict, key=fold):
        e = verdict[tool]
        names = titles_of(tool)
        does = known.get(tool, {}).get("does", "")
        evidence = [{"details": d} for d in e["details"]]
        if e["run"]:
            also = (" What speaks against it: " + "; ".join(e["clear"]) + ".") if e["clear"] else ""
            step("tool:" + tool, "both" if names else "you", "Run %s again" % tool,
                 (does + " " if does else "") + "Why for this mod: " + "; ".join(e["run"]) + "." + also,
                 "to do", [{"tool": n} for n in names] + evidence,
                 note="Run it after the demaster. Only you can tell when this is done: tick it off." if names else
                 "It is not in this MO2's list of tools; run it the way the modlist's own guide says.")
        else:
            clear_items.append({"text": "%s: %s.%s" % (tool, "; ".join(e["clear"]), (" (" + does + ")") if does else ""),
                                "evidence": e["details"]})
    if clear_items:
        step("tools-clear", "ModTrap", "Tools that need no new run for this mod",
             "ModTrap looked at what each of these tools made and found nothing of the mod in it: no file the tool "
             "feeds on, no record with the mod's changes, no file made from the mod's. Each tool has one verdict: "
             "it is either here or among the steps above, never both.", "not needed", clear_items)

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
    if going:                                           # a demaster is in hand: its steps say so (WHY§61)
        for st in steps:
            if st["key"] in ("switch-off", "demaster", "disable") and st["state"] in ("to do", "waiting"):
                st["state"], st["action"] = "going", ""
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
    named, mcut = mentions(inst, trapped, skip) if trapped else ([], False)
    outputs, output_files = tool_outputs(m, mods, trapped, paths_all)
    return {"kinds": kinds, "replacements": reps, "mentions": named, "mentions_cut": mcut, "cut": cut,
            "outputs": outputs, "output_files": output_files}


OUTPUT_SECONDS = 60.0          # all the reading of plugins for one look at the tools, at most
OUTPUT_FILE_SECONDS = 12.0     # and of one plugin
DETAILS = 40                   # records named in one plugin's evidence, at most


def tool_outputs(m: model.Model, mods: list[Mod], trapped: list[str], paths_low: set[str]) -> tuple[list[dict], list[dict]]:
    """Which tools' outputs carry something of the mods being taken out, by evidence (WHY§63, WHY§64).

    A patcher builds its plugin from the whole load order. Its output need not name the mod as a master to carry
    what the mod did: it may have copied a value from the mod's version of a record. Holding the same record is
    not enough to say so, though: a mod often holds a record it does not change at all (a cell it only puts
    things into), and a tool may hold a record for a reason of its own. So, with ModTrap's own reader:

    1. What the mod changes. For each record the mod's plugins (and the patches made for the mod) hold but do not
       own, their version is compared, field by field, with the version in the last of that plugin's own masters
       that holds the record: what the plugin's author had before them. A record with no differing field is not
       changed by the mod, and is left out. The differing fields are the mod's changes.
    2. What a tool's plugin carries. For each plugin a tool made that does not depend on the mod, and each record
       it holds that the mod changes: does it hold one of the mod's changed fields, byte for byte? Then it
       carries the mod's change, and the tool is to run again. If it holds the record but none of the mod's
       changed fields, it was built from another version of the record, or changed other things.

    A generator that works on files is judged by files: how many files of its output mod lie at the path of one
    of the mod's own loose files."""
    inst = m.instance
    tf = {fold(p) for p in trapped}
    game = {fold(x) for x in inst.primary}
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
        return r.path if r is not None else None

    # 1. What the mods' plugins, and the patches made for them, change.
    sources: list[tuple[str, Path, tuple[str, ...]]] = []
    for x in mods:
        for p in x.plugins:
            if x.folder is not None and (x.folder / p).is_file():
                try:
                    sources.append((p, x.folder / p, tuple(plugin.read(x.folder / p).masters)))
                except (plugin.Unreadable, OSError):
                    pass
    for f in m.order:
        r = m.plugins[f]
        if r.path is None or fold(r.name) in tf or not any(fold(x) in tf for x in r.masters):
            continue
        partners = [x for x in r.masters if fold(x) not in game and fold(x) not in tf]
        if len(partners) <= dryrun.PARTNERS and dryrun.named_for(r.name, trapped, names):
            sources.append((r.name, r.path, tuple(r.masters)))
    changes: dict[tuple[str, int], dict] = {}            # record -> {"by", "kind", "fields": set of (type, bytes)}
    unsure = False
    try:
        for name, path, masters in sources:
            src = records_of(path)
            if src is None:
                unsure = True
                continue
            unsure = unsure or src.cut
            for key, (_pos, _len, _flags, kind) in src.index.items():
                if key[0] == src.own:
                    continue                             # the plugin's own record: nothing else can hold it unasked
                mine = src.fields(key) or []
                before = None
                for master in reversed([x for x in masters if fold(x) not in tf]):
                    held = records_of(path_of(master))
                    if held is not None and key in held.index:
                        before = held.fields(key)
                        break
                if before is None:
                    changed = set(mine)                  # no earlier version to be had: every field counts
                else:
                    earlier = set(before)
                    changed = {fd for fd in mine if fd not in earlier}
                    if not changed and len(mine) == len(before):
                        continue                         # held, but not changed
                    if not changed:
                        changed = {("(a field taken out)", b"")}
                entry = changes.setdefault(key, {"by": [], "kind": kind, "fields": set()})
                entry["by"].append(name)
                entry["fields"] |= changed

        # 2. What each tool-made plugin carries of that.
        outputs = []
        for f in m.order:
            r = m.plugins[f]
            if not r.active or r.source is None or r.path is None or fold(r.name) in tf:
                continue
            if any(fold(x) in tf for x in r.masters):
                continue                                 # a dependant: the demaster itself deals with it
            ev = [e for e in tools.identify(r.name, r.author, r.source, inst.output_mods, binaries) if e.kind != "editor"]
            if not ev or "plugins" not in data.get(ev[0].tool, {}).get("reads", ["plugins"]):
                continue
            out = records_of(r.path)
            row = {"plugin": r.name, "mod": r.source, "tool": ev[0].tool, "strong": ev[0].strong, "how": ev[0].how,
                   "records": 0, "shared": 0, "carried": 0, "cut": out is None or out.cut or unsure, "details": []}
            if out is not None:
                row["records"] = len(out.index)
                for key in out.index.keys() & changes.keys():
                    ch = changes[key]
                    theirs = set(out.fields(key) or [])
                    same = sorted({t for (t, b) in ch["fields"] if (t, b) in theirs})
                    row["shared"] += 1
                    row["carried"] += bool(same)
                    if len(row["details"]) < DETAILS or same:
                        row["details"].append({"kind": ch["kind"], "owner": key[0], "id": "%06X" % key[1],
                                               "by": sorted(set(ch["by"])), "carried": same,
                                               "changed": sorted({t for (t, _b) in ch["fields"]})})
                row["details"].sort(key=lambda d: (not d["carried"], d["kind"], d["owner"], d["id"]))
                del row["details"][DETAILS:]
            outputs.append(row)
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
        if fold(target) in seen or out_mod is None or out_mod.folder is None or target in names:
            continue
        seen.add(fold(target))
        listing, cut = walk(out_mod.folder)
        shared = sorted(p for p in listing if "/" in p and p.lower() in paths_low)
        output_files.append({"tool": tool, "title": title, "mod": target, "files": len(listing),
                             "shared": len(shared), "examples": shared[:DETAILS], "cut": cut})
    return outputs, output_files


__all__ = ["compile_steps", "look_deeper", "contents", "replacements", "mentions", "walk"]
