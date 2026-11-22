"""The dry run (DESIGN§6.1, DESIGN§6.2): the plan, starting the owner's xEdit through MO2 with ModTrap's script in
report mode, following its progress, and reading its report. Nothing in the instance is changed: the script only
reads, and everything ModTrap writes goes into the job's own folder under ModTrap's work folder.

The command line facts are in MO01§3 and XE01§2 to XE01§6; what a run on the owner's PC still has to show is in
WHY§31.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from . import logbook, model, paths, process, tools, winauto
from .instance import GAME, Executable, Instance, fold

SCRIPT = Path(__file__).resolve().parent / "xedit" / "ModTrap.pas"
MO2_EXE = "ModOrganizer.exe"
# The program files xEdit goes by for Skyrim SE, the 64-bit ones first (WHY§14).
XEDIT_NAMES = ("sseedit64.exe", "xedit64.exe", "sseedit.exe", "xedit.exe")
TIME_LIMIT = 60 * 60            # seconds a dry run may take before ModTrap gives up waiting
START_LIMIT = 20 * 60           # seconds xEdit may take to load before the script's first line
GONE_GRACE = 8                  # seconds xEdit must be gone, with no end line in the report, to count as closed
# Arrays whose entries can be taken out without changing what the rest of the record means (MT4, case B): by the
# record's signature ("*" for any) and the list's name as xEdit gives it. LIKELY until the first real report shows
# xEdit's exact names (WHY§31); the report carries every name, so the list can be corrected without a new script.
SAFE_ARRAYS = (("FLST", "FormIDs"), ("LVLI", "Leveled List Entries"), ("LVLN", "Leveled List Entries"),
               ("LVSP", "Leveled List Entries"), ("*", "KWDA - Keywords"),
               # A script's property that points at a record of the mod, and one object in a property that is a
               # list of objects (XE01§21): with the property gone the script finds nothing there, as it would
               # with the mod gone and the property left dangling. Named so in the plan (WHY§76).
               ("*", "Properties"), ("*", "Array of Object"))
SCRIPT_ARRAYS = ("Properties", "Array of Object")

log = logbook.get("dryrun")


class Refused(Exception):
    """The dry run cannot be planned or started; the text says why, in words for the page."""


@dataclass
class Plan:
    trapped_mods: list[str]
    trapped: list[str]              # trapped plugins, in load order
    dependants: list[str]           # dependant plugins, in load order
    load: list[str]                 # every plugin xEdit is to load, in load order
    mo2: str                        # ModOrganizer.exe
    profile: str
    tool: str                       # the executable's title in MO2
    tool_binary: str
    warnings: list[str] = field(default_factory=list)
    tool_args: str = ""             # the arguments MO2 has for this executable: kept, since `-a` replaces them
    data_dir: str = ""              # the game's Data folder as MO2 manages it: where xEdit must look (XE01§11)

    def public(self) -> dict:
        return {"trapped_mods": self.trapped_mods, "trapped": self.trapped, "dependants": self.dependants,
                "load": len(self.load), "load_names": self.load, "profile": self.profile, "tool": self.tool,
                "tool_file": Path(self.tool_binary.replace("\\", "/")).name, "warnings": self.warnings}


# Switches of an executable's own arguments that ModTrap's run must not inherit (XE01§2, XE01§11): the ones it sets
# itself, and the ones that put xEdit into another mode.
OWN_SWITCHES = frozenset(("script", "p", "b", "r", "autoload", "autoexit", "quickclean", "qc", "quickautoclean", "qac",
                          "quickshowconflicts", "qsc", "veryquickshowconflicts", "vqsc", "autogamelink", "agl",
                          "quickedit", "nobuildrefs"))
_MODE_WORDS = ("quickautoclean", "quickclean", "qac", "quickshowconflicts", "qsc", "vqsc", "autogamelink")


def split_arguments(text: str) -> list[str]:
    """An argument string as its parts: split at spaces that are not inside double quotes; the quotes are kept."""
    out, cur, quoted = [], "", False
    for ch in text:
        if ch == '"':
            quoted = not quoted
        if ch.isspace() and not quoted:
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def switch_name(part: str) -> str:
    """The name of a switch such as -D:"..." or /IgnoreESL, lower case; "" for something that is not a switch."""
    if not part or part[0] not in "-/":
        return ""
    return re.split(r"[:=]", part[1:], maxsplit=1)[0].strip().lower()


def find_xedit_exe(inst: Instance) -> Executable:
    """The xEdit set up in MO2, as MO2 has it. The 64-bit one first; of several entries for the same program, one
    whose own arguments or title do not put xEdit into a cleaning or comparing mode."""
    by_name: dict[str, list[Executable]] = {}
    for e in inst.executables:
        by_name.setdefault(fold(Path(e.binary.replace("\\", "/")).name), []).append(e)
    for name in XEDIT_NAMES:
        found = by_name.get(name)
        if found:
            plain = [e for e in found if not any(w in (e.arguments + " " + e.title).lower().replace(" ", "") for w in _MODE_WORDS)
                     and not any(switch_name(x) in _MODE_WORDS for x in split_arguments(e.arguments))]
            return (plain or found)[0]
    raise Refused("no xEdit is set up as an executable in this MO2 (looked for SSEEdit64.exe, xEdit64.exe, "
                  "SSEEdit.exe and xEdit.exe)")


def find_xedit(inst: Instance) -> tuple[str, str]:
    """The xEdit set up in MO2: (its title, its program file)."""
    e = find_xedit_exe(inst)
    return e.title, e.binary


def data_dir_of(inst: Instance) -> str:
    """The game's Data folder as MO2 manages it, or "" when MO2's settings do not name the game's folder."""
    return str(inst.game_dir / "Data") if inst.game_dir is not None else ""


