"""ModTrap's endpoints (DESIGN§4). Version 0.1 reads only: the instance, its mods, its plugins and what depends on
what. Nothing here writes to an instance; the one thing saved is the chosen folder, in ModTrap's own settings."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import shutil
import threading
import time
from pathlib import Path
from typing import Callable

import tempfile

from . import (NAME, VERSION, adding, browse, dryrun, fomod, instance, locate, logbook, model, paths, plugin, records,
               savelog, sessions, steps, toolrun, tools, unpack)
from . import process, version
from .server import Bad


def probejob_steps() -> tuple:
    from . import probejob                     # imported late: nothing of the probe is loaded for looking only
    return probejob.STEPS

log = logbook.get("app")


class HeaderCache:
    """Plugin headers by path, size and time: a rescan re-reads only the plugins that changed."""

    def __init__(self) -> None:
        self._seen: dict[str, tuple[int, int, object]] = {}
        self.read_count = 0
        self.touched: set[str] = set()

    def load(self, path: Path) -> None:
        """Headers kept from an earlier run of ModTrap: a start then re-reads only the plugins that changed."""
        try:
            with open(path, "rb") as f:
                data = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            for key, (size, mtime, ok, flags, author, description, masters) in data.items():
                got: object = (plugin.Header(flags, author, description, tuple(masters)) if ok
                               else plugin.Unreadable(str(description)))
                self._seen.setdefault(key, (int(size), int(mtime), got))
        except (OSError, ValueError, TypeError):
            return

    def save(self, path: Path) -> None:
        out = {}
        for key in self.touched:
            size, mtime, got = self._seen[key]
            if isinstance(got, plugin.Header):
                out[key] = [size, mtime, True, got.flags, got.author, got.description, list(got.masters)]
            else:
                out[key] = [size, mtime, False, 0, "", str(got), []]
        paths.write_atomic(path, json.dumps(out, ensure_ascii=False).encode("utf-8"))

    def read(self, path: Path) -> plugin.Header:
        try:
            st = path.stat()
        except OSError as e:
            raise plugin.Unreadable("the file could not be opened (%s)" % type(e).__name__) from None
        key = str(path)
        self.touched.add(key)
        hit = self._seen.get(key)
        if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
            got = hit[2]
        else:
            self.read_count += 1
            try:
                got = plugin.read(path)
            except plugin.Unreadable as e:
                got = e
            self._seen[key] = (st.st_size, st.st_mtime_ns, got)
        if isinstance(got, plugin.Unreadable):
            raise got
        return got  # type: ignore[return-value]


# What starts something through MO2's command line. MO2 hands such a command to a MO2 that is already open,
# whichever modlist that one is for (MO01§9): with another modlist's MO2 open it would go to the wrong one (WHY§77).
LAUNCHES_MO2 = frozenset(("/api/dryrun/start", "/api/records/start", "/api/tool/start", "/api/demaster/start",
                          "/api/probe/start", "/api/mo2/open"))
OTHER_MO2 = ("Another Mod Organizer is open, for another modlist. MO2 hands every command to the MO2 that is already "
             "open, so ModTrap's would go to the wrong modlist. Close that MO2: ModTrap then goes on.")

# The owner's settings (DESIGN§19): name -> default. Kept in ModTrap's own folder, for every session.
SETTINGS = {
    "auto_go": False,          # after the dry run, go ahead without asking when the plan leaves nothing to the owner
    "close_mo2": False,        # close this modlist's MO2 without asking when a step needs it closed
    "open_mo2_after": False,   # start MO2 again once a demaster is in place
    "follow": True,            # show the Process tab when a demaster starts
    "script_props": True,      # take script properties that point at the mod out (MT4); off: they are left to the owner
    "retire_copies": True,     # after a tool's run, take ModTrap's own copy of a plugin the tool made anew out of the way
    "auto_tools": False,       # after the demaster, start the tools that are to run again, one after another
    "tools_self": True,        # a tool with switches of its own to work and close by itself is started with them (WHY§84)
    "tool_versions": True,     # before the patcher framework starts: library versions its last log shows as not fitting are set right (MT27)
    "tool_prebuild": True,     # and patchers its last log shows as not built are built outside MO2 first (MT28)
    "mo2_leave_alone": True,   # a compiler a tool's log shows crashing inside MO2 is added to MO2's list of programs it leaves alone (MT32)
}

NEEDS_SAME_VERSION = frozenset(("/api/dryrun/start", "/api/records/start", "/api/tool/start", "/api/demaster/start",
                                "/api/demaster/install", "/api/add/run", "/api/probe/start"))


class Api:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache = HeaderCache()
        self.status = "none"            # none, reading, ready, error
        self.message = ""
        self.folder = ""
        self.profile = ""
        self.model: model.Model | None = None
        self._run = 0
        self._lists: dict[str, tuple[object, dict]] = {}
        self._deep: dict[tuple, dict | None] = {}     # steps.look_deeper by (reading, mods); None while going
        self._adding: dict[tuple, dict | None] = {}   # adding.analyse by (reading, mods); None while going
        self._making_tools = 0                        # readings of what the tools made that are going (WHY§92)
        self._installed: tuple[object, dict] | None = None    # adding.installed_from of the current reading
        self._staged: dict[str, dict] = {}            # archives taken in, unpacked in the session's folder, by id
        self.seven_zip: Path | None = None            # replaced in tests; else the owner's own 7-Zip is looked for
        self.job: dryrun.Job | None = None
        self.launcher = dryrun.launch          # replaced in tests
        self.running = dryrun.image_running
        self.program_paths = dryrun.winauto.running_paths     # which MO2 is running (WHY§58); replaced in tests
        self.ask_close = dryrun.winauto.ask_to_close          # asks this modlist's MO2 to close; replaced in tests
        self._mo2_seen: tuple[float, dict] = (0.0, {})
        self._mo2_ours = False                  # the MO2 that is running was started by ModTrap for a run (WHY§67)
        self._code_seen: tuple[float, dict | None] = (0.0, None)
        self.poll = 1.0
        self.store = sessions.Store()
        self.session: sessions.Session | None = None
        self.log_epoch = 0                     # goes up when the log is replaced: the page then reads it afresh
        self.on_quit: Callable[[], None] | None = None
        self.changes = None                    # the endpoints that change a modlist; None: switched off (WHY§44)
        self.tooljob: toolrun.ToolJob | None = None
        self.recjob: records.Job | None = None
        self.saver = savelog.SaveJob()         # "Save this session" (WHY§48)
        self.closer = dryrun.close_program     # asks xEdit to close after a script (XE01§11); replaced in tests
        self.dismiss = dryrun.winauto.close_message   # closes a message MO2 stops at after a run (MO01§9); replaced in tests
        self.direct_launcher = dryrun.launch   # starts a program by itself, outside MO2 (WHY§90); replaced in tests
        self.button_presser = toolrun.press_button      # presses a tool's own run button (WHY§93); replaced in tests
        self.press_times = (toolrun.PRESS_AFTER, toolrun.PRESS_EVERY, toolrun.PRESS_LIMIT, toolrun.PRESS_AGAIN, toolrun.CLOSE_AFTER)
        self.prebuild_times: dict = {}         # shorter waits, in tests
        self.presser = dryrun.winauto.press_module_selection_ok   # presses OK in xEdit's module selection (XE01§13)

    # --- sessions (MT20, WHY§33) -----------------------------------------------------------------------------------

    def _log_file(self, s: sessions.Session) -> Path:
        return self.store.dir(s.id) / "log.json"

    def save_log(self) -> None:
        """The session's log, written to its folder (the lines are already masked)."""
        s = self.session
        if s is None:
            return
        try:
            paths.write_atomic(self._log_file(s), json.dumps(logbook.dump(), ensure_ascii=False).encode("utf-8"))
        except OSError as e:
            log.warn("the session's log could not be saved: %s", logbook.why(e))

    def _enter(self, s: sessions.Session) -> None:
        """Makes `s` the session in use: the last one's log is saved, this one's log and last job come back."""
        prev = self.session
        if prev is not None and prev.id == s.id:
            self.session = s
            return
        self.save_log()
        lines: list = []
        try:
            with open(self._log_file(s), "rb") as f:
                lines = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
        except (OSError, ValueError):
            pass
        logbook.load(lines if isinstance(lines, list) else [])
        self.log_epoch += 1
        self.session = s
        self._load_staged()
        self.job = None
        if s.last_job:
            d = self.store.dir(s.id) / "jobs" / s.last_job
            if d.is_dir():
                self.job = dryrun.PastJob(d)
        settings = paths.load_settings()
        settings["session"] = s.id
        try:
            paths.save_settings(settings)
        except OSError:
            pass

    def restore(self) -> bool:
        """At start: the session ModTrap was closed in, with its modlist read again. False when there is none."""
        sid = paths.load_settings().get("session")
        if not isinstance(sid, str) or not sid:
            return False
        try:
            s = self.store.get(sid)
        except sessions.Refused:
            return False
        self.open(s.folder, s.profile or None, session=s)
        return True

    def _session_or_bad(self, sid: object) -> sessions.Session:
        if sid is None and self.session is not None:
            return self.session
        if not isinstance(sid, str):
            raise Bad("no session was named")
        try:
            return self.store.get(sid)
        except sessions.Refused as e:
            raise Bad(str(e)) from None

    def session_switch(self, body: dict) -> dict:
        s = self._session_or_bad(body.get("id"))
        if self._busy():
            raise Bad("a dry run is going; switch sessions when it has ended")
        cur = self.session
        if cur is not None and cur.key == s.key and self.status == "ready" and (s.profile or self.profile) == self.profile:
            self._enter(s)                      # the same modlist is already read
            log.info("switched to session '%s'", s.name)
        else:
            self.open(s.folder, s.profile or None, session=s)
        return {"status": self.status}

    def session_new(self) -> dict:
        """Another session on the modlist that is open. It waits until the session holding the modlist is finished."""
        cur = self.session
        if cur is None:
            raise Bad("open a modlist first")
        if self._busy():
            raise Bad("a dry run is going; start a new session when it has ended")
        try:
            s = self.store.create(cur.folder, self.profile)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        self._enter(s)
        log.info("new session '%s' on <modlist>%s", s.name,
                 ": it waits until the session holding this modlist is finished" if s.status == sessions.WAITING else "")
        return {"id": s.id, "status": s.status}

    def session_rename(self, body: dict) -> dict:
        s = self._session_or_bad(body.get("id"))
        name = body.get("name")
        if not isinstance(name, str):
            raise Bad("a session needs a name", "name")
        try:
            s = self.store.rename(s.id, name)
        except sessions.Refused as e:
            raise Bad(str(e), "name") from None
        if self.session is not None and self.session.id == s.id:
            self.session = s
        return {"id": s.id, "name": s.name}

    def session_finish(self, body: dict) -> dict:
        """Finishing a session frees its modlist for the session that waits for it. First the check that it is
        safe: nothing of this session may still be going. (When ModTrap can demaster, every step of the session's
        jobs must also be done and the modlist's health check clean: DESIGN§14.)"""
        s = self._session_or_bad(body.get("id"))
        mine = self.session is not None and self.session.id == s.id
        if mine and self._busy():
            raise Bad("this session's dry run is still going: let it end, or stop it, before finishing the session")
        try:
            done, nxt = self.store.finish(s.id)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        log.info("session '%s' is finished: nothing of it was still going", done.name)
        if nxt is not None:
            log.info("session '%s' now holds the modlist and is unlocked", nxt.name)
        if mine:
            self.session = done
            if nxt is not None:
                self._enter(nxt)
        elif self.session is not None and nxt is not None and self.session.id == nxt.id:
            self.session = nxt
        self.save_log()
        return {"finished": done.id, "unlocked": nxt.id if nxt else None}

    def session_ui(self, body: dict) -> dict:
        ui = body.get("ui")
        if self.session is None or not isinstance(ui, dict):
            raise Bad("there is no session to remember that for")
        try:
            self.store.set_ui(self.session.id, ui)
        except sessions.Refused as e:
            raise Bad(str(e)) from None
        self.session.ui = ui
        self.save_log()                 # kept up to date as the owner works, in case the window is simply closed
        return {"saved": True}

    def quit(self, body: dict) -> tuple[dict, Callable[[], None] | None]:
        if self._busy() and body.get("force") is not True:
            raise Bad("a dry run is going. Quitting now leaves xEdit open for you to close (it changes nothing), and "
                      "the dry run's outcome is not kept.")
        if self._busy() and self.job is not None:
            self.job.stop()
        log.info("ModTrap is closing; the session is saved")
        self.save_log()
        return {"quit": True}, self.on_quit

    def handover(self) -> tuple[dict, Callable[[], None] | None]:
        """Another start of ModTrap on this PC takes over (WHY§68): this one saves and closes, unless it is in the
        middle of something."""
        if self._busy() or (self.changes is not None and self.changes.busy()) or \
                (self.tooljob is not None and self.tooljob.state in ("starting", "preparing", "running")):
            raise Bad("in the middle of a job")
        log.info("ModTrap was started again on this PC: this one (%s) saves its session and closes", VERSION)
        answer, after = self.quit({})
        return dict(answer, version=VERSION), after

    def _locked(self) -> str:
        """Why the session in use may not start a job, or "" when it may."""
        s = self.session
        if s is None:
            return ""
        if s.status == sessions.FINISHED:
            return "this session is finished: it can be looked at, but work goes on in a new session"
        if s.status == sessions.WAITING:
            holder = self.store.holder(s.folder)
            return ("this session is waiting: session “%s” still holds this modlist. Finish that one first; two "
                    "sessions working on one modlist would trip over each other" % (holder.name if holder else "another"))
        return ""

    # --- reading an instance, off the request thread ---------------------------------------------------------------

    def open(self, folder: str, profile: str | None = None, wait: bool = False,
             session: sessions.Session | None = None) -> None:
        """Reads the modlist in `folder`. With `session`, into that session; otherwise into the session that holds
        this modlist, or a new one (MT20)."""
        folder = folder.strip().strip('"')
        if not folder:
            raise Bad("give the modlist's folder", "folder")
        if self._busy():
            raise Bad("a dry run is going; open another modlist when it has ended")
        with self._lock:
            self._run += 1
            run = self._run
            self.status, self.message, self.folder, self.profile = "reading", "", folder, profile or ""
        t = threading.Thread(target=self._read, args=(run, folder, profile, session), name="read-instance", daemon=True)
        t.start()
        if wait:
            t.join()

    def _cache_file(self, folder: str) -> Path:
        key = hashlib.sha256(sessions.modlist_key(folder).encode("utf-8")).hexdigest()[:20]
        return paths.home() / "cache" / ("headers-%s.json" % key)

    def _read(self, run: int, folder: str, profile: str | None, session: sessions.Session | None = None) -> None:
        logbook.set_masks({"<modlist>": folder, "<modtrap>": str(paths.home())})
        log.info("reading the modlist in <modlist>")
        try:
            inst = instance.load(Path(folder), profile)
            logbook.set_masks({"<modlist>": folder, "<game>": str(inst.game_dir) if inst.game_dir else None,
                               "<mods>": str(inst.mods_dir), "<modtrap>": str(paths.home())})
            self._cache.touched = set()
            self._cache.load(self._cache_file(folder))
            before = self._cache.read_count
            m = model.build(inst, read=self._cache.read)
        except instance.Unusable as e:
            log.warn("the folder cannot be read: %s", str(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", logbook.mask(str(e)), None
            return
        except Exception as e:      # never leave the page waiting on "reading"
            log.error("reading the modlist failed: %s", logbook.why(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", "reading failed: " + logbook.why(e), None
            return
        with self._lock:
            if run != self._run:
                return
        try:
            s = session or self.store.open_for(folder, inst.profile)
            new = self.session is None or self.session.id != s.id
            self._enter(s)
            if s.folder != folder or s.profile != inst.profile:
                s.folder, s.profile = folder, inst.profile
                self.store.save(s)
            if new:
                log.info("session '%s' (%s)", s.name, {"active": "it holds this modlist", "waiting": "waiting, locked",
                                                       "finished": "finished"}[s.status])
        except (sessions.Refused, OSError) as e:
            log.error("the session could not be opened: %s", str(e) if isinstance(e, sessions.Refused) else logbook.why(e))
            with self._lock:
                if run == self._run:
                    self.status, self.message, self.model = "error", "the session could not be opened", None
            return
        try:
            self._cache.save(self._cache_file(folder))
        except OSError:
            pass
        real = [x for x in inst.mods if x.kind == "mod"]
        log.info("profile '%s': %d mods (%d enabled), %d plugins, %d header(s) read, %d problem(s)",
                 inst.profile, len(real), sum(x.enabled for x in real), len(m.order),
                 self._cache.read_count - before, len(m.issues))
        for note in inst.notes:
            log.warn("%s", note)
        settings = paths.load_settings()
        recent = [r for r in settings.get("recent", []) if isinstance(r, str) and r != folder]
        settings.update({"folder": folder, "profile": inst.profile, "recent": [folder, *recent][:8]})
        try:
            paths.save_settings(settings)
        except OSError as e:
            log.warn("the chosen folder could not be remembered: %s", logbook.why(e))
        with self._lock:
            if run != self._run:
                return
            self.status, self.message, self.model, self.profile = "ready", "", m, inst.profile

    def locate(self, body: dict) -> dict:
        """A folder dropped on the page (WHY§30): its name and its ModOrganizer.ini. Finds it on disk and opens it."""
        name, data = body.get("name"), body.get("ini")
        if name is not None and (not isinstance(name, str) or not name or len(name) > 255 or "/" in name
                                 or "\\" in name):
            raise Bad("the dropped folder's name is not usable")
        if not isinstance(data, str):
            raise Bad("the dropped folder's ModOrganizer.ini did not arrive")
        try:
            ini = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            raise Bad("the dropped folder's ModOrganizer.ini did not arrive whole") from None
        if not ini or len(ini) > locate.INI_CAP:
            raise Bad("that ModOrganizer.ini is empty or larger than ModTrap reads")
        settings = paths.load_settings()
        recents = [r for r in [settings.get("folder"), *settings.get("recent", [])] if isinstance(r, str) and r]
        folder, how = locate.find(name, ini, recents)
        if folder is None:
            log.warn("a dropped modlist folder was not found on this PC's drives")
            raise Bad("ModTrap could not find that folder on this PC by itself (a browser never tells a page where "
                      "a dropped folder is). Paste the folder's path into the box instead: in Explorer, click the "
                      "address bar and copy it.")
        log.info("the dropped folder was found through %s", how)
        self.open(str(folder))
        return {"status": "reading", "how": how}

    # --- the dry run (DESIGN§6.1, DESIGN§6.2) ------------------------------------------------------------------------

    def _mods(self, body: dict) -> list[str]:
        mods = body.get("mods")
        if not isinstance(mods, list) or not mods or len(mods) > 50 or not all(isinstance(x, str) and x for x in mods):
            raise Bad("tick at least one mod")
        return mods

    def working(self) -> list[dict]:
        """ModTrap's own reading and scanning that is still going (WHY§92): [{"key", "text"}]. While any of it goes,
        nothing that changes the modlist or starts a program is begun: the page greys those buttons, and the
        starts themselves are refused (`unsettled`)."""
        out = []
        if self.status == "reading":
            out.append({"key": "modlist", "text": "reading the modlist"})
        m = self.model
        if m is not None:
            if any(v is None for k, v in list(self._deep.items()) if k[0] == id(m)):
                out.append({"key": "steps", "text": "looking into the ticked mods' folders and the tools' plugins, for the steps"})
            if any(v is None for k, v in list(self._adding.items()) if k[0] == id(m)):
                out.append({"key": "adding", "text": "reading the mods to add"})
        if self._making_tools:
            out.append({"key": "tools", "text": "reading what the modlist's tools made"})
        try:
            if any(r.get("state") in ("copying", "unpacking") for r in list(self._staged.values())):
                out.append({"key": "unpack", "text": "unpacking a dropped archive"})
        except Exception:
            pass
        return out

    def unsettled(self) -> str:
        """Why nothing can be started just now, in words, or "" when ModTrap has finished its own reading and
        scanning. The modlist being read keeps the words the page already waits on."""
        if self.status != "ready":
            return "the modlist is being read"
        rest = [w["text"] for w in self.working()]
        return "ModTrap is still at work (%s)" % "; ".join(rest) if rest else ""

    def _busy(self) -> bool:
        if self.tooljob is not None and self.tooljob.state in ("starting", "preparing", "running"):
            return True
        if self.recjob is not None and self.recjob.state not in ("done", "failed", "stopped"):
            return True
        if self.changes is not None and self.changes.busy():
            return True
        return self.job is not None and self.job.state not in ("done", "failed", "stopped")

    # --- starting one of the modlist's tools through MO2 (DESIGN§16.8 step 5) ----------------------------------------

    def tool_start(self, body: dict) -> dict:
        m = self._need()
        title = body.get("title")
        if not isinstance(title, str) or not title or len(title) > 300:
            raise Bad("which tool to start did not arrive")
        with self._lock:
            if self._busy():
                raise Bad("something else is going; wait for it to end")
            if self.unsettled():
                raise Bad(self.unsettled() + "; try again in a moment")
            if self._locked():
                raise Bad(self._locked())
            inst = m.instance
            exe = next((e for e in inst.executables if e.title == title), None)
            if exe is None:
                raise Bad("“%s” is not in this MO2's list of tools" % title)
            name, _kind = tools.of_executable(exe.title, exe.binary)
            memo: dict = {}
            made = [r.path for r in m.plugins.values() if r.path is not None
                    and any(e.tool == name for e in adding.generated(m, r, memo))]
            try:
                job = toolrun.ToolJob(inst, title, made, launcher=self._launch, running=self.running, poll=self.poll,
                                      self_run=self.settings().get("tools_self") is not False, dismiss=self.dismiss,
                                      keep_logs=self.store.dir(self.session.id) / "tool-logs" if self.session else None,
                                      presser=self.button_presser, closer=self.ask_close, press_times=self.press_times)
            except toolrun.Refused as e:
                raise Bad(str(e)) from None

            def ended() -> None:
                self.save_log()
                if job.state == "done" and self.session is not None:
                    try:
                        from . import history
                        history.History(self.store.dir(self.session.id)).add(
                            "tool ran", tool=title, files=len(job.changed), seconds=int((job.ended or time.time()) - job.started),
                            why="started by ModTrap through MO2" + (", to run and close by itself" if job.switches else ""))
                    except Exception:
                        pass
                    if self.changes is not None:
                        self.changes.tool_ran(title, len(job.changed))     # what makes its step done (WHY§91)
                    if not job.changed:
                        job.retry = self._worth_again(exe, job)            # said to the page: the row may start it once more
                if job.state == "done" and self.folder and self.status == "ready":
                    self.open(self.folder, self.profile or None, session=self.session, wait=True)   # its output, read again
                    if self.changes is not None:
                        self.changes.retire_remade()         # a copy of ModTrap's that the run made needless (WHY§80)
            job.on_end = ended
            job.before = self._fit_tool(exe, job.image) + self._leave_alone(exe, job.image)
            gap = self._unbuilt_tool(exe)
            if gap is not None:
                job.prepare = lambda wait: self._prebuild_tool(exe, gap, wait)
            self.tooljob = job
            if self.changes is not None:
                # With a demaster in place, what the tool is about to write over is kept for Revert (WHY§81).
                target = inst.mod(inst.output_mods.get(title, "")) if inst.output_mods.get(title) else None
                self.changes.before_tool(title, made, target.folder if target is not None else None)
        job.start()
        return job.public()

    def _fit_tool(self, exe, image: str) -> list[str]:
        """Before the patcher framework is started (MT27, WHY§89): if its newest log shows that the library versions
        its profile is still set to do not fit the program, they are set to the program's own pair, unless the
        owner's setting says no. Returns what was done or found, in words. Never raises: the start goes on."""
        from . import history, toolfit
        try:
            if not toolfit.is_tool(exe.title, exe.binary) or self.running(image):
                return []
            folder = Path(exe.binary.replace("\\", "/")).parent
            found = toolfit.check(folder)
            if not found:
                return []
            if self.settings().get("tool_versions") is False or self.session is None:
                said = ["%s. Left as it is: the setting to set them right is off" % toolfit.words(f).split(". ModTrap set")[0] for f in found]
                for x in said:
                    log.warn("%s", x)
                return said
            done = toolfit.apply(folder, found, self.store.dir(self.session.id) / "tool-settings")
            said = []
            for f in done:
                history.History(self.store.dir(self.session.id)).add(
                    "tool settings changed", tool=exe.title, file=toolfit.SETTINGS, profile=f["profile"],
                    was="Mutagen %s, Synthesis %s" % (f["was"]["mutagen"], f["was"]["synthesis"]),
                    now="Mutagen %s, Synthesis %s" % (f["now"]["mutagen"], f["now"]["synthesis"]),
                    why="its last log (%s) shows the versions set as not fitting this program" % f["log"], kept=f["kept"])
                text = toolfit.words(f) + ". A copy of its settings file as it was is kept with this session (%s)" % f["kept"]
                log.info("%s", text)
                said.append(text)
            return said
        except Exception as e:
            log.warn("the library versions of “%s” could not be checked or set: %s", exe.title, logbook.why(e))
            return []

    def _tool_log_text(self, exe) -> tuple[str, str]:
        """The tool's own newest log, whenever written: (its text, its name), ("", "") when there is none."""
        from . import toollog
        spec = toollog.spec_for(exe.title, exe.binary)
        if spec is None:
            return "", ""
        folder = Path(exe.binary.replace("\\", "/")).parent / str(spec["folder"])
        path = toollog.newest(folder, str(spec.get("pattern", "*.log")), 0.0)
        try:
            return (toollog.read(path), path.name) if path is not None else ("", "")
        except OSError:
            return "", ""

    def _leave_alone_spec(self, exe) -> tuple[list[str], str] | None:
        """For a tool whose data names it (TL01§22): the programs MO2 should leave alone, if the tool's newest log
        shows the crash that calls for it, and that log's name."""
        name, _kind = tools.of_executable(exe.title, exe.binary)
        spec = next((t for t in tools.load() if t["tool"] == name), {}).get("mo2_leave_alone")
        if not isinstance(spec, dict):
            return None
        text, log_name = self._tool_log_text(exe)
        try:
            if not text or not re.search(str(spec["when"]), text):
                return None
        except (re.error, KeyError):
            return None
        return [str(x) for x in spec.get("programs", [])], log_name

    def _leave_alone(self, exe, image: str) -> list[str]:
        """Before a tool is started (MT32, WHY§94): if its own newest log shows a compiler crashing inside MO2, the
        compiler is added to MO2's list of programs its virtual file system leaves alone, in MO2's settings file,
        with a copy of the file kept first. Only with MO2 closed, and unless the owner's setting says no. Returns
        what was done or found, in words. Never raises."""
        from . import history, mo2fix
        try:
            m = self.model
            got = self._leave_alone_spec(exe)
            if m is None or got is None or self.running(image):
                return []
            programs, log_name = got
            need = mo2fix.missing(m.instance.root, programs)
            if not need:
                return []
            what = ("its last log (%s) shows the compiler crashing when started inside MO2; MO2's list of programs it "
                    "leaves alone does not name %s" % (log_name, " or ".join(need)))
            if self.settings().get("mo2_leave_alone") is False or self.session is None:
                log.warn("“%s”: %s. Left as it is: the setting to add them is off", exe.title, what)
                return ["%s%s. Left as it is: the setting to add them is off" % (what[0].upper(), what[1:])]
            self.wait_mo2_gone(seconds=10.0)
            if self.mo2()["state"] != "closed":
                why = ("MO2 is open, and writes its settings when it closes: close MO2, then start the tool from here again"
                       if self.mo2()["state"] == "open" else "ModTrap cannot tell on this PC whether MO2 is closed, so it leaves MO2's settings alone")
                log.warn("“%s”: %s. %s", exe.title, what, why)
                return ["%s%s. %s" % (what[0].upper(), what[1:], why)]
            done = mo2fix.add(m.instance.root, need, self.store.dir(self.session.id) / "tool-settings")
            if not done["added"]:
                return []
            history.History(self.store.dir(self.session.id)).add(
                "mo2 settings changed", file=mo2fix.INI, was="not on the list of programs MO2 leaves alone",
                now="added: " + ", ".join(done["added"]), kept=done["kept"],
                why="“%s”'s last log (%s) shows the compiler crashing inside MO2" % (exe.title, log_name))
            text = ("%s%s. ModTrap added %s to that list, in MO2's settings file (Settings, Workarounds, Executables "
                    "Blacklist in MO2); a copy of the file as it was is kept with this session (%s)" % (
                        what[0].upper(), what[1:], " and ".join(done["added"]), done["kept"]))
            log.info("“%s”: %s", exe.title, text)
            return [text]
        except Exception as e:
            log.warn("MO2's list of programs it leaves alone could not be checked or changed: %s", logbook.why(e))
            return []

    def _worth_again(self, exe, job) -> str:
        """After a tool closed without output: is there a reason to start it once more that is not a guess? Either
        something ModTrap sets right before a start is still to be set right (a remedy its last run called for),
        or its log shows a refusal by Windows of the kind that passes. "" when neither. Never raises."""
        from . import toolfit
        try:
            if toolfit.is_tool(exe.title, exe.binary):
                folder = Path(exe.binary.replace("\\", "/")).parent
                if self.settings().get("tool_versions") is not False and toolfit.check(folder):
                    return "its library versions are to be set right first"
                if self.settings().get("tool_prebuild") is not False and toolfit.unbuilt(folder):
                    return "its patchers are to be built outside MO2 first"
            got = self._leave_alone_spec(exe)
            if got is not None and self.settings().get("mo2_leave_alone") is not False and self.model is not None:
                from . import mo2fix
                if mo2fix.missing(self.model.instance.root, got[0]):
                    return "the compiler is to be added to the programs MO2 leaves alone first"
            name, _kind = tools.of_executable(exe.title, exe.binary)
            passing = next((t for t in tools.load() if t["tool"] == name), {}).get("passing")
            if isinstance(passing, str) and passing:
                text, _n = self._tool_log_text(exe)
                if re.search(passing, text):
                    return "its log shows Windows refusing it a start, of the kind that passes"
        except Exception:
            pass
        return ""

    def _unbuilt_tool(self, exe) -> dict | None:
        """For the patcher framework: what its newest log names as not built, if the owner's setting lets ModTrap
        build it outside MO2. None for any other tool. Never raises."""
        from . import toolfit
        try:
            if not toolfit.is_tool(exe.title, exe.binary) or self.settings().get("tool_prebuild") is False:
                return None
            return toolfit.unbuilt(Path(exe.binary.replace("\\", "/")).parent)
        except Exception:
            return None

    def _prebuild_tool(self, exe, gap: dict, wait: Callable[[float], bool]) -> list[str]:
        """Before the patcher framework is started through MO2 (MT28, WHY§90): its newest log names patchers whose
        build is not there, so the program is opened by itself, outside MO2, until they are built, and closed
        again. Runs in the tool job's own time. Returns what was done, in words; raises toolrun.Refused when the
        patchers could not be built, since a start through MO2 would then only fail the same way."""
        from . import toolfit
        log.info("“%s”: its last log (%s) names %d patcher(s), %d of them not built. ModTrap opens it by itself, outside "
                 "MO2, so that it builds them; nothing in it is pressed, and it is closed again once they are built",
                 exe.title, gap["log"], gap["named"], gap["missing"])
        try:
            got = toolfit.prebuild(exe.binary, launcher=self.direct_launcher, closer=self.ask_close, stopped=wait,
                                   poll=self.poll, **self.prebuild_times)
        except OSError as e:
            raise toolrun.Refused("“%s” could not be opened by itself to build its patchers: %s" % (exe.title, logbook.why(e))) from None
        if got["settings_put_back"]:
            log.warn("“%s” had changed its settings file while it was open outside MO2: ModTrap put the file back as it was", exe.title)
        if got["why"] == "stopped":
            return []
        if not got["closed"]:
            raise toolrun.Refused("“%s” was opened outside MO2 to build its patchers and did not close when asked. Close "
                                  "it, then start it from here again." % exe.title)
        if not got["ok"]:
            raise toolrun.Refused("“%s” could not build its patchers outside MO2 either (%s; %d of %d built%s). Its own "
                                  "log (%s) has the errors; a start through MO2 would fail the same way, so ModTrap did "
                                  "not make one." % (exe.title, got["why"], got["built"], got["named"],
                                                     "; " + "; ".join(got["errors"]) if got["errors"] else "", got["log"] or "none written"))
        text = ("its last log (%s) showed %d of its %d patcher(s) as not built, so ModTrap opened it by itself, outside "
                "MO2, where it built them (%d of %d, in %d s), and closed it again without running anything" % (
                    gap["log"], gap["missing"], gap["named"], got["built"], got["named"], got["seconds"]))
        log.info("“%s”: %s", exe.title, text)
        return [text[0].upper() + text[1:]]

    # --- the record check (DESIGN§16.5): xEdit, read-only ----------------------------------------------------------

    def records_start(self, body: dict) -> dict:
        m = self._need()
        mods = body.get("mods")
        if not isinstance(mods, list) or not mods or len(mods) > 20 or not all(isinstance(x, str) and x for x in mods):
            raise Bad("which mods to check did not arrive")
        with self._lock:
            if self._busy():
                raise Bad("something else is going; wait for it to end")
            if self.unsettled():
                raise Bad(self.unsettled() + "; try again in a moment")
            if self._locked():
                raise Bad(self._locked())
            s = self.session
            try:
                p = records.plan(m, mods)
                base = (self.store.dir(s.id) if s is not None else paths.home()) / "jobs"
                job = records.Job(m, p, records.new_job_dir(base), launcher=self._launch, running=self.running,
                                  poll=self.poll, closer=self.closer, presser=self.presser)
            except (records.Refused, dryrun.Refused) as e:
                raise Bad(str(e)) from None
            job.on_end = self.save_log
            self.recjob = job
        logbook.set_masks({"<modlist>": self.folder, "<game>": str(m.instance.game_dir) if m.instance.game_dir else None,
                           "<mods>": str(m.instance.mods_dir), "<job>": str(job.dir), "<modtrap>": str(paths.home())})
        job.start()
        return job.public()

    def records_stop(self) -> dict:
        if self.recjob is None:
            raise Bad("no record check is going")
        self.recjob.stop()
        return self.recjob.public()

    # --- "Save this session" (WHY§48): the session's logs, cleaned, in one .7z to download -------------------------

    def save_start(self) -> dict:
        s = self.session
        if s is None:
            raise Bad("open a modlist first: there is no session to save yet")
        self.save_log()
        m = self.model
        session_dir = self.store.dir(s.id)

        def gather() -> tuple[list, savelog.Cleaner, str]:
            folders: dict[str, str | None] = {"<modlist>": self.folder or None, "<modtrap>": str(paths.home()),
                                              "<temp>": tempfile.gettempdir()}
            about = savelog.describe()
            about["session"] = {"name": s.name, "status": s.status, "created": s.created, "profile": s.profile}
            about["changes_allowed"] = self.changes is not None
            profile_dir = None
            if m is not None:
                inst = m.instance
                folders.update({"<game>": str(inst.game_dir) if inst.game_dir else None, "<mods>": str(inst.mods_dir),
                                "<overwrite>": str(inst.overwrite_dir), "<profiles>": str(inst.profiles_dir),
                                "<downloads>": str(inst.downloads_dir) if inst.downloads_dir else None})
                profile_dir = inst.profiles_dir / inst.profile
                real = [x for x in inst.mods if x.kind == "mod"]
                try:
                    xe = dryrun.find_xedit_exe(inst)
                except dryrun.Refused:
                    xe = None
                about["modlist"] = {
                    "game": inst.game_name, "profile": inst.profile, "mods": len(real),
                    "mods_enabled": sum(x.enabled for x in real),
                    "plugins_active": sum(1 for r in m.plugins.values() if r.active),
                    "problems": len(m.issues), "notes": list(inst.notes),
                    "game_folder": (inst.game_dir.name if inst.game_dir else ""),
                    "game_folder_inside_modlist": bool(inst.game_dir and str(inst.game_dir).lower().startswith(
                        str(inst.root).lower())),
                    "xedit": {"title": xe.title, "own_arguments": xe.arguments} if xe else None,
                    "tools": [{"title": e.title, "program": Path(e.binary.replace("\\", "/")).name,
                               "output_mod": inst.output_mods.get(e.title, "")} for e in inst.executables]}
            if self.changes is not None:
                try:
                    pr = self.changes.probe_public()
                    about["probe"] = {"state": pr.get("state", ""), "reason": pr.get("reason", ""),
                                      "steps": [[x.get("key"), x.get("result", ""), x.get("detail", "")] for x in pr.get("steps", [])]}
                except Exception:
                    about["probe"] = {"state": "unknown"}
            items = savelog.collect(session_dir, profile_dir, paths.home(), about)
            return items, savelog.Cleaner(folders), savelog.archive_name(s.name)

        if self.saver.start(gather):
            log.info("packing this session's logs for download")
        return self.saver.public()

    def save_take(self) -> tuple[Path, str] | None:
        """The packed archive, once, for the server to send and remove."""
        return self.saver.take()

    def history_events(self) -> dict:
        """Everything ModTrap changed in this session's modlist (MT15, DESIGN§12), newest first. Read only: the
        file is written by the jobs that change things."""
        s = self.session
        events: list = []
        if s is not None:
            try:
                with open(self.store.dir(s.id) / "history.jsonl", "rb") as f:
                    for ln in f.read(64 * 1024 * 1024).decode("utf-8", "replace").splitlines():
                        try:
                            e = json.loads(ln)
                        except ValueError:
                            continue
                        if isinstance(e, dict):
                            events.append(e)
            except OSError:
                pass
        out = {"events": events[::-1][:2000], "total": len(events), "jobs": [], "can_change": self.changes is not None}
        if self.changes is not None:                    # the jobs themselves, standing or not (WHY§67)
            out["jobs"] = ([dict(j, what="demaster") for j in self.changes.demaster_jobs()] +
                           [dict(j, what="add") for j in self.changes.jobs()])
            out["jobs"].sort(key=lambda j: j.get("when", ""), reverse=True)
        return out

    def tool_stop(self) -> dict:
        if self.tooljob is None:
            raise Bad("no tool was started from here")
        self.tooljob.stop()
        return self.tooljob.public()

    def dry_plan(self, body: dict) -> dict:
        if self._locked():
            raise Bad(self._locked())
        try:
            return dryrun.plan(self._need(), self._mods(body)).public()
        except dryrun.Refused as e:
            raise Bad(str(e)) from None

    def dry_start(self, body: dict) -> dict:
        m = self._need()
        with self._lock:
            if self._busy():
                raise Bad("a dry run is already going")
            if self.unsettled():
                raise Bad(self.unsettled() + "; try again in a moment")
            if self._locked():
                raise Bad(self._locked())
            s = self.session
            try:
                p = dryrun.plan(m, self._mods(body))
                base = self.store.dir(s.id) / "jobs" if s is not None else None
                job = dryrun.Job(m, p, dryrun.new_job_dir(base), launcher=self._launch, running=self.running,
                                 poll=self.poll, closer=self.closer, presser=self.presser)
            except dryrun.Refused as e:
                raise Bad(str(e)) from None
            job.on_end = self.save_log
            self.job = job
            if s is not None:
                s.last_job = job.id
                self.store.save(s)
        logbook.set_masks({"<modlist>": self.folder, "<game>": str(m.instance.game_dir) if m.instance.game_dir else None,
                           "<mods>": str(m.instance.mods_dir), "<job>": str(job.dir), "<modtrap>": str(paths.home())})
        job.start()
        return job.public()

    def _touched_for(self, mods: list[str]) -> tuple[dict | None, str]:
        """What a dry run of these mods told about the records they really change (XE01§18), and that dry run's
        id; (None, "") when no dry run at hand told it. The dry run in hand is looked at first, then this
        session's earlier ones: what a mod changes stays true after the modlist has moved on (WHY§66)."""
        want = sorted(mods)
        job = self.job
        if job is not None:
            pub = job.public()
            res = pub.get("result") or {}
            if pub.get("state") == "done" and sorted(pub.get("plan", {}).get("trapped_mods", [])) == want \
                    and res.get("touched") and "changes" in res:     # told by a script that tells stakes (WHY§69)
                return dict(res["touched"], **{"": res["changes"]}), str(pub.get("id", ""))
        s = self.session
        if s is None:
            return None, ""
        try:
            folders = sorted((p for p in (self.store.dir(s.id) / "jobs").iterdir()
                              if p.is_dir() and p.name.startswith("dryrun-")), reverse=True)[:12]
        except OSError:
            return None, ""
        for d in folders:
            try:
                with open(d / "job.json", "rb") as f:
                    meta = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
                if sorted(meta.get("plan", {}).get("trapped_mods", [])) != want:
                    continue
                with open(d / "result.json", "rb") as f:
                    res = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(res, dict) and res.get("touched") and isinstance(res.get("changes"), dict):
                return dict(res["touched"], **{"": res["changes"]}), d.name
        return None, ""

    def steps(self, body: dict) -> dict:
        """The steps for the ticked mods (DESIGN§14). The part that reads folders takes seconds on a large list:
        it runs once, off the request, and the answer says while it is still going."""
        m = self._need()
        mods = body.get("mods")
        if not isinstance(mods, list) or len(mods) > 50 or not all(isinstance(x, str) and x for x in mods):
            raise Bad("the ticked mods did not arrive")
        touched, told_by = self._touched_for(mods)
        key = (id(m), tuple(sorted(mods)), told_by)
        with self._lock:
            started = key in self._deep
            if not started and mods:
                self._deep = {k: v for k, v in self._deep.items() if k[0] == id(m)}     # an older reading's are dropped
                self._deep[key] = None
        if not started and mods:
            def work() -> None:
                try:
                    found = steps.look_deeper(m, mods, touched)
                except Exception as e:
                    log.warn("looking into the ticked mods' folders failed: %s", logbook.why(e))
                    found = {}
                with self._lock:
                    self._deep[key] = found
            threading.Thread(target=work, name="steps-deep", daemon=True).start()
        deep = self._deep.get(key)
        job = self.job.public() if self.job else None
        out = steps.compile_steps(m, mods, job, deep, auto=self.changes is not None,
                                  going=self.changes is not None and self.changes.dm_state in ("working", "verified"),
                                  tools_run=self.changes.tools_run() if self.changes is not None else None,
                                  self_run=self.settings().get("tools_self") is not False)
        out["looking"] = bool(mods) and deep is None
        return out

    # --- adding mods (MT21, DESIGN§16): read-only ------------------------------------------------------------------

    def add_resolve(self, body: dict) -> dict:
        """What the dropped files and folders are in this MO2, by their names (DESIGN§16.1)."""
        m = self._need()
        items = body.get("items")
        if (not isinstance(items, list) or not items or len(items) > 50 or not all(
                isinstance(x, dict) and isinstance(x.get("name"), str) and 0 < len(x["name"]) <= 300 for x in items)):
            raise Bad("what was dropped could not be used")
        inst = m.instance
        names = {instance.fold(x.name) for x in inst.mods if x.kind == "mod"}
        index: dict | None = {}
        if any(instance.fold(x["name"].strip()) not in names for x in items):
            hit = self._installed
            if hit is None or hit[0] is not m:
                hit = (m, adding.installed_from(inst))        # one small read of each mod's meta.ini
                self._installed = hit
            index = hit[1]
        got = adding.resolve(inst, [{"name": x["name"]} for x in items], index)
        log.info("add: %d dropped, %d found in MO2", len(got), sum(1 for g in got if g["mods"]))
        return {"items": got}

    # Archives taken in (DESIGN§16.1): kept and unpacked in the session's own folder, never in the modlist.

    def _incoming(self) -> Path:
        if self.session is None:
            raise Bad("open a modlist first: a dropped mod is kept with the session of its modlist")
        return self.store.dir(self.session.id) / "incoming"

    def _save_staged(self, rec: dict) -> None:
        try:
            paths.write_atomic(Path(rec["dir"]) / "staged.json", json.dumps(
                {k: rec.get(k, "") for k in ("id", "archive", "name", "state", "note", "root", "files", "kind", "source",
                                             "installer", "options", "raw", "picks")},
                ensure_ascii=False).encode("utf-8"))
        except OSError:
            pass

    def _load_staged(self) -> None:
        """The archives this session took in before, as they were left; one that was still being unpacked when
        ModTrap closed is marked so."""
        self._staged = {}
        try:
            base = self._incoming()
            folders = sorted(p for p in base.iterdir() if p.is_dir())
        except (OSError, Bad, sessions.Refused):
            return
        for d in folders:
            try:
                with open(d / "staged.json", "rb") as f:
                    rec = json.loads(f.read(1024 * 1024).decode("utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict) or rec.get("id") != d.name:
                continue
            rec["dir"] = str(d)
            if rec.get("state") in ("copying", "unpacking"):
                rec["state"], rec["note"] = "failed", "ModTrap was closed while this was being unpacked. Drop it again."
            self._staged[d.name] = rec

    def _new_staged(self, archive: str, source: str) -> dict:
        base = self._incoming()
        sid = secrets.token_hex(5)
        d = base / sid
        d.mkdir(parents=True, exist_ok=False)
        m = self.model
        taken = {instance.fold(x.name) for x in m.instance.mods} if m is not None else set()
        taken |= {instance.fold(r["name"]) for r in self._staged.values()}
        stem = adding.NEXUS_TAIL.sub("", adding.ARCHIVE.sub("", archive)).strip(" .") or "New mod"
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", stem).strip(" .")[:120] or "New mod"
        name, n = stem, 2
        while instance.fold(name) in taken:
            name, n = "%s (%d)" % (stem, n), n + 1
        rec = {"id": sid, "archive": archive, "name": name, "state": "copying", "note": "", "root": "", "files": 0,
               "kind": "", "source": source, "dir": str(d), "installer": "", "options": [], "raw": "", "picks": {}}
        self._staged[sid] = rec
        self._save_staged(rec)
        return rec

    def _unpack(self, rec: dict, src: Path) -> None:
        """Off the request: unpack, then find the mod inside (DESIGN§16.1)."""
        d = Path(rec["dir"])
        try:
            got = unpack.unpack(src, d / "files", self.seven_zip)
            lay = unpack.layout(d / "files")
            rec.update(kind=got["kind"], files=got["files"], root=str(lay["root"]))
            if lay["installer"]:
                # An installer that asks which parts to install (DESIGN§16.1): the questions are asked on the
                # page; the answers build the mod's folder. One ModTrap cannot read is handed to MO2.
                rec.update(state="installer", raw=str(lay["root"]), root="", picks={},
                           installer="fomod" if lay["installer"] == "fomod" else "folders",
                           options=list(lay.get("options", []))[:200],
                           note="This mod asks which parts to install. Answer below; ModTrap then builds the mod "
                                "from your answers.")
                try:
                    self._installer_of(rec)
                except fomod.Unreadable as e:
                    rec.update(installer="", note="This mod comes with an installer ModTrap cannot read (%s) Install "
                               "it in MO2, leave it disabled, press Rescan here, and find it in the box above." % e)
            else:
                rec.update(state="ready", note="" if lay["sure"] else
                           "ModTrap did not find the usual game folders in this archive and took it as it is. If it "
                           "is not a mod for the game's Data folder, it does not belong in MO2's mod list.")
            log.info("add: unpacked “%s” (%s, %d files): %s", rec["archive"], got["kind"], got["files"], rec["state"])
        except unpack.Refused as e:
            rec.update(state="failed", note=str(e))
            log.warn("add: “%s” was not taken in: %s", rec["archive"], e)
        except Exception as e:
            rec.update(state="failed", note="Unpacking failed: %s" % logbook.why(e))
            log.warn("add: unpacking “%s” failed: %s", rec["archive"], logbook.why(e))
        finally:
            self._save_staged(rec)

    def _installer_of(self, rec: dict) -> fomod.Installer:
        if rec.get("installer") == "fomod":
            path = fomod.find(Path(rec["raw"]))
            if path is None:
                raise fomod.Unreadable("its installer file is no longer there.")
            return fomod.read(path)
        if rec.get("installer") == "folders":
            return fomod.from_folders([str(x) for x in rec.get("options", [])])
        raise fomod.Unreadable("it has no installer ModTrap can read.")

    def _plugin_state(self, name: str) -> str:
        """A plugin's standing in the load order, in an installer's words (MO02§5)."""
        m = self.model
        r = m.row(name) if m is not None else None
        if r is None or r.source is None:
            return "Missing"
        return "Active" if r.active else "Inactive"

    def _installer_rec(self, body: dict) -> tuple[dict, dict]:
        sid = body.get("id")
        rec = self._staged.get(sid) if isinstance(sid, str) else None
        if rec is None or not rec.get("installer"):
            raise Bad("that mod has no questions to answer")
        picks = body.get("picks", {})
        if not isinstance(picks, dict) or len(picks) > 2000 or not all(
                isinstance(k, str) and len(k) < 20 and isinstance(v, list) and len(v) < 2000 for k, v in picks.items()):
            raise Bad("the answers did not arrive")
        return rec, picks

    def add_installer(self, body: dict) -> dict:
        """The installer's questions as they stand for the answers so far (DESIGN§16.1)."""
        rec, picks = self._installer_rec(body)
        try:
            v = fomod.view(self._installer_of(rec), picks, self._plugin_state)
        except fomod.Unreadable as e:
            raise Bad(str(e)) from None
        return {"id": rec["id"], "name": v["name"] or rec["name"], "steps": v["steps"], "problems": v["problems"],
                "files": len(v["files"]), "state": rec["state"]}

    def add_choose(self, body: dict) -> dict:
        """Builds the mod's folder from the answers, in the session's folder; it is then analysed like any other."""
        rec, picks = self._installer_rec(body)
        if rec["state"] not in ("installer", "ready"):
            raise Bad("it is not ready to be answered")
        try:
            v = fomod.view(self._installer_of(rec), picks, self._plugin_state)
            if v["problems"]:
                raise Bad(" ".join(v["problems"]))
            d = Path(rec["dir"])
            n = 1
            while (d / ("built-%d" % n)).exists():
                n += 1
            got = fomod.build(v["files"], Path(rec["raw"]), d / ("built-%d" % n))
        except fomod.Unreadable as e:
            raise Bad(str(e)) from None
        except OSError as e:
            raise Bad("the mod could not be built from the answers: %s" % logbook.why(e)) from None
        if not got["copied"]:
            shutil.rmtree(d / ("built-%d" % n), ignore_errors=True)
            raise Bad("these answers install nothing")
        old = rec.get("root")
        rec.update(state="ready", root=str(d / ("built-%d" % n)), picks=picks, files=got["copied"],
                   note=("The installer names %d file(s) or folder(s) the archive does not have: %s. The mod may not "
                         "work as meant." % (len(got["missing"]), ", ".join(got["missing"][:5]))) if got["missing"] else "")
        if old and Path(old).parent == d and Path(old).name.startswith("built-"):
            shutil.rmtree(old, ignore_errors=True)
        self._save_staged(rec)
        log.info("add: built “%s” from its installer's answers (%d files)", rec["name"], got["copied"])
        return self._staged_public(rec)

    @staticmethod
    def _archive_name(name: object) -> str:
        if not isinstance(name, str):
            raise Bad("the dropped file has no usable name")
        name = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not name or len(name) > 255 or name in (".", "..") or re.search(r'[<>:"|?*\x00-\x1f]', name):
            raise Bad("the dropped file has no usable name")
        return name

    def upload(self, name: str, length: int, stream) -> dict:
        """A dropped archive, as its bytes: written into the session's folder as it arrives, then unpacked."""
        self._need()
        name = self._archive_name(name)
        if length <= 0:
            raise Bad("the dropped file is empty")
        base = self._incoming()
        base.mkdir(parents=True, exist_ok=True)
        try:
            free = shutil.disk_usage(base).free
        except OSError:
            free = None
        if free is not None and free < length * 2 + unpack.SPARE_BYTES:
            raise Bad("there is not enough room on the disk of ModTrap's work folder to take this file in and unpack "
                      "it (%s free)" % unpack.size_words(free))
        rec = self._new_staged(name, "upload")
        target = Path(rec["dir"]) / "archive"
        left = length
        try:
            with open(target, "wb") as f:
                while left:
                    block = stream.read(min(left, 1024 * 1024))
                    if not block:
                        break
                    f.write(block)
                    left -= len(block)
        except OSError as e:
            left = -1
            log.warn("add: “%s” could not be written: %s", name, logbook.why(e))
        if left:
            shutil.rmtree(rec["dir"], ignore_errors=True)
            self._staged.pop(rec["id"], None)
            raise Bad("the file did not arrive whole; drop it again")
        rec["state"] = "unpacking"
        self._save_staged(rec)
        log.info("add: took in “%s” (%s)", name, unpack.size_words(length))
        threading.Thread(target=self._unpack, args=(rec, target), name="unpack", daemon=True).start()
        return self._staged_public(rec)

    def add_take(self, body: dict) -> dict:
        """A dropped archive that is already in MO2's Downloads: read where it lies, no copy."""
        m = self._need()
        name = self._archive_name(body.get("name"))
        size = body.get("size")
        base = m.instance.downloads_dir
        src = base / name if base is not None else None
        try:
            ok = src is not None and src.is_file() and (not isinstance(size, int) or src.stat().st_size == size)
        except OSError:
            ok = False
        if not ok:
            raise Bad("that file is not in MO2's Downloads as it was dropped")
        rec = self._new_staged(name, "downloads")
        rec["state"] = "unpacking"
        self._save_staged(rec)
        threading.Thread(target=self._unpack, args=(rec, src), name="unpack", daemon=True).start()
        return self._staged_public(rec)

    def add_forget(self, body: dict) -> dict:
        """Takes an archive off the list and removes ModTrap's own copy of it. Nothing of the modlist is touched."""
        sid = body.get("id")
        rec = self._staged.get(sid) if isinstance(sid, str) else None
        if rec is None:
            raise Bad("that is not on the list")
        if rec["state"] in ("copying", "unpacking"):
            raise Bad("it is still being unpacked; take it off the list when that has ended")
        d = Path(rec["dir"])
        if d.parent == self._incoming() and re.fullmatch(r"[0-9a-f]{10}", d.name):
            shutil.rmtree(d, ignore_errors=True)
        self._staged.pop(sid, None)
        return {"forgotten": sid}

    @staticmethod
    def _staged_public(rec: dict) -> dict:
        out = {k: rec[k] for k in ("id", "archive", "name", "state", "note", "files", "kind")}
        out["installer"] = bool(rec.get("installer"))
        out["picks"] = rec.get("picks") or {}
        return out

    def add(self, body: dict) -> dict:
        """The analysis for the mods to add (DESIGN§16). It lists file names in many folders, which takes
        seconds on a large list: it runs once, off the request, and the answer says while it is still going."""
        m = self._need()
        mods = body.get("mods")
        if not isinstance(mods, list) or len(mods) > 20 or not all(isinstance(x, str) and 0 < len(x) <= 300 for x in mods):
            raise Bad("the mods to add did not arrive")
        ids = body.get("staged", [])
        if not isinstance(ids, list) or len(ids) > 20 or not all(isinstance(x, str) for x in ids):
            raise Bad("the mods to add did not arrive")
        recs = [self._staged[i] for i in ids if i in self._staged]
        status = [self._staged_public(r) for r in recs]
        gone = [i for i in ids if i not in self._staged]
        ready = [r for r in recs if r["state"] == "ready" and r["root"]]
        busy = any(r["state"] in ("copying", "unpacking") for r in recs)
        if not mods and not ready:
            return {"looking": False, "unpacking": busy, "mods": [], "steps": [], "staged": status, "gone": gone,
                    "summary": "Nothing to analyse yet.",
                    "added": self.changes.jobs() if self.changes is not None else []}
        key = (id(m), tuple(mods), tuple(r["id"] for r in ready))
        with self._lock:
            started = key in self._adding
            if not started:
                self._adding = {k: v for k, v in self._adding.items() if k[0] == id(m)}
                self._adding[key] = None
        if not started:
            extra = [adding.staged_mod(r["name"], Path(r["root"])) for r in ready]

            def work() -> None:
                try:
                    found = adding.analyse(m, mods, read=self._cache.read, staged=extra, auto=self.changes is not None)
                    log.info("add: analysed %d mod(s): %s", len(found["mods"]), found["summary"])
                except Exception as e:
                    log.warn("analysing the mods to add failed: %s", logbook.why(e))
                    found = {"failed": "The analysis failed: %s" % logbook.why(e), "mods": [], "steps": []}
                with self._lock:
                    self._adding[key] = found
            threading.Thread(target=work, name="adding", daemon=True).start()
        got = self._adding.get(key)
        added = self.changes.jobs() if self.changes is not None else []
        rec = self.recjob.public() if self.recjob is not None else None
        if got is None:
            return {"looking": True, "unpacking": busy, "mods": [], "steps": [], "staged": status, "gone": gone,
                    "added": added, "records": rec}
        return dict(got, looking=False, unpacking=busy, staged=status, gone=gone, added=added, records=rec)

    def job_state(self) -> dict:
        if not self.job:
            return {"job": None}
        out = self.job.public()
        # The modlist has been read again since (a demaster, a Rescan, a change in MO2): the result describes the
        # modlist as it was, and a demaster needs a fresh one (WHY§61).
        out["stale"] = bool(out.get("state") == "done" and not out.get("past")
                            and getattr(self.job, "model", None) is not self.model)
        return {"job": out}

    # --- answers ---------------------------------------------------------------------------------------------------

    def _need(self) -> model.Model:
        m = self.model
        if m is None:
            raise Bad("no modlist is open")
        return m

    # --- MO2: open or closed, for this modlist (WHY§58) ---------------------------------------------------------------

    def updated_on_disk(self) -> dict | None:
        """Have ModTrap's own files changed since this ModTrap started (WHY§67)? Then: the version now on disk
        (WHY§68). Looked at every few seconds."""
        when, was = self._code_seen
        if time.time() - when > 3:
            was = {"version": version.recorded()[0]} if version.code_mark() != version.STARTED else None
            self._code_seen = (time.time(), was)
        return was

    def _launch(self, cmd: list[str], cwd: str):
        """Starts MO2's command for a job. A MO2 that was not open before is then ModTrap's own for this run: it
        closes by itself afterwards, and until it has, nothing asks the owner whether to close it (WHY§67)."""
        if self.mo2()["state"] == "closed":
            self._mo2_ours = True
        return self.launcher(cmd, cwd)

    def mo2(self) -> dict:
        """Is MO2 open on this modlist? "open", "closed", or "unknown" (it cannot be told: then nothing that needs
        it closed is done). A MO2 of another modlist does not count: it has its own lists. Where it cannot be told
        which MO2 is running, a running MO2 counts as this one."""
        m = self.model
        mine = str(m.instance.root / dryrun.MO2_EXE) if m is not None else ""
        try:
            paths_now = self.program_paths(dryrun.MO2_EXE)
        except Exception:
            paths_now = None
        if paths_now is None:
            r = self.running(dryrun.MO2_EXE)
            st = {"state": "unknown" if r is None else "open" if r else "closed", "other": False}
        elif not paths_now:
            st = {"state": "closed", "other": False}
        elif not mine or any(dryrun.winauto.same_file(p, mine) for p in paths_now):
            st = {"state": "open", "other": False}
        else:
            st = {"state": "closed", "other": True}         # only the MO2 of another modlist is running
        if st["state"] == "closed":
            self._mo2_ours = False
        st["ours"] = st["state"] == "open" and self._mo2_ours
        return st

    def wait_mo2_gone(self, seconds: float = 45.0, poll: float = 0.5, ask_after: float = 5.0,
                      owners_too: bool = False) -> bool:
        """Waits for a MO2 that ModTrap itself started for a run to have gone, before a step that needs MO2 closed.
        Its end-of-run message is closed as it shows, and after some seconds it is asked to close (never ended).
        A MO2 the owner opened is left alone and not waited for, unless `owners_too`: the last step of a demaster
        whose confirmed plan said MO2 would be closed for it (WHY§67). True when no MO2 of this modlist is open."""
        m = self.model
        exe = str(m.instance.root / dryrun.MO2_EXE) if m is not None else ""
        start, asked = time.monotonic(), False
        while True:
            st = self.mo2()
            if st["state"] != "open":
                return st["state"] == "closed"
            if not (st.get("ours") or owners_too):
                return False
            waited = time.monotonic() - start
            if waited > seconds:
                return False
            try:
                dryrun.winauto.close_message(dryrun.MO2_EXE)
                if not asked and waited >= ask_after and exe:
                    asked = True
                    if self.ask_close(exe):
                        log.info("MO2 was asked to close%s (as a click on its X does)",
                                 ": ModTrap had started it for a run" if st.get("ours") else
                                 " for the demaster's last step, as its plan said")
            except Exception:
                pass
            time.sleep(poll)

    def mo2_closed(self) -> bool | None:
        st = self.mo2()["state"]
        return None if st == "unknown" else st == "closed"

    def mo2_close(self) -> dict:
        """Asks this modlist's MO2 to close, as a click on its X does: on the owner's word, and never by force."""
        m = self._need()
        if self._busy() or (self.changes is not None and self.changes.busy()) or \
                (self.tooljob is not None and self.tooljob.public().get("state") in ("starting", "preparing", "running")):
            raise Bad("ModTrap is running something through MO2 right now; wait until it has ended")
        if self.mo2()["state"] != "open":
            return {"asked": False, "mo2": self.mo2()}
        ours = self._mo2_ours
        asked = False
        try:
            asked = bool(self.ask_close(str(m.instance.root / dryrun.MO2_EXE)))
        except Exception:
            asked = False
        if not asked:
            raise Bad("MO2 could not be asked to close: close it yourself")
        log.info("MO2 was asked to close%s (as a click on its X does)",
                 ": ModTrap had started it for a run" if ours else ", on your word")
        self._mo2_seen = (0.0, {})
        return {"asked": True, "mo2": self.mo2()}

    def mo2_open(self) -> dict:
        """Starts this modlist's MO2, as a double click on it does."""
        m = self._need()
        exe = m.instance.root / dryrun.MO2_EXE
        if not exe.is_file():
            raise Bad("ModOrganizer.exe was not found in the modlist's folder")
        if self.mo2()["state"] == "open":
            return {"started": False, "mo2": self.mo2()}
        try:
            self.launcher([str(exe), "-p", m.instance.profile], str(m.instance.root))
        except OSError as e:
            raise Bad("MO2 could not be started: %s" % logbook.why(e)) from None
        self._mo2_ours = False                  # this one is the owner's to close
        log.info("MO2 was started for you (profile '%s')", m.instance.profile)
        self._mo2_seen = (0.0, {})
        return {"started": True, "mo2": self.mo2()}

    def process_public(self, dm: dict | None = None, pr: dict | None = None) -> list[dict]:
        """The demaster as stages and tasks, as far as ModTrap itself carries it (DESIGN§18, WHY§70): the probe,
        the dry run, the plan, the change on copies, putting it in place. Each task has a state the page colours:
        waiting, going, done, failed, skipped, yours (waits for the owner)."""
        P = process
        out: list[dict] = []

        def stage(key: str, title: str, who: str, tasks: list[dict], note: str = "") -> None:
            out.append({"key": key, "title": title, "who": who, "tasks": tasks, "state": P.stage_state(tasks),
                        "note": note})

        ch = self.changes
        # 1. The probe: ModTrap proves itself on this modlist with invented plugins, before it touches a real one.
        if ch is not None and ch.require_probe:
            pr = pr if pr is not None else ch.probe_public()
            known = {"passed": P.DONE, "failed": P.FAILED, "going": P.GOING, "skipped": P.SKIPPED}
            tasks = [{"key": s["key"], "text": s["title"], "state": known.get(s.get("result", ""), P.WAITING),
                      "note": s.get("detail", "") or ""} for s in pr.get("steps", [])]
            note = ""
            if not pr.get("reason") and pr.get("state") != "working":
                note = "Passed%s; it holds for this xEdit and these scripts." % (" on " + pr["when"].replace("T", " ") if pr.get("when") else "")
                if not tasks:
                    tasks = [{"key": "passed", "text": "The probe has passed on this modlist", "state": P.DONE, "note": ""}]
            elif not tasks:
                tasks = [{"key": k, "text": t, "state": P.WAITING, "note": ""} for k, t in probejob_steps()]
            if pr.get("state") == "failed" and pr.get("message") and not any(t["state"] == P.FAILED for t in tasks):
                tasks.append({"key": "why", "text": "The probe stopped", "state": P.FAILED, "note": pr["message"]})
            stage("probe", "Probe", "ModTrap", tasks, note or (pr.get("reason") or ""))
        # 2. The dry run.
        tasks = P.BOARD.tasks("dry")
        job = self.job_state()["job"]
        dm = dm if dm is not None else ch.demaster_public() if ch is not None else {}
        in_hand = dm.get("state") in ("working", "verified", "installed") or bool(P.BOARD.tasks("change"))
        # A dry run of the modlist as it was (kept from an earlier start, or made before the modlist was read
        # again) is not this demaster's dry run: a new one is made (WHY§61, WHY§71).
        # Once a demaster is in hand or in place its dry run stays shown as done: it is that demaster's own.
        old = bool(not in_hand and job and job.get("state") == "done" and (job.get("past") or job.get("stale")))
        if old:
            job_note = "An earlier dry run is kept on the Dry run tab; the modlist has been read again since, so a new one is made."
            tasks = [dict(t, state=P.WAITING, note="") for t in tasks]
            job = None
        else:
            job_note = "" if not job else "For %s." % ", ".join(job.get("plan", {}).get("trapped_mods", [])[:4])
        if not tasks:
            tasks = [{"key": k, "text": t, "state": P.DONE if job and job.get("state") == "done" else P.WAITING, "note": ""}
                     for k, t in P.DRY]
        stage("dry", "Dry run", "ModTrap", tasks, job_note)
        # 3. The plan: what the dry run sorted, and the owner's word.
        files = (job or {}).get("result", {}).get("files", []) if job and job.get("state") == "done" else []
        sorted_task = {"key": "sort", "text": "Sort the dependants by what they take from the mod", "state": P.WAITING, "note": ""}
        if files:
            kinds: dict[str, int] = {}
            for fd in files:
                kinds[fd.get("reading", "?")] = kinds.get(fd.get("reading", "?"), 0) + 1
            sorted_task.update(state=P.DONE, note="; ".join("%d %s" % (n, k) for k, n in sorted(kinds.items())))
        going = in_hand
        confirm = {"key": "confirm", "text": "You read the plan and press “Go ahead”",
                   "state": P.DONE if going else P.YOURS if files and ch is not None else P.WAITING, "note": ""}
        stage("plan", "Plan", "you", [sorted_task, confirm])
        if ch is None:
            return out
        # 4. and 5. The change on copies, and putting it in place.
        tasks = P.BOARD.tasks("change") or [{"key": k, "text": t, "state": P.WAITING, "note": ""} for k, t in P.CHANGE]
        stage("change", "Demaster on copies", "ModTrap", tasks, dm.get("message", "") if dm.get("state") == "failed" else "")
        tasks = P.BOARD.tasks("install") or [{"key": k, "text": t, "state": P.WAITING, "note": ""} for k, t in P.INSTALL]
        if dm.get("state") == "verified" and not P.BOARD.tasks("install"):
            tasks[0] = dict(tasks[0], state=P.YOURS if dm.get("mo2_closed") is False else P.WAITING,
                            note="MO2 is open: ModTrap closes it in the one go, or asks you" if dm.get("mo2_closed") is False else "")
        stage("install", "Put in place", "ModTrap", tasks)
        return out

    def state(self) -> dict:
        with self._lock:
            out = {"name": NAME, "version": VERSION, "status": self.status, "message": self.message,
                   "changes": self.changes is not None,
                   "updated_on_disk": self.updated_on_disk(),
                   "settings": self.settings(),
                   "version_differs": version.DIFFERS,
                   "save": self.saver.public(),
                   "tool": self.tooljob.public() if self.tooljob is not None else None,
                   "folder": self.folder, "profile": self.profile}
            m = self.model
        if m is not None:
            when, seen = self._mo2_seen
            if time.time() - when > 1.5:
                seen = self.mo2()
                self._mo2_seen = (time.time(), seen)
            out["mo2"] = seen
        else:
            out["mo2"] = None
        out["demaster"] = self.changes.demaster_public() if self.changes is not None else None
        out["probe"] = self.changes.probe_public() if self.changes is not None else None
        out["process"] = self.process_public(out["demaster"], out["probe"]) if m is not None else []
        settings = paths.load_settings()
        out["recent"] = [r for r in settings.get("recent", []) if isinstance(r, str) and r][:8]
        out["log_epoch"] = self.log_epoch
        out["working"] = self.working()
        every = self.store.all()
        live = [x for x in every if x.status != sessions.FINISHED]
        done = [x for x in every if x.status == sessions.FINISHED][-10:]
        out["sessions"] = [x.brief() for x in live + done[::-1]]
        s = self.session
        if s is not None:
            cur = next((x for x in every if x.id == s.id), s)           # as it is on disk now
            self.session = cur
            out["session"] = dict(cur.brief(), locked=self._locked(), ui=cur.ui)
        else:
            out["session"] = None
        if m is not None and out["status"] == "ready":
            inst = m.instance
            real = [x for x in inst.mods if x.kind == "mod"]
            rows = list(m.plugins.values())
            out.update({
                "game": inst.game_name, "profiles": list(inst.profiles),
                "mods": len(real), "mods_enabled": sum(x.enabled for x in real),
                "separators": sum(x.kind == "separator" for x in inst.mods),
                "plugins": sum(r.position is not None for r in rows), "plugins_active": sum(r.active for r in rows),
                "unreadable": sum(bool(r.unreadable) and r.source is not None for r in rows),
                "tools": self._tools(inst),
                "notes": [logbook.mask(n) for n in inst.notes],
                "issues": [{"plugin": i.plugin, "master": i.master, "what": i.what} for i in m.issues[:500]],
                "issue_count": len(m.issues),
            })
        return out

    def settings(self) -> dict:
        kept = paths.load_settings().get("options")
        kept = kept if isinstance(kept, dict) else {}
        return {k: (kept[k] if isinstance(kept.get(k), bool) else d) for k, d in SETTINGS.items()}

    def settings_set(self, body: dict) -> dict:
        name, value = body.get("name"), body.get("value")
        if name not in SETTINGS or not isinstance(value, bool):
            raise Bad("that is not a setting ModTrap has")
        now = self.settings()
        now[name] = value
        try:
            kept = paths.load_settings()
            kept["options"] = now
            paths.save_settings(kept)
        except OSError as e:
            raise Bad("the setting could not be kept: %s" % logbook.why(e)) from None
        log.info("setting “%s” is now %s", name, "on" if value else "off")
        return now

    def tools_made(self) -> dict:
        """What the modlist's tools made (WHY§74): each tool-made plugin with its records by kind, and for the
        patcher framework the patchers behind it. Read once for each reading of the modlist."""
        from . import toolmade
        m = self._need()
        hit = self._lists.get("tools_made")
        if hit and hit[0] is m:
            return hit[1]
        self._making_tools += 1
        try:
            out = toolmade.made(m)
        finally:
            self._making_tools -= 1
        self._lists["tools_made"] = (m, out)
        return out

    def _tools(self, inst: instance.Instance) -> list[dict]:
        """The executables set up in MO2 (DESIGN§13): title, program file, the mod its new files go to, and
        which one ModTrap would start as xEdit."""
        try:
            chosen = dryrun.find_xedit(inst)[0]
        except dryrun.Refused:
            chosen = ""
        return [{"title": e.title, "file": Path(e.binary.replace("\\", "/")).name,
                 "output_mod": inst.output_mods.get(e.title, ""), "xedit": e.title == chosen}
                for e in inst.executables]

    def mods(self) -> dict:
        m = self._need()
        hit = self._lists.get("mods")
        if hit and hit[0] is m:
            return hit[1]
        rows = []
        for mod in reversed(m.instance.mods):               # highest priority first, as MO2 lists them
            if mod.kind in ("game", "overwrite") and not mod.plugins:
                continue
            won = m.provided_by(mod)
            deps = m.dependants_of_mod(mod) if won else []
            # The mods tied to this one as a demaster sees it (WHY§59): those holding plugins that need one of
            # its plugins, and those whose plugins its own need.
            needed_by = sorted({r.source for r in deps if r.source and r.source != mod.name})
            needs = set()
            for r in won:
                for master in r.masters:
                    mr = m.plugins.get(instance.fold(master))
                    if mr is not None and mr.source and mr.source != mod.name and mr.source != instance.GAME:
                        needs.add(mr.source)
            rows.append({"name": mod.name, "priority": mod.priority, "enabled": mod.enabled, "kind": mod.kind,
                         "listed": mod.listed, "plugins": [r.name for r in won],
                         "files": len(mod.plugins), "dependants": len(deps),
                         "needed_by": needed_by, "needs": sorted(needs)})
        out = {"mods": rows}
        self._lists["mods"] = (m, out)                  # the lists are worked out once for each reading
        return out

    def plugins(self) -> dict:
        m = self._need()
        rows = []
        for f in m.order:
            r = m.plugins[f]
            rows.append({"name": r.name, "position": r.position, "active": r.active, "kind": r.kind,
                         "mod": r.source or "", "mod_priority": r.source_priority, "primary": r.primary,
                         "masters": len(r.masters), "dependants": len(r.dependants),
                         "missing": r.missing_masters, "inactive": r.inactive_masters,
                         "unreadable": r.unreadable, "also_in": list(r.also_in)})
        return {"plugins": rows}

    def plugin(self, name: str) -> dict:
        r = self._need().row(name)
        if r is None:
            raise Bad("no plugin of that name in this profile")
        return {"name": r.name, "position": r.position, "active": r.active, "kind": r.kind, "mod": r.source or "",
                "mod_priority": r.source_priority, "author": r.author, "description": r.description[:2000],
                "masters": list(r.masters), "dependants": list(r.dependants), "missing": r.missing_masters,
                "inactive": r.inactive_masters, "unreadable": r.unreadable, "also_in": list(r.also_in)}

    def mod(self, name: str) -> dict:
        m = self._need()
        mod = m.instance.mod(name)
        if mod is None:
            raise Bad("no mod of that name in this profile")

        def brief(r: model.PluginRow) -> dict:
            return {"name": r.name, "position": r.position, "kind": r.kind, "active": r.active,
                    "masters": len(r.masters)}

        return {"name": mod.name, "priority": mod.priority, "enabled": mod.enabled, "kind": mod.kind,
                "plugins": [dict(brief(r), master_names=list(r.masters)) for r in m.provided_by(mod)],
                "groups": [{"mod": g.mod.name, "priority": g.mod.priority, "enabled": g.mod.enabled,
                            "reading": g.reading, "others": g.others, "made_by": list(g.made_by),
                            "leftover": list(g.leftover), "evidence": list(g.evidence), "proposal": g.proposal,
                            "plugins": [brief(r) for r in g.dependants]}
                           for g in model.groups(m, mod)]}

    # --- the server's two entry points -----------------------------------------------------------------------------

    def get(self, path: str, query: dict[str, str]) -> tuple[int, object]:
        if path == "/api/state":
            return 200, self.state()
        if path == "/api/mods":
            return 200, self.mods()
        if path == "/api/plugins":
            return 200, self.plugins()
        if path == "/api/plugin":
            return 200, self.plugin(query.get("name", ""))
        if path == "/api/mod":
            return 200, self.mod(query.get("name", ""))
        if path == "/api/job":
            return 200, self.job_state()
        if path == "/api/tools/made":
            return 200, self.tools_made()
        if path == "/api/history":
            return 200, self.history_events()
        if path == "/api/log":
            try:
                after = int(query.get("after", "0"))
            except ValueError:
                after = 0
            lines, newest = logbook.lines_after(after)
            return 200, {"lines": lines, "newest": newest}
        return 404, {"error": "not found"}

    def post(self, path: str, body: dict) -> tuple[int, object, Callable[[], None] | None]:
        if path in NEEDS_SAME_VERSION and self.updated_on_disk():
            on_disk = (self.updated_on_disk() or {}).get("version", "")
            raise Bad("This is ModTrap %s, still running, but the files in its folder have changed since it was "
                      "started%s. Quit ModTrap and start it again first: until then the program in memory and the "
                      "scripts on disk are of different versions, and nothing is started."
                      % (VERSION, " (they are version %s now)" % on_disk if on_disk and on_disk != VERSION else ""))
        if path in LAUNCHES_MO2 and self.model is not None and self.mo2().get("other"):
            raise Bad(OTHER_MO2)
        if path == "/api/settings":
            return 200, self.settings_set(body), None
        if path in NEEDS_SAME_VERSION:
            log.info("%s %s is asked for: %s", NAME, VERSION, path[len("/api/"):].replace("/", " "))
        if path == "/api/open":
            folder, profile = body.get("folder"), body.get("profile")
            if not isinstance(folder, str) or len(folder) > 1000:
                raise Bad("give the modlist's folder", "folder")
            if profile is not None and (not isinstance(profile, str) or len(profile) > 200):
                raise Bad("the profile's name is not usable", "profile")
            same = self.session is not None and sessions.modlist_key(folder.strip().strip('"') or ".") == self.session.key
            self.open(folder, profile or None, session=self.session if same else None)
            return 200, {"status": "reading"}, None
        if path == "/api/locate":
            return 200, self.locate(body), None
        if path == "/api/dryrun/plan":
            return 200, self.dry_plan(body), None
        if path == "/api/dryrun/start":
            return 200, self.dry_start(body), None
        if path == "/api/browse":
            where = body.get("path", "")
            if not isinstance(where, str):
                raise Bad("that is not a folder's path")
            try:
                return 200, browse.listing(where), None
            except browse.Refused as e:
                raise Bad(str(e)) from None
        if path == "/api/steps":
            return 200, self.steps(body), None
        if path == "/api/add":
            return 200, self.add(body), None
        if path == "/api/add/resolve":
            return 200, self.add_resolve(body), None
        if path == "/api/add/take":
            return 200, self.add_take(body), None
        if path == "/api/add/forget":
            return 200, self.add_forget(body), None
        if path == "/api/add/installer":
            return 200, self.add_installer(body), None
        if path == "/api/add/choose":
            return 200, self.add_choose(body), None
        if path == "/api/save/start":
            return 200, self.save_start(), None
        if path == "/api/records/start":
            return 200, self.records_start(body), None
        if path == "/api/records/stop":
            return 200, self.records_stop(), None
        if path == "/api/tool/start":
            return 200, self.tool_start(body), None
        if path == "/api/tool/stop":
            return 200, self.tool_stop(), None
        if path == "/api/mo2/close":
            return 200, self.mo2_close(), None
        if path == "/api/mo2/open":
            return 200, self.mo2_open(), None
        if path == "/api/job/stop":
            if self.job is None:
                raise Bad("no dry run is going")
            self.job.stop()
            return 200, self.job_state(), None
        if path == "/api/session/switch":
            return 200, self.session_switch(body), None
        if path == "/api/session/new":
            return 200, self.session_new(), None
        if path == "/api/session/rename":
            return 200, self.session_rename(body), None
        if path == "/api/session/finish":
            return 200, self.session_finish(body), None
        if path == "/api/session/ui":
            return 200, self.session_ui(body), None
        if path == "/api/quit":
            answer, after = self.quit(body)
            return 200, answer, after
        if self.changes is not None and path in self.changes.PATHS:
            return 200, self.changes.post(path, body), None
        if path == "/api/rescan":
            if not self.folder:
                raise Bad("no modlist is open")
            if self._busy():
                raise Bad("a dry run is going; rescan when it has ended")
            self.open(self.folder, self.profile or None, session=self.session)
            return 200, {"status": "reading"}, None
        return 404, {"error": "not found"}, None
