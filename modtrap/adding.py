"""Adding mods to a modlist (MT21, DESIGN§16): for mods that MO2 has already installed, what each one brings, what
it needs, where it would go among the mods and in the load order, which files it would replace or lose, which
tools must run again, and the steps to add it safely.

Read-only. It reads plugin headers, lists file names in mod folders, and reads one line of each mod's meta.ini
(the archive it was installed from). What is inside a plugin's records is xEdit's to read, not this module's.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from . import model, plugin, steps, tools
from .instance import GAME, OVERWRITE, Instance, Mod, fold, ini_value

FULL_SLOTS = 254               # XE02§6: full plugins the game can load
LIGHT_SLOTS = 4096             # XE02§6: light plugins
NEW_HEADER = 1.71              # XE02§6: the header version the newer game versions introduced
META_BYTES = 256 * 1024        # meta.ini is read no further than this
CONFLICT_SECONDS = 25.0        # looking for shared files, over all the mods to add
DIFFER_SECONDS = 20.0        # the most a comparing of two versions' files may take
EXAMPLES = 4
TAIL_GAP = 2                   # plugins of unknown making that may sit among the tools' output at the load order's end
ARCHIVE = re.compile(r"\.(7z|zip|rar|fomod|exe|001)$", re.IGNORECASE)
# What a download site adds to a file's name: "-<numbers>" one after another (Nexus's older way), or
# " <mod's number> <version> <day>T<time>Z <code>" (its newer way, TL01§31); and a browser's "(1)".
NEXUS_TAIL = re.compile(r"(?: ?\(\d+\))?$|(-\d+)+(?: ?\(\d+\))?$")
LAST = "*last*"                               # a place chosen by hand: last of all in MO2's list
NEXUS_NEW = re.compile(r" (\d{1,8}) (\S+) (\d{4}-\d\d-\d\dT\d\d-\d\dZ) ([0-9A-Za-z]{6,16})(?: ?\(\d+\))?$")
NEXUS_OLD = re.compile(r"-(\d{1,8})-([0-9A-Za-z-]+?)-(\d{9,11})(?: ?\(\d+\))?$")


def from_archive_name(archive: str) -> dict:
    """What a download's name says of itself, where a site wrote it: {"stem": the name without what the site added,
    "mod_id", "version", "code"}; the numbers are 0 or "" where the name does not say."""
    stem = ARCHIVE.sub("", archive)
    m = NEXUS_NEW.search(stem)
    if m:
        return {"stem": stem[:m.start()].strip(" ."), "mod_id": int(m.group(1)), "version": m.group(2), "code": m.group(4)}
    m = NEXUS_OLD.search(stem)
    if m:
        return {"stem": stem[:m.start()].strip(" ."), "mod_id": int(m.group(1)), "version": m.group(2).replace("-", "."), "code": ""}
    return {"stem": NEXUS_TAIL.sub("", re.sub(r" ?\(\d+\)$", "", stem)).strip(" ."), "mod_id": 0, "version": "", "code": ""}
OUTPUT_NAME = re.compile(r"\boutputs?\b", re.IGNORECASE)
_INSTALLED = re.compile(rb"^installationFile=(.*)$", re.MULTILINE)
# Kinds of shared file worth a look before the mod goes in, and why.
NOTABLE = {
    "plugin": "a plugin of the same name: the mod replaces that plugin itself",
    "scripts": "compiled scripts: only the winner's version runs, and the other mod was made for its own",
    "script extender plugin": "the same script extender plugin twice: only one version is loaded",
    "face data": "face files: the mod that wins a character's face files must be the one whose plugin wins that "
                 "character, or the face turns dark",
    "archive": "an archive of the same name: only one of the two is used",
    "menus": "menu files: the look or the settings menu of the other mod is replaced",
}


def is_master(kind: str) -> bool:
    """The game loads these before every other plugin (XE02§3)."""
    return kind.startswith("esm") or kind == "esl" or "+esm" in kind


def is_light(kind: str) -> bool:
    return "esl" in kind


# --- which mod was dropped (DESIGN§16.1) ---------------------------------------------------------------------------

def installed_from(inst: Instance) -> dict[str, list[str]]:
    """The archive's file name (folded) to the mods MO2 installed from it, by each mod's meta.ini (MO01§7)."""
    out: dict[str, list[str]] = {}
    for m in inst.mods:
        if m.kind != "mod" or m.folder is None:
            continue
        try:
            with open(m.folder / "meta.ini", "rb") as f:
                hit = _INSTALLED.search(f.read(META_BYTES))
        except OSError:
            continue
        if not hit:
            continue
        try:
            value = ini_value(hit.group(1).decode("utf-8", "replace").strip())
        except (ValueError, OverflowError):
            continue
        name = value.replace("\\", "/").rsplit("/", 1)[-1]
        if name:
            out.setdefault(fold(name), []).append(m.name)
    return out


def resolve(inst: Instance, dropped: list[dict], index: dict[str, list[str]] | None = None) -> list[dict]:
    """What each dropped thing is in this MO2. A page learns only a dropped file's or folder's name, so the name
    is what is matched: a mod's folder by its name, an archive by the mod MO2 installed from it."""
    by_name = {fold(m.name): m for m in inst.mods if m.kind == "mod"}
    out = []
    for item in dropped:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        hit = by_name.get(fold(name))
        if hit is not None:
            out.append({"name": name, "mods": [hit.name], "how": "a mod of this name is in MO2", "sure": True})
            continue
        if index is None:
            index = installed_from(inst)
        mods = index.get(fold(name), [])
        if mods:
            out.append({"name": name, "mods": mods, "how": "MO2 installed %s from this file" % (
                "this mod" if len(mods) == 1 else "these mods"), "sure": True})
            continue
        stem = NEXUS_TAIL.sub("", ARCHIVE.sub("", name)).strip()
        hit = by_name.get(fold(stem))
        if hit is not None:
            out.append({"name": name, "mods": [hit.name], "how": "a mod in MO2 has this file's name", "sure": False})
            continue
        downloaded = False
        if inst.downloads_dir is not None and ARCHIVE.search(name):
            try:
                downloaded = (inst.downloads_dir / name).is_file()
            except OSError:
                downloaded = False
        out.append({"name": name, "mods": [], "sure": False, "downloaded": downloaded,
                    "how": ("It is in MO2's Downloads, but not installed. Install it in MO2 (double-click it on the "
                            "Downloads tab), leave it disabled, press Rescan here, then drop it again."
                            if downloaded else
                            "MO2 has no mod installed from it. Install it in MO2 first (the “Install a new mod from "
                            "an archive” button), leave it disabled, press Rescan here, then drop it again.")})
    return out