def plan(m: model.Model, mod_names: list[str]) -> Plan:
    inst = m.instance
    if not mod_names:
        raise Refused("tick at least one mod")
    trapped: dict[str, model.PluginRow] = {}
    mods = []
    for name in mod_names:
        mod = inst.mod(name)
        if mod is None or mod.kind != "mod":
            raise Refused("'%s' is not a mod of this profile" % name)
        if not mod.enabled:
            raise Refused("'%s' is disabled: a mod must be enabled while it is demastered, so that xEdit can load "
                          "its plugins" % mod.name)
        mods.append(mod.name)
        for r in m.provided_by(mod):
            trapped[fold(r.name)] = r
    if not trapped:
        raise Refused("the ticked mods provide no plugin: there is nothing to demaster")
    deps: dict[str, model.PluginRow] = {}
    for r in trapped.values():
        if r.primary or r.source == GAME:
            raise Refused("%s is one of the game's own plugins" % r.name)
        for d in r.dependants:
            if fold(d) not in trapped:
                deps[fold(d)] = m.plugins[fold(d)]
    if not deps:
        raise Refused("nothing depends on the ticked mods' plugins: they can be disabled in MO2 as they are")
    warnings: list[str] = []
    for r in deps.values():
        if r.primary or r.source == GAME:
            raise Refused("%s, one of the game's own plugins, depends on a ticked mod; ModTrap never changes the "
                          "game's files" % r.name)
        if not r.active:
            warnings.append("%s is not active in the load order; it is read all the same" % r.name)
    # Everything xEdit must load: the dependants and every master under them (XE01§3).
    need: dict[str, model.PluginRow] = {}
    stack = list(deps.values())
    while stack:
        r = stack.pop()
        if fold(r.name) in need:
            continue
        need[fold(r.name)] = r
        for name in r.masters:
            mr = m.plugins.get(fold(name))
            if mr is None or mr.source is None:
                raise Refused("%s needs %s, which no enabled mod provides: fix that in MO2 first (see the Health tab)"
                              % (r.name, name))
            stack.append(mr)
    order = [m.plugins[f] for f in m.order if f in need]
    exe = find_xedit_exe(inst)
    mo2 = inst.root / MO2_EXE
    return Plan(trapped_mods=mods, trapped=[r.name for r in order if fold(r.name) in trapped],
                dependants=[r.name for r in order if fold(r.name) in deps], load=[r.name for r in order],
                mo2=str(mo2), profile=inst.profile, tool=exe.title, tool_binary=exe.binary, warnings=warnings,
                tool_args=exe.arguments, data_dir=data_dir_of(inst))


