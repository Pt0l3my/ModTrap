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
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import logbook, model, paths
from .instance import GAME, Instance, fold

SCRIPT = Path(__file__).resolve().parent / "xedit" / "ModTrap.pas"
MO2_EXE = "ModOrganizer.exe"
# The program files xEdit goes by for Skyrim SE, the 64-bit ones first (WHY§14).
XEDIT_NAMES = ("sseedit64.exe", "xedit64.exe", "sseedit.exe", "xedit.exe")
TIME_LIMIT = 60 * 60            # seconds a dry run may take before ModTrap gives up waiting
START_LIMIT = 20 * 60           # seconds xEdit may take to load before the script's first line
GONE_GRACE = 8                  # seconds xEdit must be gone, with no end line in the report, to count as closed
# Arrays whose entries can be taken out without changing what the rest of the record means (MT4, case B): by the
# record's signature ("*" for any) and the last part of the array's path as xEdit names it. LIKELY until the first
# real report shows xEdit's exact names (WHY§31).
SAFE_ARRAYS = (("FLST", "FormIDs"), ("LVLI", "Leveled List Entries"), ("LVLN", "Leveled List Entries"),
               ("LVSP", "Leveled List Entries"), ("*", "KWDA - Keywords"))

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

    def public(self) -> dict:
        return {"trapped_mods": self.trapped_mods, "trapped": self.trapped, "dependants": self.dependants,
                "load": len(self.load), "load_names": self.load, "profile": self.profile, "tool": self.tool,
                "tool_file": Path(self.tool_binary.replace("\\", "/")).name, "warnings": self.warnings}


def find_xedit(inst: Instance) -> tuple[str, str]:
    """The xEdit set up in MO2: (its title, its program file). The 64-bit one first."""
    by_name: dict[str, tuple[str, str]] = {}
    for e in inst.executables:
        base = fold(Path(e.binary.replace("\\", "/")).name)
        by_name.setdefault(base, (e.title, e.binary))
    for name in XEDIT_NAMES:
        if name in by_name:
            return by_name[name]
    raise Refused("no xEdit is set up as an executable in this MO2 (looked for SSEEdit64.exe, xEdit64.exe, "
                  "SSEEdit.exe and xEdit.exe)")


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
    title, binary = find_xedit(inst)
    mo2 = inst.root / MO2_EXE
    return Plan(trapped_mods=mods, trapped=[r.name for r in order if fold(r.name) in trapped],
                dependants=[r.name for r in order if fold(r.name) in deps], load=[r.name for r in order],
                mo2=str(mo2), profile=inst.profile, tool=title, tool_binary=binary, warnings=warnings)


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
    paths.write_atomic(script_dir / "modtrap-job.txt", ("\r\n".join(lines) + "\r\n").encode("utf-8"))
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


def arguments(job_dir: Path) -> str:
    """xEdit's arguments (XE01§2 to XE01§6): our script, our plugin list, no questions, close at the end; backups
    and a log in the job's folder; no reference building, which the report does not need."""
    q = lambda p: '"%s"' % p                                   # noqa: E731
    return " ".join(["-sse", "-script:" + q(job_dir / "script" / SCRIPT.name), "-P:" + q(job_dir / "plugins.txt"),
                     "-autoload", "-autoexit", "-nobuildrefs", "-B:" + q(job_dir / "xedit-backups"),
                     "-R:" + q(job_dir / "xedit-log.txt")])


def command(p: Plan, job_dir: Path) -> list[str]:
    """MO2's command to run a configured executable in its virtual file system with our arguments (MO01§3)."""
    return [p.mo2, "-p", p.profile, "run", "-e", "-a", arguments(job_dir), p.tool]


# --- the report ---------------------------------------------------------------------------------------------------

def _safe_array(signature: str, array_path: str) -> bool:
    last = array_path.rsplit("\\", 1)[-1].strip()
    return any((sig in ("*", signature)) and last == name for sig, name in SAFE_ARRAYS)