# --- files shared with other mods (DESIGN§16.4) ---------------------------------------------------------------------

def _trie(paths: list[str]) -> dict:
    root: dict = {}
    for p in paths:
        parts = p.lower().split("/")
        node = root
        for part in parts[:-1]:
            nxt = node.get(part)
            if nxt is None:
                if part in node:
                    break                      # a file where another path has a folder: left out
                nxt = node[part] = {}
            node = nxt
        else:
            node.setdefault(parts[-1], None)
    return root


def shared_files(folder: Path, trie: dict, stop: float) -> tuple[list[str], bool]:
    """The files under `folder` that the trie also has, as relative paths. Only folders the trie has are entered,
    so a mod that shares nothing costs one listing of its top folder."""
    out: list[str] = []
    stack = [(folder, trie, "")]
    while stack:
        if time.monotonic() > stop:
            return out, True
        d, node, rel = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            low = e.name.lower()
            if low not in node:
                continue
            child = node[low]
            try:
                if child is None:
                    if e.is_file(follow_symlinks=False):
                        out.append(rel + e.name)
                elif e.is_dir(follow_symlinks=False):
                    stack.append((Path(e.path), child, rel + e.name + "/"))
            except OSError:
                continue
    return out, False


def kind_of(path: str) -> str:
    low = path.lower()
    if "/" not in low and plugin.is_plugin_name(low):
        return "plugin"
    return next((k for k, rx in steps.KINDS if rx.search(low)), "other files")


# --- where it would go (DESIGN§16.3) --------------------------------------------------------------------------------

def _makers(m: model.Model, r: model.PluginRow, memo: dict) -> list:
    f = fold(r.name)
    if f not in memo:
        inst = m.instance
        memo[f] = tools.identify(r.name, r.author, r.source or "", inst.output_mods,
                                 {e.title: e.binary for e in inst.executables})
    return memo[f]


def output_section(m: model.Model, memo: dict) -> tuple[str, set[str]]:
    """A curated modlist keeps what its tools made under a separator of its own, named for it ("Outputs"). Returns
    that separator's name and the (folded) names of the mods under it, or ("", empty) when there is none. A
    separator heads the mods that follow it in priority, up to the next separator."""
    if "section" not in memo:
        inst = m.instance
        listed = [x for x in inst.mods if x.kind in ("mod", "separator", "foreign")]
        found: tuple[str, set[str]] = ("", set())
        for i, x in enumerate(listed):
            if x.kind == "separator" and OUTPUT_NAME.search(x.name[:-len("_separator")] if x.name.lower().endswith("_separator") else x.name):
                mods: set[str] = set()
                for y in listed[i + 1:]:
                    if y.kind == "separator":
                        break
                    mods.add(fold(y.name))
                if any(inst.mod(n) is not None and inst.mod(n).enabled for n in mods) and len(mods) > len(found[1]):
                    found = (x.name, mods)
        memo["section"] = found
    return memo["section"]


def generated(m: model.Model, r: model.PluginRow, memo: dict) -> list:
    """The evidence that a tool made this plugin and can make it again (not an editor: TL01§6); or that the
    modlist itself keeps it among its outputs (kind "section": which tool made it is then not known)."""
    out = [e for e in _makers(m, r, memo) if e.kind != "editor" and e.strong]
    if not out and r.source:
        name, mods = output_section(m, memo)
        if fold(r.source) in mods:
            out = [tools.Evidence("", "section", "its mod is under the modlist's own “%s” heading" % name.replace("_separator", ""), True)]
    return out


def is_output_mod(m: model.Model, mod: Mod, memo: dict) -> str:
    """Why this mod is taken as a tool's output, or ""."""
    inst = m.instance
    name, mods = output_section(m, memo)
    if fold(mod.name) in mods:
        return "it is under the modlist's own “%s” heading" % name.replace("_separator", "")
    for title, target in inst.output_mods.items():
        if fold(target) == fold(mod.name):
            return "MO2 sends the new files of “%s” to it" % title
    rows = m.provided_by(mod)
    if rows and all(generated(m, r, memo) for r in rows):
        return "every plugin in it was made by a tool"
    if OUTPUT_NAME.search(mod.name):
        return "its name says so"
    return ""


def mod_place(m: model.Model, adding: set[str], memo: dict) -> dict:
    """After every ordinary mod, before the tools' outputs at the end of MO2's list: the new mod wins every file
    it shares with an ordinary mod, and what the tools made stays last, to be made again. `adding` holds the
    (folded) names of the mods being placed; they are left out of the reckoning."""
    inst = m.instance
    listed = [x for x in inst.mods if x.kind in ("mod", "separator", "foreign") and fold(x.name) not in adding]
    heading, under = output_section(m, memo)
    if heading:
        # The modlist has a heading for its outputs: the new mod goes right before that heading, at the end of the
        # section before it. Whatever the list keeps after its outputs (options, presets) stays after it too.
        idx = next(i for i, x in enumerate(listed) if x.name == heading)
        outputs = [{"mod": x.name, "why": "it is under the modlist's own “%s” heading" % heading.replace("_separator", "")}
                   for x in listed if fold(x.name) in under and x.enabled]
        return {"priority": listed[idx].priority, "before": listed[idx].name,
                "after": listed[idx - 1].name if idx > 0 else "", "outputs": outputs, "heading": heading}
    idx = len(listed)                           # the new mod goes before listed[idx]
    outputs: list[dict] = []
    for i in range(len(listed) - 1, -1, -1):
        x = listed[i]
        why = is_output_mod(m, x, memo) if x.kind == "mod" and x.enabled else ""
        if why:
            outputs.append({"mod": x.name, "why": why})
            idx = i
        elif x.kind == "separator" or not x.enabled:
            continue                            # says nothing either way
        else:
            break
    while outputs and idx > 0 and listed[idx - 1].kind == "separator":
        idx -= 1                                # the outputs' own heading stays with them
    before = listed[idx].name if idx < len(listed) else ""
    after = listed[idx - 1].name if idx > 0 else ""
    priority = listed[idx].priority if idx < len(listed) else (listed[-1].priority + 1 if listed else 0)
    return {"priority": priority, "before": before, "after": after, "outputs": outputs}


