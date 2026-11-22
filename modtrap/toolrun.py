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
PRESS_AFTER = 8.0              # seconds a tool's window is given before ModTrap looks for its run button
PRESS_EVERY = 4.0              # and between two looks
PRESS_LIMIT = 300.0            # after this long without a button that can be pressed, the tool is left to the owner
PRESS_AGAIN = 60.0             # a press after which the tool's log shows no run begun is taken as not having landed
CLOSE_AFTER = 3.0              # seconds after the tool's log says its run has finished, before its window is asked to close
HELPER_SECONDS = 45


def press_button(image: str, automation_id: str) -> dict:
    """Presses one button in a tool's window, by the helper program `uia.py` (WHY§93): its own process, so that
    nothing it does wrong can end ModTrap. {"pressed", "enabled", "candidates", "why"}; never raises."""
    import json
    import subprocess
    import sys
    helper = Path(__file__).with_name("uia.py")
    try:
        got = subprocess.run([sys.executable, "-I", str(helper), "press", image, automation_id], capture_output=True,
                             timeout=HELPER_SECONDS, stdin=subprocess.DEVNULL)
        line = got.stdout.decode("utf-8", "replace").strip().splitlines()[-1] if got.stdout.strip() else ""
        data = json.loads(line) if line else {}
        if isinstance(data, dict) and "pressed" in data:
            return data
        return {"pressed": False, "enabled": None, "candidates": 0,
                "why": "the helper that presses the button ended without an answer (code %d)" % got.returncode}
    except subprocess.TimeoutExpired:
        return {"pressed": False, "enabled": None, "candidates": 0, "why": "the helper that presses the button did not answer in time"}
    except (OSError, ValueError) as e:
        return {"pressed": False, "enabled": None, "candidates": 0, "why": "the helper that presses the button could not be run: " + logbook.why(e)}


