"""The record check (MT21, DESIGN§16.5): which records of a newly added plugin override records of other plugins,
and what that takes from, or loses to, the plugins that change the same records.

Only xEdit can read inside plugins. ModTrap starts the owner's xEdit through MO2 with a script of its own that only
reports (modtrap/xedit/ModTrapRecords.pas), as the dry run does (DESIGN§7), with the whole active load order
loaded: a conflict is between all the plugins that hold a record. Nothing is changed; the plugins looked at are
hashed before and after to prove it.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import adding, dryrun, logbook, model, paths
from .instance import fold

log = logbook.get("records")
SCRIPT = Path(__file__).resolve().parent / "xedit" / "ModTrapRecords.pas"
LIST_CAP = 400                 # records listed for the page, for each plugin and kind
# xEdit's levels (XE01§10). Over all plugins: 5 is a conflict, 6 a critical one. For this plugin's copy:
ALL_CONFLICT, ALL_CRITICAL = 5, 6
THIS_ITM, THIS_ITM_WINS, THIS_WINS, THIS_LOSES = 3, 9, 10, 11


class Refused(Exception):
    """The record check cannot be planned or started; the text says why."""


@dataclass
class Plan:
    new: list[str]                  # the plugins to look at, in load order
    load: list[str]                 # every plugin xEdit is to load: the whole active load order
    mo2: str
    profile: str
    tool: str
    tool_binary: str
    warnings: list[str] = field(default_factory=list)
    tool_args: str = ""
    data_dir: str = ""

    def public(self) -> dict:
        return {"new": self.new, "load": len(self.load), "profile": self.profile, "tool": self.tool,
                "tool_file": Path(self.tool_binary.replace("\\", "/")).name, "warnings": self.warnings}


def plan(m: model.Model, mod_names: list[str]) -> Plan:
    inst = m.instance
    new: dict[str, model.PluginRow] = {}
    for name in mod_names:
        mod = inst.mod(name)
        if mod is None or mod.kind != "mod":
            raise Refused("'%s' is not a mod of this profile" % name)
        if not mod.enabled:
            raise Refused("'%s' is not enabled yet: xEdit can only read a plugin that is in the game's folder as MO2 "
                          "builds it. Add the mod first." % mod.name)
        for r in m.provided_by(mod):
            if r.active and r.path is not None and not r.primary:
                new[fold(r.name)] = r
    if not new:
        raise Refused("these mods have no active plugin to look at")
    rows = [m.plugins[f] for f in m.order if m.plugins[f].position is not None and m.plugins[f].active
            and m.plugins[f].source is not None]
    missing = sorted({i.plugin for i in m.issues})
    if missing:
        raise Refused("the load order has plugins with missing or inactive masters (%s): xEdit would stop at them. "
                      "See the Health tab." % ", ".join(missing[:4]))
    exe = dryrun.find_xedit_exe(inst)
    return Plan(new=[r.name for r in rows if fold(r.name) in new], load=[r.name for r in rows],
                mo2=str(inst.root / dryrun.MO2_EXE), profile=inst.profile, tool=exe.title, tool_binary=exe.binary,
                tool_args=exe.arguments, data_dir=dryrun.data_dir_of(inst))


def prepare(m: model.Model, p: Plan, job_dir: Path) -> dict:
    """The job's folder: the script, its job file, the plugin list for xEdit, and a hash of each plugin looked at.
    Writes nothing outside `job_dir`."""
    script_dir = job_dir / "script"
    script_dir.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script_dir / SCRIPT.name)
    lines = ["format=modtrap-job/1", "mode=records", "out=%s" % (job_dir / "report.tsv"),
             "progress=%s" % (job_dir / "progress.txt"), "new.count=%d" % len(p.new)]
    lines += ["new.%d=%s" % (i, n) for i, n in enumerate(p.new)]
    paths.write_atomic(script_dir / "modtrap-job.txt", ("\r\n".join(lines) + "\r\n").encode("utf-8-sig"))
    primary = {fold(x) for x in m.instance.primary}
    listed = ["*" + n for n in p.load if fold(n) not in primary]
    try:
        text = ("\r\n".join(listed) + "\r\n").encode("mbcs" if os.name == "nt" else "cp1252")
    except UnicodeEncodeError:
        raise Refused("a plugin's name cannot be written in this PC's text encoding, which xEdit's plugin list "
                      "needs") from None
    paths.write_atomic(job_dir / "plugins.txt", text)
    hashes = {n: dryrun._sha256(m.plugins[fold(n)].path) for n in p.new}
    manifest = {"format": "modtrap-records/1", "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "profile": p.profile,
                "new": p.new, "load": len(p.load), "tool": p.tool, "sha256": hashes}
    paths.write_atomic(job_dir / "manifest.json", (json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    return manifest


def command(p: Plan, job_dir: Path) -> list[str]:
    return [p.mo2, "-p", p.profile, "run", "-e", "-a",
            dryrun.arguments(job_dir, SCRIPT.name, p.tool_args, p.data_dir), p.tool]


# --- the report -------------------------------------------------------------------------------------------------------

def parse_report(text: str, m: model.Model | None = None) -> dict:
    """What the script found, sorted for the owner. For each plugin looked at, its overriding records fall into:
    alone (only it changes the record), takes (it wins a record that other plugins also change: their change to it
    is lost), loses (a later plugin wins it), same (identical to what it overrides: it changes nothing)."""
    files: dict[str, dict] = {}
    out = {"format": "", "xedit": "", "files": [], "missing": [], "held_changed": [], "end": "", "reason": "",
           "data_path": ""}
    memo: dict = {}

    def made_by_tool(name: str) -> bool:
        r = m.row(name) if m is not None else None
        return bool(r is not None and adding.generated(m, r, memo))

    for line in text.split("\n"):
        parts = line.rstrip("\r").split("\t")
        kind = parts[0]
        if kind == "H" and len(parts) >= 4:
            out["format"], out["xedit"] = parts[1], parts[3]
        elif kind == "F" and len(parts) >= 4:
            files[fold(parts[1])] = {"name": parts[1], "records": int(parts[2] or 0), "own": 0, "overrides": 0,
                                     "alone": 0, "same": 0, "takes": [], "loses": [], "takes_count": 0,
                                     "loses_count": 0, "from": {}, "to": {}, "unknown": 0, "done": False}
        elif kind == "O" and len(parts) >= 8 and fold(parts[1]) in files:
            f = files[fold(parts[1])]
            try:
                lvl_all, lvl_this = int(parts[5]), int(parts[6])
            except ValueError:
                lvl_all = lvl_this = -1
            chain = parts[7].split("\x1f")
            me = next((i for i, n in enumerate(chain) if fold(n) == fold(f["name"])), None)
            rec = {"sig": parts[2], "form": parts[3], "edid": parts[4], "level": lvl_all}
            if me is None:
                f["unknown"] += 1
                continue
            before = [n for n in chain[1:me]]                # other overriding plugins that load before it
            after = chain[me + 1:]
            if lvl_this in (THIS_ITM, THIS_ITM_WINS):
                f["same"] += 1
            elif after:
                # A later plugin holds the record: its copy is the one the game uses.
                f["loses_count"] += 1
                winner = after[-1]
                f["to"][winner] = f["to"].get(winner, 0) + 1
                if len(f["loses"]) < LIST_CAP:
                    f["loses"].append(dict(rec, to=winner, tool=made_by_tool(winner)))
            elif before and (lvl_all >= ALL_CONFLICT or lvl_all < 0):
                f["takes_count"] += 1
                for n in before:
                    f["from"][n] = f["from"].get(n, 0) + 1
                if len(f["takes"]) < LIST_CAP:
                    f["takes"].append(dict(rec, **{"from": before}))
            else:
                f["alone"] += 1                              # only it changes the record, or the changes agree
        elif kind == "D" and len(parts) >= 5 and fold(parts[1]) in files:
            f = files[fold(parts[1])]
            f["own"], f["overrides"], f["done"] = int(parts[3] or 0), int(parts[4] or 0), True
        elif kind == "M" and len(parts) >= 2:
            out["missing"].append(parts[1])
        elif kind == "P" and len(parts) >= 2:
            out["data_path"] = parts[1]
        elif kind == "U" and len(parts) >= 2:
            out["held_changed"].append(parts[1])
        elif kind == "X" and len(parts) >= 2:
            out["end"], out["reason"] = parts[1], parts[2] if len(parts) > 2 else ""
    for f in files.values():
        f["from"] = sorted(([n, c, made_by_tool(n)] for n, c in f["from"].items()), key=lambda x: -x[1])
        f["to"] = sorted(([n, c, made_by_tool(n)] for n, c in f["to"].items()), key=lambda x: -x[1])
        # What needs the owner: records it takes from plugins made by hand (a patch settled them), and records it
        # loses to plugins made by hand. What a tool made is made again by running the tool.
        f["needs_patch"] = min(f["takes_count"], sum(c for n, c, tool in f["from"] if not tool))
        f["lost_to_hand"] = sum(c for n, c, tool in f["to"] if not tool)
        f["reading"] = ("needs a look" if f["needs_patch"] or f["lost_to_hand"] else "clean")
        out["files"].append(f)
    return out


# --- running ----------------------------------------------------------------------------------------------------------

class Job:
    """One record check. Its state is read by the page; its lines go to the log. The tool check (MT23,
    `toolcheck.Job`) is the same run with another script: what differs is in the five methods below `_run`."""

    WHAT = "record check"
    THREAD = "records"

    def __init__(self, m: model.Model, p: Plan, job_dir: Path, *, launcher: Callable = dryrun.launch,
                 running: Callable[[str], bool | None] = dryrun.image_running, poll: float = 1.0,
                 closer: Callable[[str, bool], None] = dryrun.close_program,
                 presser: Callable[[str], bool] = dryrun.winauto.press_module_selection_ok):
        self.model, self.plan, self.dir = m, p, job_dir
        self.id = job_dir.name
        self._launcher, self._running, self._poll, self._closer = launcher, running, poll, closer
        self._presser = presser
        self.state = "preparing"       # preparing, starting, loading, reading, checking, done, failed, stopped
        self.message = ""
        self.started = time.time()
        self.ended: float | None = None
        self.result: dict | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_end: Callable[[], None] | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=self.THREAD, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def public(self) -> dict:
        return {"id": self.id, "state": self.state, "message": self.message, "plan": self.plan.public(),
                "seconds": int((self.ended or time.time()) - self.started), "result": self.result}

    def _run(self) -> None:
        try:
            self._do()
        except (Refused, dryrun.Refused) as e:
            self.state, self.message = "failed", logbook.mask(str(e))
            log.error("the %s failed: %s", self.WHAT, e)
        except Exception as e:
            self.state, self.message = "failed", "an error inside ModTrap: " + logbook.why(e)
            log.error("the %s failed: %s", self.WHAT, logbook.why(e))
        self.ended = self.ended or time.time()
        try:
            paths.write_atomic(self.dir / "job.json", (json.dumps(self.public(), indent=1) + "\n").encode("utf-8"))
        except (OSError, TypeError, ValueError):
            pass
        if self.on_end:
            try:
                self.on_end()
            except Exception as e:
                log.warn("after the %s: %s", self.WHAT, logbook.why(e))

    # What a run with another script says differently.

    def _prepare(self) -> dict:
        return prepare(self.model, self.plan, self.dir)

    def _command(self) -> list[str]:
        return command(self.plan, self.dir)

    def _parse(self, text: str) -> dict:
        return parse_report(text, self.model)

    def _does(self) -> str:
        return "with ModTrap's script that reports overriding records"

    def _told(self) -> None:
        for f in self.result["files"]:
            log.info("  %s: %d of its own, %d overriding: %d alone, %d taken from others, %d lost to later plugins, "
                     "%d that change nothing -> %s", f["name"], f["own"], f["overrides"], f["alone"],
                     f["takes_count"], f["loses_count"], f["same"], f["reading"])

    def _do(self) -> None:
        p = self.plan
        log.info("%s %s: %d plugin(s) to look at, %d for xEdit to load (the whole active load order)",
                 self.WHAT, self.id, len(p.new), len(p.load))
        manifest = self._prepare()
        if not Path(p.mo2).is_file():
            raise Refused("ModOrganizer.exe was not found in the modlist's folder")
        image = Path(p.tool_binary.replace("\\", "/")).name
        if self._running(image):
            raise Refused("%s is already running: close it first, so that ModTrap can tell its own run from yours" % image)
        mo2_was_running = self._running(dryrun.MO2_EXE)
        log.info("starting %s through MO2 (profile '%s'), %s", p.tool, p.profile, self._does())
        self.state = "starting"
        try:
            proc = self._launcher(self._command(), str(Path(p.mo2).parent))
        except OSError as e:
            raise Refused("MO2 could not be started: " + logbook.why(e)) from None
        progress, report = self.dir / "progress.txt", self.dir / "report.tsv"
        seen, seen_running, gone_since = 0, False, None
        ok = dryrun.OkPresser(image, self._presser)
        self.state = "loading"
        log.info("xEdit is loading the whole load order; on a large modlist this takes many minutes")
        while True:
            if self._stop.wait(self._poll):
                self.state, self.message, self.ended = "stopped", "stopped at your request", time.time()
                log.warn("the %s was stopped; xEdit is left for you to close (it has changed nothing)", self.WHAT)
                return
            if seen == 0:
                ok.look()
            lines = dryrun._lines(progress)
            for ln in lines[seen:]:
                log.info("xEdit: %s", ln)
                self.state = "reading"
            seen = len(lines)
            if dryrun._ended(report):
                break
            elapsed = time.time() - self.started
            alive = self._running(image)
            if alive:
                seen_running, gone_since = True, None
            elif alive is False and (seen_running or proc.poll() is not None and elapsed > 30):
                gone_since = gone_since or time.time()
                if time.time() - gone_since > dryrun.GONE_GRACE:
                    raise Refused("xEdit closed before the script finished. Its own log is in the job's folder "
                                  "(xedit-log.txt).")
            if seen == 0 and elapsed > dryrun.START_LIMIT * 2:
                raise Refused("xEdit did not start the script within %d minutes" % (dryrun.START_LIMIT * 2 // 60))
            if elapsed > dryrun.TIME_LIMIT * 2:
                raise Refused("the %s took longer than %d minutes; ModTrap stopped waiting"
                              % (self.WHAT, dryrun.TIME_LIMIT * 2 // 60))
        self.state = "checking"
        self.result = self._parse(dryrun._read(report))
        dryrun.close_xedit(image, self._running, self._closer, self._poll, mo2_was_running=mo2_was_running)
        changed = []
        for name, digest in manifest["sha256"].items():
            r = self.model.plugins[fold(name)]
            try:
                if r.path is None or dryrun._sha256(r.path) != digest:
                    changed.append(name)
            except OSError:
                changed.append(name)
        self.ended = time.time()
        if changed:
            raise Refused("these plugins are not the files they were before the check: %s" % ", ".join(changed))
        if self.result["end"] != "ok":
            raise Refused("the script reported a failure: " + (self.result["reason"] or "no reason given"))
        if self.result["missing"]:
            raise Refused("xEdit did not load %s. It looked for plugins in %s." % (
                ", ".join(self.result["missing"][:6]), self.result.get("data_path") or "the folder it reads"))
        paths.write_atomic(self.dir / "result.json", (json.dumps(self.result, indent=1) + "\n").encode("utf-8"))
        self.state = "done"
        self._told()


def new_job_dir(base: Path, kind: str = "records") -> Path:
    base.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for n in range(100):
        d = base / ("%s-%s%s" % (kind, stamp, "-%d" % n if n else ""))
        try:
            d.mkdir()
            return d
        except FileExistsError:
            continue
    raise Refused("a folder for the job could not be made")


__all__ = ["Plan", "Job", "Refused", "plan", "prepare", "command", "parse_report", "new_job_dir"]