def tail_start(m: model.Model, memo: dict, masters: bool) -> tuple[int, list[str]]:
    """The place where a new plugin goes: before the tools' output at the end of the load order (or, for a
    master-flagged plugin, before the tools' output at the end of the masters' block). Returns the position and
    the generated plugins that stay after it. Plugins that are not active, or have no file, say nothing."""
    rows = [m.plugins[f] for f in m.order if m.plugins[f].position is not None]
    end = len(rows)
    if masters:
        end = next((i for i, r in enumerate(rows) if r.source is not None and not is_master(r.kind)), len(rows))
    start = end
    after: list[str] = []
    odd: list[tuple[int, str]] = []             # plugins not known to be made by a tool, met on the way back
    for i in range(end - 1, -1, -1):
        r = rows[i]
        if r.source is None or not r.active:
            continue
        if not generated(m, r, memo):
            odd.append((i, r.name))
            if len(odd) > TAIL_GAP:
                break                           # the run of outputs has ended
            continue
        # A tool-made plugin: it and the few unknown ones between it and the run so far all stay after.
        for _j, name in reversed(odd):
            after.insert(0, name)
        odd = []
        after.insert(0, r.name)
        start = i
    pos = rows[start].position if start < len(rows) else (rows[-1].position + 1 if rows else 0)
    return pos, after


# --- the analysis ---------------------------------------------------------------------------------------------------

def _sizes(folder: Path, stop: float) -> tuple[dict[str, tuple[str, int]], bool]:
    """Every file under a mod's folder: {its path in lower case: (its path, its size)}; and whether time ran out."""
    out: dict[str, tuple[str, int]] = {}
    todo = [(folder, "")]
    while todo:
        if time.monotonic() > stop:
            return out, True
        here, rel = todo.pop()
        try:
            with os.scandir(here) as it:
                for e in it:
                    name = rel + e.name
                    try:
                        if e.is_dir(follow_symlinks=False):
                            todo.append((Path(e.path), name + "/"))
                        elif name.lower() != "meta.ini":
                            out[name.lower()] = (name, e.stat(follow_symlinks=False).st_size)
                    except OSError:
                        continue
        except OSError:
            continue
    return out, False


def version_changes(old: Path, new: Path, stop: float) -> dict:
    """What a newer version of a mod differs in from the older one, by its files' names and sizes (MT49): how many
    files are new, gone, of another size, and the same; the same by kind; and the plugins among them. A file of the
    same name and size counts as the same: its contents are not read."""
    a, cut_a = _sizes(old, stop)
    b, cut_b = _sizes(new, stop)
    added = [b[k][0] for k in b if k not in a]
    gone = [a[k][0] for k in a if k not in b]
    changed = [b[k][0] for k in b if k in a and a[k][1] != b[k][1]]
    kinds: dict[str, int] = {}
    for f in added + gone + changed:
        k = kind_of(f)
        kinds[k] = kinds.get(k, 0) + 1
    plug = lambda files: sorted((f for f in files if kind_of(f) == "plugin"), key=str.lower)
    return {"added": len(added), "gone": len(gone), "changed": len(changed), "same": len(b) - len(added) - len(changed),
            "kinds": kinds, "plugins": {"added": plug(added), "gone": plug(gone), "changed": plug(changed)},
            "examples": sorted(added + gone + changed, key=str.lower)[:EXAMPLES], "cut": cut_a or cut_b}


def staged_mod(name: str, folder: Path) -> Mod:
    """A mod ModTrap has unpacked in its own work folder and MO2 does not have yet (DESIGN§16.1)."""
    try:
        plugs = tuple(sorted((e.name for e in os.scandir(folder) if plugin.is_plugin_name(e.name) and e.is_file()),
                             key=fold))
    except OSError:
        plugs = ()
    return Mod(name, -1, False, "mod", folder, plugs, listed=False)