def press_spec(title: str, binary: str) -> dict | None:
    """For a tool that has no switch to run by itself, only a button: which button, and the lines of its own log
    that say its run began and ended (data, `tools.json`, "self_run" with "press")."""
    name, _kind = tools.of_executable(title, binary)
    entry = next((t for t in tools.load() if t["tool"] == name), {})
    spec = entry.get("self_run")
    return spec if isinstance(spec, dict) and isinstance(spec.get("press"), dict) and spec["press"].get("id") else None


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
                 grace: float = dryrun.GONE_GRACE, keep_logs: Path | None = None,
                 presser: Callable[[str, str], dict] = press_button, closer: Callable[[str], bool] | None = None,
                 press_times: tuple[float, float, float, float, float] = (PRESS_AFTER, PRESS_EVERY, PRESS_LIMIT, PRESS_AGAIN, CLOSE_AFTER)):
        exe = next((e for e in inst.executables if e.title == title), None)
        if exe is None:
            raise Refused("“%s” is not in this MO2's list of tools" % title)
        self.inst, self.title = inst, title
        self._dismiss, self._grace = dismiss, grace
        self._binary, self._keep_logs = exe.binary, keep_logs
        self.own_log: dict | None = None        # what the tool's own log of this run says (toollog, WHY§88)
        self.before: list[str] = []             # what ModTrap set right in the tool's own settings before the start (WHY§89)
        # Something to do before the start, in this job's own time (building a tool's patchers outside MO2, WHY§90):
        # called with a function that waits and says whether the owner stopped the job; returns what was done, in
        # words, or raises Refused when the start is not to go on.
        self.prepare: Callable[[Callable[[float], bool]], list[str]] | None = None
        self.arguments, self.switches = self_run_arguments(title, exe.binary, exe.arguments) if self_run else ("", [])
        # A tool run by pressing its own button, and closed when its own log says the run is over (WHY§93).
        self._press = press_spec(title, exe.binary) if self_run else None
        self._presser, self._closer, self._press_times = presser, closer, press_times
        self.drive = "wait" if self._press else ""           # wait, pressed, finished, left to the owner
        self.drive_note = ""
        self._launched = 0.0
        self._next_look = self._pressed_at = self._finished_at = 0.0
        self._presses = 0
        self._close_asked = False
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
        self.state = "starting"            # starting, preparing, running, done, failed, stopped
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
                "changed_count": len(self.changed), "by_itself": bool(self.switches) or self.drive in ("wait", "pressed", "finished"),
                "drive": self.drive, "drive_note": self.drive_note, "profile": self.inst.profile,
                "hint": self.hint if self.state == "done" and not self.changed else "", "own_log": self.own_log, "before": list(self.before)}

    def _own_log(self) -> str:
        spec = toollog.spec_for(self.title, self._binary)
        if spec is None:
            return ""
        folder = Path(self._binary.replace("\\", "/")).parent / str(spec["folder"])
        path = toollog.newest(folder, str(spec.get("pattern", "*.log")), self._launched)
        try:
            return toollog.read(path) if path is not None else ""
        except OSError:
            return ""

    def _drive_on(self) -> None:
        """One step of running a tool by its own button (WHY§93): look for the button and press it once it can be
        pressed; then read the tool's own log for the lines that say a run began and that it ended; then ask the
        window to close. Whatever does not go as known leaves the tool open and to the owner: nothing is guessed."""
        after, every, limit, again, close_after = self._press_times
        now = time.time()
        spec = self._press or {}
        if self.drive == "wait":
            if now - self._launched < after or now < self._next_look:
                return
            self._next_look = now + every
            got = self._presser(self.image, str(spec["press"]["id"]))
            if got.get("pressed"):
                self._presses += 1
                self.drive, self._pressed_at = "pressed", now
                self.drive_note = "ModTrap pressed its run button; it closes when its own log says the run has finished"
                log.info("“%s” was ready: ModTrap pressed its run button%s", self.title,
                         " again" if self._presses > 1 else "")
            elif now - self._launched > limit:
                self.drive = "left to the owner"
                self.drive_note = "ModTrap did not press its run button (%s). It is yours to run, then close." % (
                    got.get("why") or "it could not be pressed")
                log.warn("“%s”: %s", self.title, self.drive_note)
            else:
                self.drive_note = "waiting for its run button: " + str(got.get("why") or "not ready yet")
        elif self.drive == "pressed":
            text = self._own_log()
            began = str(spec.get("began", ""))
            ended = str(spec.get("ended", ""))
            at = text.rfind(began) if began else -1
            if at >= 0 and ended and text.find(ended, at) >= 0:
                self.drive, self._finished_at = "finished", now
                self.drive_note = "its own log says the run has finished; ModTrap closes it"
                log.info("“%s”: its own log says the run has finished", self.title)
            elif at < 0 and now - self._pressed_at > again:
                if self._presses < 3:
                    self.drive, self._next_look = "wait", now                # the press did not land: look again
                else:
                    self.drive = "left to the owner"
                    self.drive_note = ("ModTrap pressed its run button %d times and its log shows no run begun. It is "
                                       "yours to run, then close." % self._presses)
                    log.warn("“%s”: %s", self.title, self.drive_note)
        elif self.drive == "finished" and not self._close_asked and now - self._finished_at >= close_after:
            self._close_asked = True
            try:
                asked = bool(self._closer(self._binary)) if self._closer is not None else False
            except Exception:
                asked = False
            if not asked:
                self.drive_note = "its run has finished; its window did not take ModTrap's asking to close: close it"
                log.warn("“%s”: %s", self.title, self.drive_note)

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
        if self.prepare is not None:
            self.state = "preparing"
            self.before += self.prepare(self._stop.wait)
            if self._stop.is_set():
                self.state, self.message = "stopped", "ModTrap stopped before the tool was started through MO2"
                return
        before = _snapshot(self.places, self.files)
        cmd = [str(self.mo2), "-p", self.inst.profile, "run", "-e"] + (["-a", self.arguments] if self.switches else []) + [self.title]
        if self._press:
            log.info("starting “%s” through MO2 (profile '%s'); it has no switch to run by itself, so ModTrap presses its "
                     "run button once it is ready, and closes it when its own log says the run has finished",
                     self.title, self.inst.profile)
        elif self.switches:
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
        self._launched = time.time()
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
                if self.drive in ("wait", "pressed", "finished"):
                    self._drive_on()
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