# --- the job's folder ---------------------------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(m: model.Model, p: Plan, job_dir: Path) -> dict:
    """Writes the job's folder: the script and its job file, the plugins file for xEdit, and a copy and a sha256
    of every dependant as it is now. Returns the manifest. Writes nothing outside `job_dir`."""
    script_dir, safe = job_dir / "script", job_dir / "safe"
    script_dir.mkdir(parents=True)
    safe.mkdir()
    shutil.copyfile(SCRIPT, script_dir / SCRIPT.name)
    report, progress = job_dir / "report.tsv", job_dir / "progress.txt"
    lines = ["format=modtrap-job/1", "mode=report", "out=%s" % report, "progress=%s" % progress,
             "trap.count=%d" % len(p.trapped)]
    lines += ["trap.%d=%s" % (i, n) for i, n in enumerate(p.trapped)]
    lines += ["dep.count=%d" % len(p.dependants)] + ["dep.%d=%s" % (i, n) for i, n in enumerate(p.dependants)]
    # The plugins whose own changes the script is to tell: the trapped ones, and the patches made for them
    # (WHY§52, WHY§66). What a tool's output may carry of the mod is judged from that.
    game = {fold(x) for x in m.instance.primary} | {fold(x) for x in p.trapped}
    touch = list(p.trapped)
    for name in p.dependants:
        r = m.plugins.get(fold(name))
        if r is not None and len([x for x in r.masters if fold(x) not in game]) <= PARTNERS \
                and named_for(name, p.trapped, p.trapped_mods):
            touch.append(name)
    lines += ["touch.count=%d" % len(touch)] + ["touch.%d=%s" % (i, n) for i, n in enumerate(touch)]
    # The plugins a tool made: they have no say in which version of a record wins, so that the script can tell
    # where the leaving plugins have the last word among the others (XE01§19, WHY§69).
    binaries = {e.title: e.binary for e in m.instance.executables}
    made = [r.name for r in (m.plugins[f] for f in m.order)
            if r.active and r.source is not None and fold(r.name) not in game
            and any(e.kind != "editor" for e in tools.identify(r.name, r.author, r.source, m.instance.output_mods, binaries))]
    lines += ["made.count=%d" % len(made)] + ["made.%d=%s" % (i, n) for i, n in enumerate(made)]
    # With a byte-order mark: the script's string list then reads the file as UTF-8, whatever the PC's own text
    # encoding, so a folder name with letters outside it still arrives whole (WHY§34).
    paths.write_atomic(script_dir / "modtrap-job.txt", ("\r\n".join(lines) + "\r\n").encode("utf-8-sig"))
    primary = {fold(x) for x in m.instance.primary}
    listed = ["*" + n for n in p.load if fold(n) not in primary]
    try:
        text = ("\r\n".join(listed) + "\r\n").encode("mbcs" if os.name == "nt" else "cp1252")
    except UnicodeEncodeError:
        raise Refused("a plugin's name cannot be written in this PC's text encoding, which xEdit's plugin list "
                      "needs") from None
    paths.write_atomic(job_dir / "plugins.txt", text)
    files = []
    for name in p.dependants:
        r = m.plugins[fold(name)]
        assert r.path is not None
        shutil.copy2(r.path, safe / r.name)
        digest = _sha256(r.path)
        if _sha256(safe / r.name) != digest:
            raise Refused("the copy of %s in the job's safe folder does not match the original" % r.name)
        st = r.path.stat()
        files.append({"name": r.name, "mod": r.source, "mod_priority": r.source_priority, "position": r.position,
                      "kind": r.kind, "size": st.st_size, "sha256": digest})
    manifest = {"format": "modtrap-dryrun/1", "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "profile": p.profile,
                "trapped_mods": p.trapped_mods, "trapped": p.trapped, "dependants": files, "load": p.load,
                "tool": p.tool}
    paths.write_atomic(job_dir / "manifest.json", (json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    return manifest


def arguments(job_dir: Path, script: str = SCRIPT.name, own: str = "", data_dir: str = "") -> str:
    """xEdit's arguments (XE01§2 to XE01§6, XE01§11). MO2's `-a` replaces the executable's own arguments, so those
    are carried over, less the switches ModTrap sets itself and the ones that would put xEdit into another mode.
    Then: the game's Data folder as MO2 manages it, unless the executable's own arguments already name one (without
    it xEdit looks up the game in the registry, which need not be the folder MO2 fills); our script, our plugin
    list, backups and a log in the job's folder; no reference building, which a report does not need."""
    q = lambda p: '"%s"' % p                                   # noqa: E731
    kept = [x for x in split_arguments(own) if switch_name(x) not in OWN_SWITCHES and switch_name(x) != ""]
    names = {switch_name(x) for x in kept}
    parts = list(kept)
    if not (names & {"sse", "tes5", "tes5vr", "enderal", "enderalse", "fo4", "fo4vr", "fnv", "fo3", "tes4", "sf1"}):
        parts.append("-sse")
    if "d" not in names and data_dir:
        parts.append("-D:" + q(str(data_dir).rstrip("\\/")))     # no closing slash: before a quote it would escape it
    parts += ["-script:" + q(job_dir / "script" / script), "-P:" + q(job_dir / "plugins.txt"), "-nobuildrefs",
              "-B:" + q(job_dir / "xedit-backups"), "-R:" + q(job_dir / "xedit-log.txt")]
    return " ".join(parts)


def command(p: Plan, job_dir: Path, script: str = SCRIPT.name) -> list[str]:
    """MO2's command to run a configured executable in its virtual file system with our arguments (MO01§3)."""
    return [p.mo2, "-p", p.profile, "run", "-e", "-a", arguments(job_dir, script, p.tool_args, p.data_dir), p.tool]


# --- the report ---------------------------------------------------------------------------------------------------

ARRAY_ELEMENTS = ("etArray", "etSubRecordArray")      # xEdit's names for an element that is a list
ARRAY_VALUES = ("dtArray", "dtSubRecordArray")         # and for a value that is one (a list inside one field)


def _safe_array(signature: str, array_name: str, script_props: bool = True) -> bool:
    if not script_props and array_name.strip() in SCRIPT_ARRAYS:
        return False                                  # the owner's setting: script properties are left to them
    return any((sig in ("*", signature)) and array_name.strip() == name for sig, name in SAFE_ARRAYS)


def read_chain(text: str) -> dict:
    """What the script's chain says about one element (XE01§7, WHY§34): is it, or something above it, an entry of
    a list; and which list, and how long. The chain runs from the element up to its record; a step is "name,
    element kind, value kind, how many elements it holds, its place in the step above"."""
    steps = []
    for item in text.split("\x1e"):
        parts = item.split("\x1f")
        if len(parts) >= 5:
            steps.append({"name": parts[0], "element": parts[1], "value": parts[2],
                          "count": int(parts[3]) if parts[3].lstrip("-").isdigit() else 0,
                          "index": int(parts[4]) if parts[4].lstrip("-").isdigit() else -1})
    for i in range(len(steps) - 1):
        above = steps[i + 1]
        if above["element"] in ARRAY_ELEMENTS or above["value"] in ARRAY_VALUES:
            # How to reach the entry from its record: the place of each step in the one above it, top down.
            route = [st["index"] for st in reversed(steps[i:])]
            return {"kind": "entry", "entry": steps[i]["name"], "index": steps[i]["index"], "array": above["name"],
                    "array_length": above["count"], "steps": steps, "route": route if min(route) >= 0 else []}
    return {"kind": "field", "entry": "", "index": -1, "array": "", "array_length": 0, "steps": steps, "route": []}


PARTNERS = 2        # a patch for the mod: at most this many masters besides the game's own and the trapped ones


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _initials(name: str) -> set[str]:
    """The first letters of a name's words, read two ways: words as written, and words as capitals begin them."""
    words = [re.sub(r"[^A-Za-z0-9]", "", w) for w in re.split(r"[\s_]+", name)]
    plain = "".join(w[0] for w in words if w)
    camel = "".join(w[0] for w in re.findall(r"[A-Z]+[a-z0-9]*|[a-z0-9]+", name))
    return {x.lower() for x in (plain, camel) if len(x) >= 3}


def named_for(dependant: str, trapped: Iterable[str], trapped_mods: Iterable[str]) -> bool:
    """Is a plugin named after a trapped mod, as patches are ("Inn - Lantern Patch.esp", "LNT_Inn.esp")? Its name
    holds the trapped plugin's or the mod's whole name, or their initials as a word of its own."""
    stem = dependant.rsplit(".", 1)[0]
    flat, words = _squash(stem), {w for w in re.split(r"[^a-z0-9]+", stem.lower()) if w}
    for name in [t.rsplit(".", 1)[0] for t in trapped] + list(trapped_mods):
        if len(_squash(name)) >= 4 and _squash(name) in flat:
            return True
        if _initials(name) & words:
            return True
    return False


LISTS = ("etSubRecordArray", "etArray")


def resolve_part(key: tuple[str, str, str], hard: list[dict], parts: dict, entries: dict, gone: set[str],
                 sources: set[str], settled: dict) -> tuple:
    """What ModTrap does about one part of a record (one of the record's direct elements) that needs a trapped
    plugin and is not simply a list that may be shortened (MT4's case C; XE01§14, WHY§55). `hard` are the
    elements of that part that need the owner so far. The answer is kept in `settled` for the dependants that
    load later and carry the same part on.

    ("put back", plugin)  the dependant's version of the part is that of a plugin that goes (a trapped plugin, or
                          a patch that is switched off): the part is put back as the dependant's last master
                          that does not need the mod has it
    ("take out", plugin)  the same, where that master has no such part
    ("entries",)          the part is a list, and each entry that needs the mod is also in an earlier plugin's
                          version of the list (the dependant did not write it): those entries are taken out
    ()                    none of these: it needs the owner"""
    if key in settled:
        return settled[key]
    settled[key] = ()                                   # until known; also ends a chain that comes back on itself
    file, form, name = key
    part = parts.get(key)
    answer: tuple = ()
    if part:
        same = fold(part["same"])
        back = ("put back" if part["state"] == "present" else "take out", part["prev"]) \
            if part["prev"] and part["state"] in ("present", "absent") else ()
        if same in gone and back:
            answer = back
        elif same in sources and same not in gone:      # the same as an earlier dependant that is itself demastered
            theirs = settled.get((part["same"], form, name), ())
            if theirs and theirs[0] in ("put back", "take out") and theirs == back:
                answer = back                           # both go back to the same plugin's version
        if not answer and part["element"] in LISTS and hard:
            ok = True
            for e in hard:
                g = entries.get((file, form, name, e["route"][-1])) if len(e.get("route") or []) == 2 else None
                if e["kind"] != "entry" or e["array"] != name or not g or fold(g["src"]) not in sources or g["breaks"]:
                    ok = False
                    break
            if ok:
                answer = ("entries",)
    settled[key] = answer
    return answer


def parse_report(text: str, trapped: Iterable[str] = (), trapped_mods: Iterable[str] = (),
                 primary: Iterable[str] = (), script_props: bool = True) -> dict:
    """The script's report as the page shows it: per dependant, what needs a trapped plugin and what ModTrap would
    do about each (MT4): "record" (the dependant's copy of a trapped plugin's own record: taken out), "entry" (an
    entry of a list that is safe to shorten: taken out), "needs you" (anything else).

    With the trapped plugins and mods named, a dependant that is a patch for the mod by its masters and its name
    is read as "patch only" whatever it holds (MT6, WHY§52), and each part that needs the owner says whether the
    dependant only carries it on from the mod (reported, not yet acted on: MT4)."""
    trapped, trapped_mods = list(trapped), list(trapped_mods)
    game = {fold(x) for x in primary} | {fold(x) for x in trapped}
    out: dict = {"format": "", "xedit": "", "end": "", "reason": "", "files": [], "not_loaded": [], "held_changed": [],
                 "data_path": "", "trap_missing": [], "loaded": 0,
                 # what each looked-through plugin really changes, by xEdit's own comparison (XE01§18): plugin ->
                 # [{"form", "kind", "owner", "fields"}]; a plugin is a key only if the script looked through it
                 "touched": {},
                 # how many records each looked-through plugin changes at all (a stake is narrower, XE01§19)
                 "changes": {}}
    touched_rows: dict[str, list[dict]] = {}
    changed_rows: dict[str, int] = {}
    files: dict[str, dict] = {}
    records: dict[tuple[str, str], dict] = {}
    parts: dict[tuple[str, str, str], dict] = {}
    entries: dict[tuple[str, str, str, int], dict] = {}
    for line in text.split("\n"):              # not splitlines(): the chain's separators would count as line ends
        f = line.rstrip("\r").split("\t")
        kind = f[0]
        if kind == "H" and len(f) >= 4:
            out["format"], out["xedit"] = f[1], f[3]
        elif kind == "F" and len(f) >= 4:
            files[f[1]] = {"name": f[1], "records": int(f[2] or 0), "masters": [x for x in f[3].split(",") if x],
                           "needing": 0, "done": False, "own": 0, "entries": 0, "needs_you": 0, "items": []}
            out["files"].append(files[f[1]])
        elif kind == "R" and len(f) >= 7 and f[1] in files:
            rec = {"signature": f[2], "form": f[3], "belongs_to": f[4], "own": f[5] == "1", "editor_id": f[6],
                   "elements": []}
            records[(f[1], f[3])] = rec
            files[f[1]]["items"].append(rec)
        elif kind == "E" and len(f) >= 7 and (f[1], f[2]) in records:
            rec = records[(f[1], f[2])]
            c = read_chain(f[6])
            safe = c["kind"] == "entry" and _safe_array(rec["signature"], c["array"], script_props)
            rec["elements"].append({"kind": c["kind"], "entry": c["entry"], "index": c["index"], "array": c["array"],
                                    "array_length": c["array_length"], "path": f[3], "target_file": f[4],
                                    "target_form": f[5], "would": "entry" if safe else "needs you",
                                    "route": c["route"], "part": c["steps"][-1]["name"] if c["steps"] else "",
                                    "chain": [[st["name"], st["element"], st["value"], st["count"]]
                                              for st in c["steps"]]})
        elif kind == "C" and len(f) >= 10:
            parts[(f[1], f[2], f[3])] = {"part": f[3], "element": f[4], "same": f[5], "prev": f[6], "state": f[7],
                                         "tainted": int(f[8] or 0), "rest_same": f[9] == "1"}
        elif kind == "G" and len(f) >= 7 and f[4].isdigit():
            entries[(f[1], f[2], f[3], int(f[4]))] = {"src": f[5], "breaks": f[6] == "1"}
        elif kind == "T" and len(f) >= 6:
            changed_rows[f[1]] = changed_rows.get(f[1], 0) + 1
        elif kind == "W" and len(f) >= 6:
            touched_rows.setdefault(f[1], []).append({"form": f[2], "kind": f[3], "owner": f[4],
                                                      "fields": sorted({x for x in f[5].split(",") if x})})
        elif kind == "V" and len(f) >= 4:
            # Only a script that tells stakes (W) is believed: an earlier one told every change, and a tool that
            # holds a value many plugins share was then asked to run again for nothing (WHY§69).
            out["touched"][f[1]] = touched_rows.get(f[1], [])
            out["changes"][f[1]] = changed_rows.get(f[1], 0)
        elif kind == "D" and len(f) >= 4 and f[1] in files:
            files[f[1]]["needing"], files[f[1]]["done"] = int(f[3] or 0), True
        elif kind == "M" and len(f) >= 2:
            out["not_loaded"].append(f[1])
        elif kind == "N" and len(f) >= 2:
            out["trap_missing"].append(f[1])
        elif kind == "P" and len(f) >= 2:
            out["data_path"] = f[1]
            out["loaded"] = int(f[2]) if len(f) > 2 and f[2].isdigit() else 0
        elif kind == "U" and len(f) >= 2:
            out["held_changed"].append(f[1])
        elif kind == "X" and len(f) >= 2:
            out["end"], out["reason"] = f[1], f[2] if len(f) > 2 else ""
    sources = {fold(x) for x in trapped} | {fold(n) for n in files}
    for fd in files.values():
        partners = [x for x in fd["masters"] if fold(x) not in game]
        fd["made_for"] = bool(trapped) and len(partners) <= PARTNERS and named_for(fd["name"], trapped, trapped_mods)
    gone = {fold(x) for x in trapped} | {fold(n) for n, fd in files.items() if fd["made_for"]}
    settled: dict = {}
    for fd in out["files"]:                             # in load order: a later dependant may carry an earlier one on
        fd["parts"] = 0
        for rec in fd["items"]:
            if rec["own"]:
                rec["would"] = "record"
                fd["own"] += 1
                continue
            by_part: dict[str, list[dict]] = {}
            for e in rec["elements"]:
                if e["would"] == "needs you":
                    by_part.setdefault(e["part"], []).append(e)
            for name, hard in by_part.items():
                key = (fd["name"], rec["form"], name)
                answer = resolve_part(key, hard, parts, entries, gone, sources, settled)
                part = parts.get(key)
                for e in hard:
                    if part:
                        e["same_as"], e["without"], e["without_state"] = part["same"], part["prev"], part["state"]
                    if answer and answer[0] == "entries":
                        e["would"], e["came"] = "entry", "added"
                    elif answer:
                        e["would"], e["came"], e["action"], e["from"] = "part", "carried", answer[0], answer[1]
                    else:
                        e["came"] = ""
                if answer and answer[0] != "entries":
                    fd["parts"] += 1
            kinds = {e["would"] for e in rec["elements"]}
            if not rec["elements"] or "needs you" in kinds:
                rec["would"] = "needs you"
                fd["needs_you"] += 1
            elif "part" in kinds:
                rec["would"] = "part"
                fd["entries"] += sum(e["would"] == "entry" for e in rec["elements"])
            else:
                rec["would"] = "entry"
                fd["entries"] += len(rec["elements"])
        fd["why"] = ""
        if not fd["done"]:
            fd["reading"] = "not finished"
        elif fd["made_for"]:
            fd["reading"], fd["why"] = "patch only", "named for the mod"     # a patch for the mod: switch it off (MT6)
        elif fd["needs_you"]:
            fd["reading"] = "needs you"
        elif fd["records"] and fd["own"] >= fd["records"]:
            fd["reading"], fd["why"] = "patch only", "nothing would remain"  # switch it off (MT6)
        else:
            fd["reading"] = "can be demastered"
    return out


# --- running ------------------------------------------------------------------------------------------------------

def _no_window() -> dict:
    return {"creationflags": 0x08000000} if os.name == "nt" else {}        # CREATE_NO_WINDOW, for helpers


def image_running(image: str) -> bool | None:
    """Is a program of this file name running? None when it cannot be told (not Windows, or the check failed)."""
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + image, "/FO", "CSV", "/NH"], capture_output=True,
                           text=True, timeout=20, **_no_window())
    except (OSError, subprocess.SubprocessError):
        return None
    return fold(image) in fold(r.stdout)