def analyse(m: model.Model, names: list[str], read=plugin.read, seconds: float = CONFLICT_SECONDS,
            staged: list[Mod] | tuple[Mod, ...] = (), auto: bool = False, updates: dict[str, str] | None = None,
            before: str = "") -> dict:
    """Everything ModTrap can tell about adding these mods without xEdit. `staged` are mods unpacked in
    ModTrap's work folder, not yet in MO2: they are read where they lie. `updates` names, for a staged mod, the
    mod of the modlist it is a newer version of (MT40): it is then judged at that mod's own place, right above
    it, and not at the place a new mod would get."""
    inst = m.instance
    memo: dict = {}
    olds = {fold(new): inst.mod(old) for new, old in (updates or {}).items()}
    olds = {k: v for k, v in olds.items() if v is not None and v.kind == "mod"}

    def above(old: Mod) -> str:
        """The mod that stands right above `old` in MO2's list: a newer version goes directly before it."""
        nxt = min((y for y in inst.mods if y.priority > old.priority and y.kind in ("mod", "separator", "foreign")),
                  key=lambda y: y.priority, default=None)
        return nxt.name if nxt is not None else ""

    cands = [x for x in (inst.mod(n) for n in names) if x is not None and x.kind == "mod" and x.folder is not None]
    waiting = {id(x) for x in staged}
    cands += list(staged)
    adding = {fold(x.name) for x in cands}
    place = mod_place(m, {fold(x.name) for x in cands if not x.enabled}, memo)
    place["chosen"] = False
    if before:
        # A place the owner chose (MT53): right before the mod, heading or other entry of MO2's list they named,
        # or last of all.
        target = inst.mod(before) if before != LAST else None
        listed = sorted((y for y in inst.mods if y.kind in ("mod", "separator", "foreign") and fold(y.name) not in adding), key=lambda y: y.priority)
        if before == LAST:
            place = {"priority": (listed[-1].priority + 1) if listed else 0, "before": "", "after": listed[-1].name if listed else "", "outputs": place["outputs"],
                     "heading": "", "chosen": True, "would_be": place["before"]}
        elif target is not None and target.kind in ("mod", "separator", "foreign") and fold(target.name) not in adding:
            i = next(k for k, y in enumerate(listed) if y.name == target.name)
            place = {"priority": target.priority, "before": target.name, "after": listed[i - 1].name if i > 0 else "", "outputs": place["outputs"],
                     "heading": place.get("heading", ""), "chosen": True, "would_be": place["before"]}
    turn = {x.name: i for i, x in enumerate(cands)}

    def effective(x: Mod) -> float:
        """A mod's priority as it would be: a mod still to enable sits in the proposed place."""
        if not x.enabled and fold(x.name) in olds:
            return olds[fold(x.name)].priority + 0.5
        return float(x.priority) if x.enabled else place["priority"] - 0.5 + 0.001 * turn.get(x.name, 0)
    stop = time.monotonic() + seconds

    # Plugins that the mods to add bring, by name: a master may come with another mod of the same batch.
    brought = {fold(p): x.name for x in cands for p in x.plugins}
    in_disabled: dict[str, list[str]] = {}
    for x in inst.mods:
        if x.kind == "mod" and not x.enabled and fold(x.name) not in adding:
            for p in x.plugins:
                in_disabled.setdefault(fold(p), []).append(x.name)

    full_now = sum(1 for r in m.plugins.values() if r.active and r.source is not None and not is_light(r.kind))
    light_now = sum(1 for r in m.plugins.values() if r.active and r.source is not None and is_light(r.kind))
    full_add = light_add = 0
    kinds_all: dict[str, int] = {}
    new_plugins = 0
    out_mods = []
    cut_any = False
    rows_in_order = {r.position: r for r in m.plugins.values() if r.position is not None}

    for x in cands:
        files, cut = steps.walk(x.folder)
        files = [f for f in files if f.lower() != "meta.ini"]
        cut_any = cut_any or cut
        kinds: dict[str, int] = {}
        for f in files:
            k = kind_of(f)
            kinds[k] = kinds.get(k, 0) + 1
        for k, n in kinds.items():
            kinds_all[k] = kinds_all.get(k, 0) + n

        # Its plugins.
        plugs = []
        for p in x.plugins:
            entry: dict = {"name": p, "kind": "", "masters": [], "unreadable": "", "version": None, "notes": []}
            try:
                h = read(x.folder / p)
                entry["kind"] = plugin.kind(p, h)
                entry["version"] = h.version
                masters = h.masters
            except plugin.Unreadable as e:
                entry["unreadable"] = str(e)
                masters = ()
            row = m.row(p)
            mine = row is not None and row.source == x.name
            other = row is not None and row.source not in (None, x.name)
            entry["active"] = bool(row is not None and row.active and (mine or (other and x.enabled)))
            entry["position"] = row.position if entry["active"] else None
            if other and x.enabled:
                entry["notes"].append("“%s” has a plugin of the same name and the higher priority: MO2 uses that "
                                      "copy, not this mod's." % row.source)
            elif other:
                entry["replaces"] = {"mod": row.source, "priority": row.source_priority,
                                     "dependants": len(row.dependants), "active": row.active}
            latest = -1
            for mname in masters:
                mr = m.row(mname)
                if mr is not None and mr.source is not None and fold(mr.source) not in adding:
                    state = "active" if mr.active else "inactive"
                    entry["masters"].append({"name": mname, "state": state, "mod": mr.source, "position": mr.position})
                    if mr.position is not None:
                        latest = max(latest, mr.position)
                elif fold(mname) in brought:
                    entry["masters"].append({"name": mname, "state": "comes along", "mod": brought[fold(mname)]})
                elif fold(mname) in in_disabled:
                    entry["masters"].append({"name": mname, "state": "disabled mod", "mods": in_disabled[fold(mname)]})
                else:
                    entry["masters"].append({"name": mname, "state": "missing"})
            if not entry["unreadable"]:
                master = is_master(entry["kind"])
                pos, after = tail_start(m, memo, master)
                why = ("at the end of the masters' block" if master else
                       "after everything made by hand, before what the tools made" if after else "at the end")
                if latest >= pos:
                    pos, why = latest + 1, "after its last master"
                    after = [n for n in after if (m.row(n).position or 0) >= pos]
                before = rows_in_order.get(pos)
                entry["proposed"] = {"position": pos, "before": before.name if before is not None else "",
                                     "why": why, "stay_after": after}
                if master and any(mm["state"] == "active" and not is_master(m.row(mm["name"]).kind)
                                  for mm in entry["masters"]):
                    entry["notes"].append("It is flagged as a master but needs a plugin that is not: the game loads "
                                          "masters first whatever the list says, so it would load before that plugin.")
                if entry["active"] and not master and after and entry["position"] is not None \
                        and entry["position"] > pos and not generated(m, row, memo):
                    entry["notes"].append("It now loads after %s, which a tool made: generated plugins are meant to "
                                          "stay last." % ", ".join(after[:3]))
                if entry["version"] is not None and entry["version"] >= NEW_HEADER - 0.001:
                    entry["notes"].append("Its header is in the newer format (%.2f): it needs game version 1.6.1130 "
                                          "or later, or a backport of that format on an older game." % entry["version"])
                # A plugin of a newer version that the load order already names keeps the older version's place
                # and state there (MT40): it is not a new plugin.
                there = m.row(entry["name"]) if fold(x.name) in olds else None
                if there is not None and there.position is not None and not entry["active"]:
                    entry["keeps"] = {"position": there.position, "active": bool(there.active)}
                if not entry["active"] and not entry.get("keeps"):
                    new_plugins += 1
                    if is_light(entry["kind"]):
                        light_add += 1
                    else:
                        full_add += 1
            plugs.append(entry)
        # Files it shares with other mods.
        trie = _trie(files)
        my_priority = effective(x)
        wins, loses = [], []
        # The older version of an update is not another mod it shares files with: it is the one it stands in for.
        mine_old = olds[fold(x.name)].name if fold(x.name) in olds else None
        others = [o for o in inst.mods if o.kind in ("mod", "overwrite") and o.folder is not None and o.enabled
                  and o.name != x.name and o.name != mine_old]
        others += [o for o in cands if o.name != x.name and not o.enabled]
        for o in others:
            if not trie or time.monotonic() > stop:
                cut_any = cut_any or bool(trie)
                break
            found, c = shared_files(o.folder, trie, stop)
            cut_any = cut_any or c
            found = [f for f in found if f.lower() != "meta.ini"]
            if not found:
                continue
            ks: dict[str, int] = {}
            for f in found:
                k = kind_of(f)
                ks[k] = ks.get(k, 0) + 1
            o_priority = effective(o)
            entry2 = {"mod": o.name, "priority": o.priority if o.enabled else None, "files": len(found), "kinds": ks,
                      "examples": sorted(found, key=str.lower)[:EXAMPLES],
                      "notable": [k for k in ks if k in NOTABLE],
                      "output": is_output_mod(m, o, memo) if o.kind == "mod" else "",
                      "adding": fold(o.name) in adding and not o.enabled}
            (wins if o_priority < my_priority else loses).append(entry2)
        wins.sort(key=lambda e: -e["files"])
        loses.sort(key=lambda e: -e["files"])
        out_mods.append({"name": x.name, "priority": x.priority, "enabled": x.enabled, "listed": x.listed,
                         "staged": id(x) in waiting,
                         "files": len(files), "cut": cut, "kinds": kinds, "plugins": plugs,
                         "wins": wins, "loses": loses,
                         # A newer version of a mod of the modlist (MT40): which, where it goes, and whether the
                         # older one is enabled now and so is to be disabled when this one is added.
                         "updates": olds[fold(x.name)].name if fold(x.name) in olds else "",
                         "own_before": above(olds[fold(x.name)]) if fold(x.name) in olds else "",
                         "updates_enabled": bool(fold(x.name) in olds and olds[fold(x.name)].enabled),
                         # What the newer version differs in from the older one, by its files (MT49).
                         "differs": version_changes(olds[fold(x.name)].folder, x.folder, time.monotonic() + DIFFER_SECONDS)
                         if fold(x.name) in olds and olds[fold(x.name)].folder is not None else None})

    # The new plugins among themselves: masters' block first, then each after the masters that come along.
    entries = {fold(p["name"]): p for x in out_mods for p in x["plugins"]}

    def depth(p: dict, seen: frozenset = frozenset()) -> int:
        f = fold(p["name"])
        if f in seen:
            return 0
        deps = [entries[fold(mm["name"])] for mm in p["masters"] if mm["state"] == "comes along" and fold(mm["name"]) in entries]
        return 1 + max((depth(d, seen | {f}) for d in deps), default=-1)

    ranked = sorted(entries.values(), key=lambda p: (not is_master(p["kind"]), depth(p), fold(p["name"])))
    for i, p in enumerate(ranked):
        p["order"] = i

    slots = {"full": {"now": full_now, "after": full_now + full_add, "limit": FULL_SLOTS},
             "light": {"now": light_now, "after": light_now + light_add, "limit": LIGHT_SLOTS}}
    # An update (MT49): every mod of the batch is a newer version of a mod of the modlist. It takes the older one's
    # place and nothing of the modlist is judged anew; the tools are named only where the files they read changed.
    update = bool(out_mods) and all(x["updates"] for x in out_mods)
    new_kinds: set[str] = set()                # the kinds of records the new mods' plugins hold
    for x in cands:
        for pname in x.plugins:
            if x.folder is not None:
                try:
                    new_kinds |= plugin.groups(x.folder / pname)
                except plugin.Unreadable:
                    new_kinds.add("?")              # not read: taken to matter to every tool that reads plugins
    if update:
        differing: dict[str, int] = {}
        for x in out_mods:
            for k, n in ((x.get("differs") or {}).get("kinds") or {}).items():
                differing[k] = differing.get(k, 0) + n
        again = run_again(m, {k: n for k, n in differing.items() if k != "plugin"}, differing.get("plugin", 0), memo)
    else:
        again = run_again(m, kinds_all, new_plugins, memo, new_kinds)
    report = {"mods": out_mods, "place": place, "slots": slots, "tools": again, "cut": cut_any, "update": update,
              "unknown": [n for n in names if inst.mod(n) is None]}
    report["steps"] = compile_steps(m, report, auto)
    todo = [s for s in report["steps"] if s["state"] not in ("done", "not needed") and not s["manual"]]
    report["complete"] = bool(out_mods) and not todo
    report["summary"] = ("Nothing to analyse yet." if not out_mods else
                         ("The newer version is in place and the older one disabled." if update else
                          "Every step that files can prove is done.") if not todo else "%d step(s) to go." % len(todo))
    return report


