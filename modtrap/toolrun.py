"""Starting one of the modlist's own tools through MO2, for the owner to work, and saying afterwards which of its
output files changed (MT18, MT21, DESIGN§16.8 step 5).

ModTrap changes nothing here: it starts a program the owner has set up in MO2, exactly as MO2's own Run button
does (MO01§3), waits for it to close, and compares the files in the places that tool writes to with how they were
before. What the tool does in between is the tool's and the owner's.

A tool that has switches of its own to do its work and close without being touched is started with them, beside
the arguments MO2 has for it, when the owner's setting says so (TL01§16, WHY§84): the switches are data
(`tools.json`, "self_run"), never guessed. And a MO2 that stops at a message once the tool has gone (MO01§9) has
that message closed, so that the run ends when the tool does (WHY§84).
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable

from . import dryrun, logbook, steps, toollog, tools, winauto
from .instance import Instance, fold

log = logbook.get("tool")
TIME_LIMIT = 8 * 60 * 60
WATCH_FILES = 60_000
MO2_STAYS = 30                 # seconds a MO2 whose message was closed may take to go, before the run counts as ended


class Refused(Exception):
    """The tool is not started; the text says why."""


def _snapshot(folders: list[Path], files: list[Path]) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}

    def note(p: Path) -> None:
        try:
            st = p.stat()
            out[str(p)] = (st.st_mtime_ns, st.st_size)
        except OSError:
            pass

    for f in files:
        note(f)
    for d in folders:
        names, _cut = steps.walk(d, limit=WATCH_FILES, seconds=20.0)
        for n in names:
            if len(out) >= WATCH_FILES:
                break
            note(d.joinpath(*n.split("/")))
    return out


def self_run_arguments(title: str, binary: str, own: str) -> tuple[str, list[str]]:
    """For a tool that can do its work and close by itself: the whole argument string to start it with (MO2's `-a`
    replaces the executable's own arguments, so those come first, as they are) and the switches added. ("", [])
    for a tool without such switches, or one whose own arguments already carry them all."""
    name, _kind = tools.of_executable(title, binary)
    entry = next((t for t in tools.load() if t["tool"] == name), {})
    spec = entry.get("self_run")
    if not isinstance(spec, dict):
        return "", []
    have = {dryrun.switch_name(x) for x in dryrun.split_arguments(own)}
    add = [sw["switch"] for sw in spec.get("switches", [])
           if not have & {dryrun.switch_name(a) for a in [sw["switch"]] + list(sw.get("also", []))}]
    if not add:
        return "", []
    return (own.strip() + " " + " ".join(add)).strip(), add


class ToolJob:
    def __init__(self, inst: Instance, title: str, watch_files: list[Path], *,
                 launcher: Callable = dryrun.launch, running: Callable[[str], bool | None] = dryrun.image_running,
                 poll: float = 1.0, self_run: bool = False, dismiss: Callable[[str], bool] = winauto.close_message,
                 grace: float = dryrun.GONE_GRACE, keep_logs: Path | None = None):
        exe = next((e for e in inst.executables if e.title == title), None)
        if exe is None:
            raise Refused("“%s” is not in this MO2's list of tools" % title)
        self.inst, self.title = inst, title
        self._dismiss, self._grace = dismiss, grace
        self._binary, self._keep_logs = exe.binary, keep_logs
        self.own_log: dict | None = None        # what the tool's own log of this run says (toollog, WHY§88)
        self.arguments, self.switches = self_run_arguments(title, exe.binary, exe.arguments) if self_run else ("", [])
        name, _kind = tools.of_executable(title, exe.binary)
        # What is known about this tool closing without having written anything (data, TL01§16): said then, as a hint.
        self.hint = str(next((t for t in tools.load() if t["tool"] == name), {}).get("wrote_nothing", ""))
        self.image = Path(exe.binary.replace("\\", "/")).name
        self.mo2 = inst.root / dryrun.MO2_EXE
        if not self.mo2.is_file():
            raise Refused("ModOrganizer.exe was not found in the modlist's folder")
        self._launcher, self._running, self._poll = launcher, running, poll
        target = inst.output_mods.get(title, "")
        mod = inst.mod(target) if target else None
        self.places = [p for p in ([mod.folder] if mod is not None and mod.folder is not None else [])
                       + [inst.overwrite_dir] if p.is_dir()]
        self.files = watch_files
        self.output_mod = target
        self.state = "starting"            # starting, running, done, failed, stopped
        self.message = ""
        self.started = time.time()
        self.ended: float | None = None
        self.changed: list[str] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_end: Callable[[], None] | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="tool", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def public(self) -> dict:
        return {"title": self.title, "state": self.state, "message": self.message, "output_mod": self.output_mod,
                "seconds": int((self.ended or time.time()) - self.started), "changed": self.changed[:200],
                "changed_count": len(self.changed), "by_itself": bool(self.switches), "profile": self.inst.profile,
                "hint": self.hint if self.state == "done" and not self.changed else "", "own_log": self.own_log}

    def _run(self) -> None:
        try:
            self._do()
        except Refused as e:
            self.state, self.message = "failed", logbook.mask(str(e))
            log.error("%s", e)
        except Exception as e:
            self.state, self.message = "failed", "an error inside ModTrap: " + logbook.why(e)
            log.error("starting the tool failed: %s", logbook.why(e))
        self.ended = time.time()
        if self.on_end:
            try:
                self.on_end()
            except Exception as e:
                log.warn("after the tool: %s", logbook.why(e))

    def _do(self) -> None:
        if self._running(self.image):
            raise Refused("%s is already running: close it first, so that ModTrap can tell when its own start of "
                          "it has ended" % self.image)
        before = _snapshot(self.places, self.files)
        cmd = [str(self.mo2), "-p", self.inst.profile, "run", "-e"] + (["-a", self.arguments] if self.switches else []) + [self.title]
        if self.switches:
            log.info("starting “%s” through MO2 (profile '%s') with its own switches to do its work and close by itself "
                     "(%s); ModTrap waits for it to close", self.title, self.inst.profile, " ".join(self.switches))
        else:
            log.info("starting “%s” through MO2 (profile '%s'); it is yours to work, ModTrap waits for it to close",
                     self.title, self.inst.profile)
        try:
            proc = self._launcher(cmd, str(self.mo2.parent))
        except OSError as e:
            raise Refused("MO2 could not be started: " + logbook.why(e)) from None
        self.state = "running"
        seen, gone_since, closed_at = False, None, None
        while True:
            if self._stop.wait(self._poll):
                self.state, self.message = "stopped", "ModTrap stopped waiting; the tool is left as it is"
                log.warn("stopped waiting for “%s”", self.title)
                return
            alive = self._running(self.image)
            mo2_gone = proc.poll() is not None
            if alive:
                seen, gone_since = True, None
            elif mo2_gone and (alive is None or seen or time.time() - self.started > 30):
                gone_since = gone_since or time.time()
                if alive is None or time.time() - gone_since > self._grace:
                    break
            elif alive is False and seen:
                # The tool has gone and MO2 has not. MO2 ends by itself after the tool, unless it stops to show a
                # message: one of its plugins failing at the end of a command-line run does that (MO01§9). Only
                # such a message is closed, as a click on its X does; a MO2 that waits for something else is
                # waited for as before.
                gone_since = gone_since or time.time()
                if time.time() - gone_since > self._grace:
                    try:
                        hit = self._dismiss(dryrun.MO2_EXE)
                    except Exception:
                        hit = False
                    if hit and closed_at is None:
                        closed_at = time.time()
                        log.info("“%s” has closed; MO2 had stopped at a message of its own afterwards, which ModTrap "
                                 "closed (as a click on its X does)", self.title)
                    if closed_at is not None and time.time() - closed_at > MO2_STAYS:
                        log.warn("MO2 is still open %d s after its message was closed; the tool's run is over, so "
                                 "ModTrap goes on", MO2_STAYS)
                        break
            if time.time() - self.started > TIME_LIMIT:
                raise Refused("“%s” was still open after %d hours; ModTrap stopped waiting" % (self.title, TIME_LIMIT // 3600))
        self.own_log = toollog.after_run(self.title, self._binary, self.started, self._keep_logs)
        after = _snapshot(self.places, self.files)
        roots = [(str(p), p.name) for p in self.places]
        changed = []
        for path, sig in sorted(after.items()):
            if before.get(path) != sig:
                short = next((name + "/" + os.path.relpath(path, root).replace("\\", "/") for root, name in roots
                              if fold(path).startswith(fold(root))), Path(path).name)
                changed.append(short)
        self.changed = changed
        self.state = "done"
        took = int(time.time() - self.started)
        if changed:
            log.info("“%s” closed after %d s: %d file(s) of its output were written", self.title, took, len(changed))
            for c in changed[:20]:
                log.info("  %s", c)
        else:
            log.warn("“%s” closed after %d s and none of its output files changed: it may not have been run to "
                     "the end", self.title, took)
            if self.hint:
                log.info("%s", self.hint)


__all__ = ["ToolJob", "Refused"]