def close_program(image: str, force: bool = False) -> None:
    """Asks every running program of this file name to close, as a click on its window's X does; with `force`,
    ends it. xEdit stays open after a script (XE01§11), so ModTrap closes the one it started."""
    if os.name != "nt":
        return
    try:
        subprocess.run(["taskkill", "/IM", image] + (["/F"] if force else []), capture_output=True, text=True,
                       timeout=30, **_no_window())
    except (OSError, subprocess.SubprocessError):
        pass


MO2_LEAVING = 30.0             # seconds MO2 gets to close once its message has been closed (the owner's PC: 4 to 8, twice over 16)
MO2_GRACE = 4.0                # seconds a MO2 that ModTrap's own command started gets to close by itself
PRESS_EVERY = 1.5              # seconds between looks for xEdit's "Module Selection" window
PRESS_LIMIT = 8                # presses of its OK in one run, at most


class OkPresser:
    """xEdit in script mode always asks which plugins to load, with those of the plugins file already ticked
    (XE01§13). For a run ModTrap started, that list is ModTrap's own, so ModTrap presses OK. Called from a job's
    waiting loop while the script has not started."""

    def __init__(self, image: str, press: Callable[[str], bool] = winauto.press_module_selection_ok,
                 board: "process.Board | None" = None, stage: str = ""):
        self.image, self._press = image, press
        self.board, self.stage = board, stage
        self.pressed = 0
        self._next = 0.0

    def look(self) -> None:
        now = time.time()
        if now < self._next or self.pressed >= PRESS_LIMIT:
            return
        self._next = now + PRESS_EVERY
        try:
            hit = self._press(self.image)
        except Exception:
            hit = False
        if hit:
            self.pressed += 1
            if self.board is not None and self.stage:
                self.board.mark(self.stage, "ok", process.DONE, "pressed")
            if self.pressed == 1:
                log.info("xEdit asked which plugins to load. The ones ModTrap listed were already ticked: ModTrap "
                         "pressed OK.")