def run_again(m: model.Model, kinds: dict[str, int], new_plugins: int, memo: dict, record_kinds: set[str] | None = None) -> list[dict]:
    """The tools whose output the new mods make stale: those that built a plugin of this modlist from what the
    mods bring (TL01, the tools data's 'reads'), and those fed by the mods' loose files (DESIGN§14).

    `record_kinds`, where given, are the kinds of records the new plugins hold (MT53). A tool that builds a plugin
    from the load order's plugins then counts only where its own output holds records of one of those kinds: a
    patch of characters has nothing to do with a plugin of quests and spells. A new plugin that could not be read
    ("?") counts for every such tool."""
    inst = m.instance
    brings = {k for k, n in kinds.items() if n}
    if new_plugins or kinds.get("plugin"):
        brings.add("plugins")
    data = {t["tool"]: t for t in tools.load()}
    found: dict[str, dict] = {}
    for f in m.order:
        r = m.plugins[f]
        if not r.active or r.source is None:
            continue
        for e in generated(m, r, memo):
            if e.kind == "section":
                continue                        # the list keeps it among its outputs, but which tool made it is not known
            t = data.get(e.tool, {})
            reads = t.get("reads", ["plugins"])            # a tool ModTrap does not know: taken to read plugins
            hit = [k for k in reads if k in brings]
            shared: list[str] = []
            if "plugins" in hit and record_kinds is not None and "?" not in record_kinds:
                try:
                    shared = sorted(plugin.groups(r.path) & record_kinds) if r.path is not None else ["?"]
                except plugin.Unreadable:
                    shared = ["?"]                     # its output could not be read: taken to matter
                if not shared:
                    hit = [k for k in hit if k != "plugins"]
            if not hit:
                continue
            entry = found.setdefault(e.tool, {"tool": e.tool, "plugins": [], "because": hit, "known": bool(t),
                                              "if": t.get("reads_if", "") if t else
                                              "if what it builds depends on the plugins in the load order",
                                              "titles": []})
            if r.name not in entry["plugins"]:
                entry["plugins"].append(r.name)
            for k in hit:
                if k not in entry["because"]:
                    entry["because"].append(k)
            entry.setdefault("records", [])
            entry["records"] = sorted(set(entry["records"]) | {k for k in shared if k != "?"})
    for e in inst.executables:
        tool, _ = tools.of_executable(e.title, e.binary)
        if tool in found and e.title not in found[tool]["titles"]:
            found[tool]["titles"].append(e.title)
    out = list(found.values())
    for kind in sorted(steps.TOOLS_FOR):
        if kinds.get(kind):
            out.append({"tool": "", "kind": kind, "count": kinds[kind], "titles": steps.tools_for(inst, kind),
                        "plugins": [], "because": [kind], "if": "", "known": True})
    return out