def parse_report(text: str) -> dict:
    """The script's report as the page shows it: per dependant, what needs a trapped plugin and what ModTrap would
    do about each (MT4): "record" (the dependant's copy of a trapped plugin's own record: taken out), "entry" (an
    entry of a list that is safe to shorten: taken out), "needs you" (anything else)."""
    out: dict = {"format": "", "xedit": "", "end": "", "reason": "", "files": [], "not_loaded": [], "held_changed": []}
    files: dict[str, dict] = {}
    records: dict[tuple[str, str], dict] = {}
    for line in text.splitlines():
        f = line.split("\t")
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
        elif kind == "E" and len(f) >= 10 and (f[1], f[2]) in records:
            rec = records[(f[1], f[2])]
            safe = f[3] == "entry" and _safe_array(rec["signature"], f[5])
            rec["elements"].append({"kind": f[3], "entry": f[4], "array": f[5], "array_length": int(f[6] or 0),
                                    "path": f[7], "target_file": f[8], "target_form": f[9],
                                    "would": "entry" if safe else "needs you"})
        elif kind == "D" and len(f) >= 4 and f[1] in files:
            files[f[1]]["needing"], files[f[1]]["done"] = int(f[3] or 0), True
        elif kind == "M" and len(f) >= 2:
            out["not_loaded"].append(f[1])
        elif kind == "U" and len(f) >= 2:
            out["held_changed"].append(f[1])
        elif kind == "X" and len(f) >= 2:
            out["end"], out["reason"] = f[1], f[2] if len(f) > 2 else ""
    for fd in files.values():
        for rec in fd["items"]:
            if rec["own"]:
                rec["would"] = "record"
                fd["own"] += 1
            elif rec["elements"] and all(e["would"] == "entry" for e in rec["elements"]):
                rec["would"] = "entry"
                fd["entries"] += len(rec["elements"])
            else:
                rec["would"] = "needs you"
                fd["needs_you"] += 1
        if not fd["done"]:
            fd["reading"] = "not finished"
        elif fd["needs_you"]:
            fd["reading"] = "needs you"
        elif fd["records"] and fd["own"] >= fd["records"]:
            fd["reading"] = "patch only"          # nothing of it would remain: switch it off (MT6)
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


def launch(cmd: list[str], cwd: str) -> subprocess.Popen:
    """Starts MO2's command: an argument list, never a shell (WHY§9)."""
    return subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


class Job:
    """One dry run. Its state is read by the page; its lines go to the log (the page's terminal)."""

    def __init__(self, m: model.Model, p: Plan, job_dir: Path, *, launcher: Callable = launch,
                 running: Callable[[str], bool | None] = image_running, poll: float = 1.0):
        self.model, self.plan, self.dir = m, p, job_dir
        self.id = job_dir.name
        self._launcher, self._running, self._poll = launcher, running, poll
        self.state = "preparing"       # preparing, starting, loading, reading, checking, done, failed, stopped
        self.message = ""
        self.started = time.time()
        self.ended: float | None = None
        self.result: dict | None = None
        self.unchanged: bool | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.manifest: dict = {}

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

    def _do(self) -> None:
        p = self.plan
        log.info("dry run %s: %d trapped plugin(s), %d dependant(s), %d plugin(s) for xEdit to load",
                 self.id, len(p.trapped), len(p.dependants), len(p.load))
        self.manifest = prepare(self.model, p, self.dir)
        log.info("the dependants are copied and hashed in the job's safe folder (%d file(s))", len(p.dependants))
        if not Path(p.mo2).is_file():
            raise Refused("ModOrganizer.exe was not found in the modlist's folder")
        cmd = command(p, self.dir)
        image = Path(p.tool_binary.replace("\\", "/")).name
        if self._running(image):
            raise Refused("%s is already running: close it first, so that ModTrap can tell its own run from yours"
                          % image)
        log.info("starting %s through MO2 (profile '%s'), with ModTrap's script in report mode", p.tool, p.profile)
        log.info("command: ModOrganizer.exe -p \"%s\" run -e -a \"%s\" \"%s\"", p.profile,
                 arguments(self.dir).replace('"', "'"), p.tool)
        self.state = "starting"
        try:
            proc = self._launcher(cmd, str(Path(p.mo2).parent))
        except OSError as e:
            raise Refused("MO2 could not be started: " + logbook.why(e)) from None
        progress, report = self.dir / "progress.txt", self.dir / "report.tsv"
        seen, seen_running, gone_since = 0, False, None
        self.state = "loading"
        log.info("xEdit is loading the plugins; its own window shows the progress. This can take some minutes.")
        while True:
            if self._stop.wait(self._poll):
                self.state, self.message, self.ended = "stopped", "stopped at your request", time.time()
                log.warn("the dry run was stopped; xEdit is left for you to close (it has changed nothing)")
                return
            lines = _lines(progress)
            for ln in lines[seen:]:
                log.info("xEdit: %s", ln)
                self.state = "reading"
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
        self.result = parse_report(_read(report))
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
            return
        if self.result["end"] != "ok":
            self._fail("the script reported a failure: " + (self.result["reason"] or "no reason given"))
            return
        if self.result["held_changed"]:
            log.warn("xEdit held %d plugin(s) as changed although the script changed nothing; the marks were cleared "
                     "and the files are unchanged on disk", len(self.result["held_changed"]))
        paths.write_atomic(self.dir / "result.json", (json.dumps(self.result, indent=1) + "\n").encode("utf-8"))
        self.state = "done"
        fs = self.result["files"]
        log.info("the dry run is done in %d s: %d dependant(s) read, every one unchanged on disk",
                 int(self.ended - self.started), len(fs))
        for fd in fs:
            log.info("  %s: %d record(s) of the trapped mod's own, %d list entr(ies), %d that need you -> %s",
                     fd["name"], fd["own"], fd["entries"], fd["needs_you"], fd["reading"])


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
    text = _read(report)
    return any(ln.startswith("X\t") for ln in text.splitlines()[-3:])


def new_job_dir() -> Path:
    base = paths.home() / "jobs"
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