def close_xedit(image: str, running: Callable[[str], bool | None], closer: Callable[[str, bool], None],
                poll: float = 1.0, grace: float = 20.0, changed: bool = False,
                mo2_was_running: bool | None = None, mo2_grace: float = MO2_GRACE,
                dismiss: Callable[[str], bool] = winauto.close_message) -> None:
    """After the script's end line: xEdit is asked to close, and ended if it has not gone after `grace` seconds.
    Ending it is safe: the script has finished and written what it writes itself, and an xEdit that is ended saves
    nothing (which, after a changing run, is exactly what is wanted: WHY§4).

    Then MO2. A MO2 that ModTrap's command started only for this run closes by itself once xEdit has gone, unless
    it stops to show a message: one of its plugins failing at the end of a command-line run does that (MO01§9).
    Such a MO2 is asked to close, as a click on its window's X does; never ended, and never touched if the owner
    had it open before (`mo2_was_running`)."""
    wait = min(max(poll, 0.05), 1.0)
    if running(image) is not False:
        closer(image, False)
        if running(image) is not None:
            end = time.time() + grace
            while time.time() < end and running(image) is not False:
                time.sleep(wait)
            if running(image) is not False:
                log.warn("xEdit did not close when asked%s; ModTrap ends it. Nothing is lost: the script had finished.",
                         " (it may be asking whether to save)" if changed else "")
                closer(image, True)
    if mo2_was_running is not False or running(MO2_EXE) is not True:
        return                                      # the owner's own MO2, or one that cannot be watched, or gone
    end = time.time() + mo2_grace
    dismissed = 0
    while time.time() < end:
        if running(MO2_EXE) is not True:
            return
        try:
            shown = dismissed < 5 and dismiss(MO2_EXE)       # its message, the moment it shows (WHY§54)
        except Exception:
            shown = False
        if shown:
            dismissed += 1
            if dismissed == 1:
                log.info("MO2 showed a message once the run was over (one of its own plugins failing after a "
                         "command-line run: nothing of ModTrap's). ModTrap closed the message.")
                end = max(end, time.time() + MO2_LEAVING)    # with its message closed, MO2 takes some seconds to go
        time.sleep(min(wait, 0.2))
    log.warn("MO2, started only for this run, did not close by itself: it is probably showing a message (a plugin of "
             "MO2 failing after a command-line run does that). ModTrap asks it to close; if it stays, close it yourself.")
    closer(MO2_EXE, False)
    end = time.time() + mo2_grace
    while time.time() < end:
        if running(MO2_EXE) is not True:
            log.info("MO2 closed when asked.")
            return
        try:
            if dismissed < 5 and dismiss(MO2_EXE):          # a message that shows only now is closed as the first was
                dismissed += 1
                end = max(end, time.time() + MO2_LEAVING)
        except Exception:
            pass
        time.sleep(wait)
    log.warn("MO2 is still open: press OK on its message, or close it. Whatever needs MO2 closed asks it to close again first.")