# --- the steps (DESIGN§16.7) ----------------------------------------------------------------------------------------

def _update_steps(m: model.Model, rep: dict, step, doer: str, auto: bool, held: bool) -> None:
    """The steps of an update (MT49): the newer version takes the older one's place, the older one is disabled, the
    plugins keep their places. What a new mod is judged for (its place among all mods, the files it shares, the
    records it overrides, the tools to run again, a look in the game) held for the older version and is not asked
    again; what the newer version changes is told, with the tools that read it, as something to know."""
    mods = rep["mods"]
    several = len(mods) > 1
    items, placed = [], True
    for x in mods:
        here = x["enabled"] and not x["updates_enabled"]
        placed = placed and here
        items.append({"text": "%s: %s, right after “%s”" % (x["name"], ("enabled, at priority %d" % x["priority"]) if x["enabled"] else "to enable", x["updates"]),
                      "mod": x["name"], "tag": "enabled" if x["enabled"] else "not in place yet", "cls": "good" if x["enabled"] else ""})
        items.append({"text": "“%s”, the older version: %s" % (x["updates"], "to disable; it is not deleted" if x["updates_enabled"] and not x["enabled"] else
                                                                  "still enabled beside the newer one: disable it in MO2" if x["updates_enabled"] else
                                                                  "disabled, and kept as it is"),
                      "mod": x["updates"], "tag": "enabled" if x["updates_enabled"] else "disabled",
                      "cls": "warn" if x["updates_enabled"] and x["enabled"] else "good" if not x["updates_enabled"] else ""})
        for p in x["plugins"]:
            keeps = p.get("keeps")
            if p["active"] or keeps:
                items.append({"text": "%s: %s" % (p["name"], "active, at position %s, the place it had" % p["position"] if p["active"] else
                                                   "keeps its place in the load order, position %s%s" % (keeps["position"], "" if keeps["active"] else " (not active there, as you have it)")),
                              "plugin": p["name"] if p["active"] else "", "tag": "keeps its place", "cls": "good"})
    step("update", doer, "Put the newer version%s in the older one's place" % ("s" if several else ""),
         "This is an update of a mod you have, not a new mod. The newer version goes right after the older one in "
         "MO2's list, the older one is disabled and not deleted, and the plugins keep their places in the load order. "
         "Nothing else of the modlist is judged anew: the place, the files it shares with other mods and the records "
         "it overrides are the older version's. Revert, in the list of what was added, puts the older version back." + (
             " “Install mod”, above, does all of it." if auto else " Started with --allow-changes, ModTrap does this itself (“Install mod”)."),
         "done" if placed else "waiting" if held else "to do", items)

    # A plugin the older version did not have has no place to keep: it is placed as a new plugin is.
    fresh = sorted(((x, p) for x in mods for p in x["plugins"] if not p["unreadable"] and not p["active"] and not p.get("keeps")),
                   key=lambda xp: xp[1].get("order", 0))
    if fresh:
        step("activate", doer, "Activate the plugin%s the newer version adds" % ("s" if len(fresh) > 1 else ""),
             "The older version had no plugin of that name, so there is no place to keep: it goes after every master it "
             "names, and before the plugins the modlist's tools made.",
             "waiting" if not placed or held else "to do",
             [{"text": "%s [%s]: to activate, %s (%s)" % (p["name"], p["kind"], ("directly before %s" % p["proposed"]["before"]) if p["proposed"]["before"]
                                                           else "at the end of the load order", p["proposed"]["why"]), "tag": "not active"} for _, p in fresh])

    # What the newer version changes: told, not asked.
    told = []
    for x in mods:
        d = x.get("differs")
        if not d:
            continue
        lead = "%s: " % x["name"] if several else ""
        if not (d["added"] or d["gone"] or d["changed"]):
            told.append({"text": lead + "every one of its %d file(s) has the older version's name and size." % d["same"], "tag": "same files", "cls": "good"})
            continue
        told.append({"text": lead + "%d file(s) are new, %d are gone, %d have another size, %d are the same by name and size%s." % (
            d["added"], d["gone"], d["changed"], d["same"], "; the comparing was cut short" if d["cut"] else "")})
        told.append({"text": lead + "what differs, by kind: " + ", ".join("%d %s" % (n, k if k != "plugin" else "plugin(s)")
                                                                           for k, n in sorted(d["kinds"].items(), key=lambda kv: (-kv[1], kv[0])))})
        for word, names in (("has another size", d["plugins"]["changed"]), ("is new", d["plugins"]["added"]), ("is gone", d["plugins"]["gone"])):
            for n in names[:8]:
                told.append({"text": "%s%s %s" % (lead, n, word), "tag": "plugin", "cls": "warn" if word != "has another size" else ""})
    tools_named = []
    for t in rep["tools"]:
        names = t["titles"] or ([t["tool"]] if t["tool"] else [])
        if names:
            tools_named.append("%s (%s)" % (" or ".join("“%s”" % n for n in names), ", ".join(t["because"])))
    if told:
        step("differs", "ModTrap", "What the newer version changes",
             "For you to know; nothing here is asked of you. Files are compared by name and size, their contents are not read.",
             "done", told,
             note=("Tools of this modlist read files that changed: %s. What they built still holds the older version's until they run "
                   "again: with the modlist's other outputs when you next rebuild them, or now if the mod misbehaves in the game." % "; ".join(tools_named))
             if tools_named else "Nothing that a tool of this modlist builds from has changed.")

    mine = {fold(p["name"]) for x in mods for p in x["plugins"]}
    issues = [i for i in m.issues if fold(i.plugin) in mine]
    step("health", "ModTrap", "Check the load order: no missing or inactive masters",
         "The same check as MO2's warning triangle, done on the modlist as it is on disk now.",
         "to do" if issues else "done" if placed and not fresh else "waiting",
         [{"text": "%s needs %s, which is %s" % (i.plugin, i.master, "not active" if i.what == "inactive" else "missing"),
           "plugin": i.plugin, "tag": "missing" if i.what == "missing" else "not active", "cls": "bad"} for i in issues[:50]])


def compile_steps(m: model.Model, rep: dict, auto: bool = False) -> list[dict]:
    out: list[dict] = []

    doer = "ModTrap" if auto else "you"                 # for what "Add it for me" carries out (WHY§58)

    def step(key: str, who: str, title: str, why: str, state: str, items: list | None = None, note: str = "",
             manual: bool = False) -> None:
        out.append({"key": key, "who": who, "title": title, "why": why, "state": state, "items": items or [],
                    "note": note, "manual": manual, "n": len(out) + 1})

    mods = rep["mods"]
    if not mods:
        return out
    place = rep["place"]
    several = len(mods) > 1

    # 0. Mods ModTrap has unpacked, which MO2 does not have yet.
    unpacked = [x for x in mods if x.get("staged")]
    if unpacked:
        step("install", "ModTrap", "Copy the unpacked mod%s into MO2's mods folder" % ("s" if len(unpacked) > 1 else ""),
             "ModTrap has unpacked %s in its own work folder and read %s there; MO2 does not have %s yet. “Install mod”, "
             "above, copies %s in and does every step below by itself." % (("them", "them", "them", "them") if len(unpacked) > 1 else ("it", "it", "it", "it")),
             "to do", [{"text": "%s: unpacked, %d file(s)" % (x["name"], x["files"]), "tag": "not in MO2 yet"} for x in unpacked])

    # 1. What the mods need.
    needs: list[dict] = []
    for x in mods:
        for p in x["plugins"]:
            if p["unreadable"]:
                needs.append({"text": "%s could not be read: %s" % (p["name"], p["unreadable"]), "tag": "unreadable",
                              "cls": "bad", "plugin": p["name"]})
            for mm in p["masters"]:
                if mm["state"] == "missing":
                    needs.append({"text": "%s needs %s, which no mod in this MO2 has. Get the mod that provides it "
                                          "and install it in MO2." % (p["name"], mm["name"]), "tag": "missing", "cls": "bad"})
                elif mm["state"] == "disabled mod":
                    needs.append({"text": "%s needs %s, which is in a disabled mod: %s. Add that mod here too." % (
                        p["name"], mm["name"], " or ".join(mm["mods"])), "tag": "disabled", "cls": "warn",
                        "mod": mm["mods"][0], "add": mm["mods"][0]})
                elif mm["state"] == "inactive":
                    needs.append({"text": "%s needs %s, which is in the modlist but not active. Activate it on MO2's "
                                          "Plugins tab." % (p["name"], mm["name"]), "tag": "not active", "cls": "warn"})
    for which, word in (("full", "full"), ("light", "light")):
        s = rep["slots"][which]
        if s["after"] > s["limit"]:
            needs.append({"text": "The game loads at most %d %s plugins; with %s the modlist would have %d. Make room "
                                  "first (a plugin flagged light does not use a full place)." % (
                                      s["limit"], word, "these mods" if several else "this mod", s["after"]),
                          "tag": "no room", "cls": "bad"})
    step("needs", "you", "Get what %s" % ("the mods need" if several else "the mod needs"),
         "A plugin loads only when every master it names is there and active. Sorting this out before the mod is "
         "enabled keeps MO2's warning triangle away.",
         "to do" if needs else "done", needs,
         note="" if needs else "Every master is in the modlist and active, and there is room in the load order.")

    if rep.get("update"):
        _update_steps(m, rep, step, doer, auto, bool(needs or unpacked))
        for i, st in enumerate(out):
            st["n"] = i + 1
        return out

    # 2. The mod's place.
    off = [x for x in mods if not x["enabled"]]
    where = ("directly before “%s” in MO2's list" % place["before"]) if place["before"] else \
        "last in MO2's list (the highest priority)"
    items = [{"text": "%s: %s" % (x["name"], ("enabled, at priority %d" % x["priority"]) if x["enabled"]
                                    else "to enable, " + where), "mod": x["name"],
              "tag": "enabled" if x["enabled"] else "disabled", "cls": "good" if x["enabled"] else ""} for x in mods]
    step("enable", doer, "Put %s in its place in MO2's list, and enable it" % ("the mods" if several else "the mod"),
         ("The place you chose: %s." % where) if place.get("chosen") else
         "Last: after every ordinary mod in MO2's list (so it wins the files it shares with them), and before what the "
         "modlist's tools made, which stays last and is made again by the tools. That is where MO2 itself puts a new "
         "mod; “Manual placement” puts it anywhere else.",
         "done" if not off else "waiting" if needs or unpacked else "to do", items,
         note=("The modlist keeps its outputs under the heading “%s”: the mod goes right before that heading, and "
               "the %d mod(s) under it, with whatever the list keeps after them, stay after it." % (
                   place["heading"].replace("_separator", ""), len(place["outputs"]))) if place.get("heading") else
         ("Taken as tools' output, staying after it: " + ", ".join("%s (%s)" % (o["mod"], o["why"])
                                                                   for o in place["outputs"][:6])) if place["outputs"] else
         "No tool's output was recognised at the end of MO2's list, so the mod goes last.")

    # 3. Its plugins.
    plugs = sorted(((x, p) for x in mods for p in x["plugins"] if not p["unreadable"]), key=lambda xp: xp[1].get("order", 0))
    if plugs:
        items = []
        for x, p in plugs:
            pr = p["proposed"]
            spot = ("directly before %s" % pr["before"]) if pr["before"] else "at the end of the load order"
            keeps = p.get("keeps")
            if p["active"]:
                text = "%s: active, at position %s" % (p["name"], p["position"])
            elif keeps:
                text = "%s: keeps the older version's place in the load order, position %s%s" % (
                    p["name"], keeps["position"], "" if keeps["active"] else " (not active there, as you have it)")
            else:
                text = "%s [%s]: to activate, %s (%s)" % (p["name"], p["kind"], spot, pr["why"])
            items.append({"text": text, "plugin": p["name"] if p["active"] else "",
                          "tag": "active" if p["active"] else "keeps its place" if keeps else "not active",
                          "cls": "good" if p["active"] or keeps else ""})
            for n in p["notes"]:
                items.append({"text": n, "tag": "note", "cls": "warn"})
        inactive = [p for _, p in plugs if not p["active"] and not p.get("keeps")]
        step("activate", doer, "Activate the new plugin%s, in the right place" % ("s" if len(plugs) > 1 else ""),
             "After every master it names, and before the plugins the modlist's tools made: those are built from "
             "everything above them and are meant to stay last. Placed there, the new plugin wins over the plugins "
             "made by hand, as it does when you put it last; the step on records below shows what that overrides. In "
             "MO2: Plugins tab, tick the plugin and drag it to its place." + (
                 " “Install mod”, above, does this too." if auto else
                 " Started with --allow-changes, ModTrap does this itself (“Install mod”)."),
             "done" if not inactive else "waiting" if off or needs else "to do", items)

    # 4. What it overwrites, and what overwrites it: told, not asked (MT53).
    told, total_w, total_l = [], 0, 0
    for x in mods:
        lead = "%s: " % x["name"] if several else ""
        for word, lst in (("overwrites", x["wins"]), ("is overwritten by", x["loses"])):
            for c in lst:
                n = c["files"]
                if word == "overwrites":
                    total_w += n
                else:
                    total_l += n
                kinds = ", ".join("%d %s" % (k, name) for name, k in sorted(c["kinds"].items(), key=lambda kv: (-kv[1], kv[0]))[:5])
                told.append({"text": "%s%s “%s” in %d file(s): %s%s" % (lead, word, c["mod"], n, kinds,
                                                                         "; a tool made that mod's files, and makes them again when it runs" if word != "overwrites" and c["output"] else ""),
                             "mod": c["mod"], "tag": c["notable"][0] if c["notable"] else "", "cls": "warn" if c["notable"] else ""})
                for k in c["notable"]:
                    told.append({"text": "  %s" % NOTABLE[k], "tag": k, "cls": "warn"})
    for x in mods:
        for p in x["plugins"]:
            r = p.get("replaces")
            if r:
                told.append({"text": "%s is also in “%s”: this mod's copy would be the one MO2 uses. %d plugin(s) "
                                     "name it as a master and were made for the other copy." % (p["name"], r["mod"], r["dependants"]),
                             "mod": r["mod"], "tag": "same plugin", "cls": "warn"})
    where_word = "where you put it" if place.get("chosen") else "placed last, before the tools' outputs"
    step("files", "ModTrap", "What it overwrites, and what overwrites it",
         "Where two mods have a file of the same name, MO2 uses the one of the mod with the higher priority. For you to "
         "know; nothing here is asked of you. “Manual placement” puts the mod elsewhere and shows the same for that place.",
         "done", told[:160],
         note=("%s, it overwrites %d file(s) of other mods and %d of its own are overwritten." % (where_word[:1].upper() + where_word[1:], total_w, total_l))
         if told else "%s, it shares no file with any other mod: nothing is overwritten either way." % (where_word[:1].upper() + where_word[1:]))

    # 5. Records: an optional look through xEdit, never a step to tick.
    if plugs:
        step("records", "ModTrap", "Optional: what the new plugin%s in other plugins' records" % ("s override" if len(plugs) > 1 else " overrides"),
             "Two plugins that change the same record do not add up: the later one wins the whole record. Only xEdit can "
             "read which records: ModTrap starts yours through MO2 with a script that only reads, and lists the records "
             "the new plugin takes from others and those it loses. Not needed to install the mod.",
             "not needed")

    # 6. The tools that have to do with it: told, not asked; only where what they build from is touched (MT53).
    tool_items = []
    for t in rep["tools"]:
        names = t["titles"]
        if t["tool"]:
            why = []
            if t.get("records"):
                why.append("its output (%s) holds records of kinds this mod's plugin also has: %s" % (
                    ", ".join(t["plugins"][:3]) + (" and others" if len(t["plugins"]) > 3 else ""), ", ".join(t["records"][:8])))
            elif "plugins" in t["because"]:
                why.append("it builds %s from the load order's plugins" % (", ".join(t["plugins"][:3]) + (" and others" if len(t["plugins"]) > 3 else "")))
            files = [k for k in t["because"] if k != "plugins"]
            if files:
                why.append("it builds from the mod's %s" % " and ".join(files))
            text = "%s: %s%s" % (t["tool"], "; ".join(why), (" (it applies %s)" % t["if"]) if t["if"] else "")
        else:
            text = "%s: the mod brings %d file(s) of %s, which such a tool builds its output from" % (
                " or ".join("“%s”" % n for n in names) if names else "the tool that handles " + t["kind"], t["count"], t["kind"])
        tool_items.append({"text": text, "tag": "tool"})
        for n in names:
            tool_items.append({"text": "“%s” in MO2's list of tools" % n, "start": n})
    step("tools", "ModTrap", "The tools that have to do with this mod",
         "A tool's output holds the modlist as it was when the tool last ran. Named here are only the tools that build "
         "from something this mod brings: a plugin with records of the kinds the tool's own output holds, or files of "
         "the kinds the tool reads. Run them when you next rebuild the modlist's outputs, or now if what the mod adds is "
         "missing in the game; nothing here has to be ticked.",
         "done", tool_items,
         note="" if tool_items else "None of the modlist's tools builds from anything this mod brings.")

    # 7. Health.
    mine = {fold(p["name"]) for x in mods for p in x["plugins"]}
    issues = [i for i in m.issues if fold(i.plugin) in mine]
    all_in = not off and all(p["active"] for _, p in plugs)
    step("health", "ModTrap", "Check the load order: no missing or inactive masters",
         "The same check as MO2's warning triangle, done on the modlist as it is on disk now. Press Rescan after "
         "changing something in MO2.",
         "to do" if issues else "done" if all_in else "waiting",
         [{"text": "%s needs %s, which is %s" % (i.plugin, i.master, "not active" if i.what == "inactive" else "missing"),
           "plugin": i.plugin, "tag": "missing" if i.what == "missing" else "not active", "cls": "bad"} for i in issues[:50]],
         note=("%d problem(s) elsewhere in the modlist have nothing to do with %s." % (
             len(m.issues) - len(issues), "these mods" if several else "this mod")) if len(m.issues) > len(issues) else "")
    return out


__all__ = ["analyse", "resolve", "installed_from", "shared_files", "mod_place", "tail_start", "run_again",
           "compile_steps", "FULL_SLOTS", "LIGHT_SLOTS"]