def launch(cmd: list[str], cwd: str) -> subprocess.Popen:
    """Starts MO2's command: an argument list, never a shell (WHY§9)."""
    return subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


class Job:
    """One dry run. Its state is read by the page; its lines go to the log (the page's terminal)."""

    def __init__(self, m: model.Model, p: Plan, job_dir: Path, *, launcher: Callable = launch,
                 running: Callable[[str], bool | None] = image_running, poll: float = 1.0,
                 closer: Callable[[str, bool], None] = close_program,
                 presser: Callable[[str], bool] = winauto.press_module_selection_ok):
        self.model, self.plan, self.dir = m, p, job_dir
        self.id = job_dir.name
        self._launcher, self._running, self._poll, self._closer = launcher, running, poll, closer
        self._presser = presser
        self.state = "preparing"       # preparing, starting, loading, reading, checking, done, failed, stopped
        self.message = ""
        self.started = time.time()
        self.ended: float | None = None
        self.result: dict | None = None
        self.unchanged: bool | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.manifest: dict = {}
        self.on_end: Callable[[], None] | None = None     # called once the job has ended and is written down
        self.board = process.BOARD                         # what the Process tab shows of this job (WHY§70)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="dry-run", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def public(self) -> dict:
        return {"id": self.id, "state": self.state, "message": self.message, "plan": self.plan.public(),
                "folder": str(self.dir),
                "seconds": int((self.ended or time.time()) - self.started), "unchanged": self.unchanged,
                "result": self.result}

    def _fail(self, text: str) -> None:
        self.state, self.message, self.ended = "failed", logbook.mask(text), time.time()
        self.board.stop("dry", self.message)
        log.error("the dry run failed: %s", text)
        self._xedit_log()

    def _xedit_log(self) -> None:
        """xEdit writes its own messages to the job's folder when it closes (XE01§6): their last lines say why a
        script did not run or stopped, so they go to the terminal, masked like every line."""
        tail = _lines(self.dir / "xedit-log.txt")[-40:]
        if not tail:
            log.warn("xEdit left no log of its own in the job's folder (it may still be open, or never started)")
            return
        log.warn("the last lines of xEdit's own log:")
        for ln in tail:
            log.warn("  | %s", ln[:500])

    def _run(self) -> None:
        try:
            self._do()
        except Refused as e:
            self._fail(str(e))
        except Exception as e:          # the page must never wait on a job that died
            self._fail("an error inside ModTrap: " + logbook.why(e))
        # Written down, so that the session shows this job again after ModTrap is closed and started (MT20).
        try:
            paths.write_atomic(self.dir / "job.json", (json.dumps(self.public(), indent=1) + "\n").encode("utf-8"))
        except (OSError, TypeError, ValueError) as e:
            log.warn("the dry run's outcome could not be kept for later: %s", logbook.why(e))
        if self.on_end:
            try:
                self.on_end()
            except Exception as e:
                log.warn("after the dry run: %s", logbook.why(e))

    def _do(self) -> None:
        p = self.plan
        log.info("dry run %s: %d trapped plugin(s), %d dependant(s), %d plugin(s) for xEdit to load",
                 self.id, len(p.trapped), len(p.dependants), len(p.load))
        board = self.board
        board.begin("dry", process.DRY, drop=("change", "install"))
        board.mark("dry", "prepare", process.GOING, "%d dependant(s)" % len(p.dependants))
        self.manifest = prepare(self.model, p, self.dir)
        board.mark("dry", "prepare", process.DONE)
        board.mark("dry", "start", process.GOING, p.tool)
        log.info("the dependants are copied and hashed in the job's safe folder (%d file(s))", len(p.dependants))
        if not Path(p.mo2).is_file():
            raise Refused("ModOrganizer.exe was not found in the modlist's folder")
        cmd = command(p, self.dir)
        image = Path(p.tool_binary.replace("\\", "/")).name
        if self._running(image):
            raise Refused("%s is already running: close it first, so that ModTrap can tell its own run from yours"
                          % image)
        mo2_was_running = self._running(MO2_EXE)                 # False: this run's MO2 is ours to see closed
        log.info("starting %s through MO2 (profile '%s'), with ModTrap's script in report mode", p.tool, p.profile)
        log.info("command: ModOrganizer.exe -p \"%s\" run -e -a \"%s\" \"%s\"", p.profile,
                 arguments(self.dir, SCRIPT.name, p.tool_args, p.data_dir).replace('"', "'"), p.tool)
        self.state = "starting"
        try:
            proc = self._launcher(cmd, str(Path(p.mo2).parent))
        except OSError as e:
            raise Refused("MO2 could not be started: " + logbook.why(e)) from None
        progress, report = self.dir / "progress.txt", self.dir / "report.tsv"
        seen, seen_running, gone_since = 0, False, None
        ok = OkPresser(image, self._presser, board, "dry")
        try:
            touch = sum(1 for ln in (self.dir / "script" / "modtrap-job.txt").read_text(encoding="utf-8-sig").splitlines()
                        if re.match(r"touch\.\d+=", ln))
        except OSError:
            touch = 0
        told = process.Lines("dry", len(p.dependants), touch, board)
        board.mark("dry", "start", process.DONE)
        board.mark("dry", "ok", process.GOING, "waiting for xEdit's window")
        self.state = "loading"
        log.info("xEdit is loading the plugins; its own window shows the progress. This can take some minutes. If its "
                 "“Module Selection” window stays open, press OK there: the right plugins are already ticked.")
        while True:
            if self._stop.wait(self._poll):
                self.state, self.message, self.ended = "stopped", "stopped at your request", time.time()
                board.stop("dry", "stopped at your request")
                log.warn("the dry run was stopped; xEdit is left for you to close (it has changed nothing)")
                return
            if seen == 0:
                ok.look()
            lines = _lines(progress)
            for ln in lines[seen:]:
                log.info("xEdit: %s", ln)
                self.state = "reading"
                told.take(ln)
            seen = len(lines)
            ended = _ended(report)
            if ended:
                break
            elapsed = time.time() - self.started
            alive = self._running(image)
            if alive:
                seen_running, gone_since = True, None
            elif alive is False and (seen_running or proc.poll() is not None and elapsed > 30):
                gone_since = gone_since or time.time()
                if time.time() - gone_since > GONE_GRACE:              # gone for good, and no end line in the report
                    raise Refused("xEdit closed before the script finished. Its own log is in the job's folder "
                                  "(xedit-log.txt); the Log tab shows how far it got.")
            if seen == 0 and elapsed > START_LIMIT:
                raise Refused("xEdit did not start the script within %d minutes" % (START_LIMIT // 60))
            if elapsed > TIME_LIMIT:
                raise Refused("the dry run took longer than %d minutes; ModTrap stopped waiting" % (TIME_LIMIT // 60))
        self.state = "checking"
        options = paths.load_settings().get("options")
        self.result = parse_report(_read(report), p.trapped, p.trapped_mods, self.model.instance.primary,
                                   script_props=not (isinstance(options, dict) and options.get("script_props") is False))
        board.settle("dry", "close")
        board.mark("dry", "close", process.GOING)
        close_xedit(image, self._running, self._closer, self._poll, mo2_was_running=mo2_was_running)   # XE01§11
        board.mark("dry", "close", process.DONE)
        board.mark("dry", "check", process.GOING)
        # The script only read. Prove it: every dependant must still be the file that was copied (DESIGN§8).
        changed = []
        for fd in self.manifest["dependants"]:
            r = self.model.plugins[fold(fd["name"])]
            try:
                if r.path is None or _sha256(r.path) != fd["sha256"]:
                    changed.append(fd["name"])
            except OSError:
                changed.append(fd["name"])
        self.unchanged = not changed
        self.ended = time.time()
        if changed:
            self.state = "failed"
            self.message = ("these plugins are not the files they were before the dry run: %s. Their originals are "
                            "in the job's safe folder." % ", ".join(changed))
            log.error("%s", self.message)
            board.stop("dry", self.message)
            return
        if self.result["end"] != "ok":
            self._fail("the script reported a failure: " + (self.result["reason"] or "no reason given"))
            return
        absent = self.result["trap_missing"] + self.result["not_loaded"]
        if absent:
            where = self.result.get("data_path") or "the folder it reads"
            self._fail("xEdit did not load %s. It looked for plugins in %s%s. Nothing was read, and nothing was "
                       "changed." % (", ".join(absent[:6]) + (" and %d more" % (len(absent) - 6) if len(absent) > 6 else ""),
                                     where, (", while MO2 puts this modlist's files into %s" % p.data_dir)
                                     if p.data_dir and self.result.get("data_path") and
                                     fold(self.result["data_path"].rstrip("\\/")) != fold(p.data_dir.rstrip("\\/")) else ""))
            return
        if self.result["held_changed"]:
            log.warn("xEdit held %d plugin(s) as changed although the script changed nothing; the marks were cleared "
                     "and the files are unchanged on disk", len(self.result["held_changed"]))
        paths.write_atomic(self.dir / "result.json", (json.dumps(self.result, indent=1) + "\n").encode("utf-8"))
        self.state = "done"
        fs = self.result["files"]
        board.mark("dry", "check", process.DONE, "%d dependant(s) read, every one unchanged on disk" % len(fs))
        log.info("the dry run is done in %d s: %d dependant(s) read, every one unchanged on disk",
                 int(self.ended - self.started), len(fs))
        for fd in fs:
            log.info("  %s: %d record(s) of the trapped mod's own, %d list entr(ies), %d part(s) carried on from the "
                     "mod, %d that need you -> %s%s", fd["name"], fd["own"], fd["entries"], fd.get("parts", 0),
                     fd["needs_you"], fd["reading"], " (%s)" % fd["why"] if fd.get("why") else "")


def _read(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(256 * 1024 * 1024)
    except OSError:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


def _lines(path: Path) -> list[str]:
    return [ln for ln in _read(path).splitlines() if ln.strip()]


def _ended(report: Path) -> bool:
    """Has the script written its end line? Only the file's last bytes are read, and the file is held open as
    briefly as can be: xEdit's script cannot write a file that another program has open (XE01§15)."""
    try:
        with open(report, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            tail = f.read()
    except OSError:
        return False
    return any(ln.startswith("X\t") for ln in tail.decode("utf-8", "replace").split("\n")[-3:])


class PastJob:
    """A job of an earlier run of ModTrap, as its session kept it: only for showing."""

    def __init__(self, job_dir: Path):
        self.dir, self.id = job_dir, job_dir.name
        try:
            with open(job_dir / "job.json", "rb") as f:
                data = json.loads(f.read(256 * 1024 * 1024).decode("utf-8"))
            if not isinstance(data, dict) or "state" not in data or "plan" not in data:
                raise ValueError
        except (OSError, ValueError):
            # No outcome was written: ModTrap was closed, or stopped, while the job was going.
            plan = {"trapped_mods": [], "trapped": [], "dependants": [], "load": 0, "load_names": [], "profile": "",
                    "tool": "", "tool_file": "", "warnings": []}
            data = {"id": self.id, "state": "failed", "plan": plan, "seconds": 0, "unchanged": None, "result": None,
                    "message": "ModTrap was closed while this dry run was going, so its outcome was not kept. "
                               "xEdit only reads in a dry run; start it again when you are ready."}
        data["folder"] = str(job_dir)
        data["past"] = True
        self._data = data
        self.state = data["state"]

    def public(self) -> dict:
        return self._data

    def stop(self) -> None:
        pass


def new_job_dir(base: Path | None = None) -> Path:
    base = base or paths.home() / "jobs"
    base.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for n in range(100):
        d = base / ("dryrun-%s%s" % (stamp, "-%d" % n if n else ""))
        try:
            d.mkdir()
            return d
        except FileExistsError:
            continue
    raise Refused("a folder for the job could not be made")
