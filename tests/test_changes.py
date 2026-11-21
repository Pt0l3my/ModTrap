"""The switch (WHY§44): without it nothing the page calls can change a modlist; with it, "Add it" and Revert work
through the same guarded job, on an invented modlist."""

from __future__ import annotations

import inspect
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, instance, logbook, model
from modtrap.server import Bad

from . import _fixtures as fx
from .test_adding import invented
from .test_intake import NEW_MOD, snapshot
from .test_unpack import zipped

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


class Switch(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        self.api = api.Api()
        self.mo2_running: bool | None = False
        self.api.running = lambda image: self.mo2_running
        self.api.open(str(self.root), wait=True)
        self.before = snapshot(self.root)

    def tearDown(self) -> None:
        self.wait_ready()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def wait_ready(self) -> None:
        for _ in range(400):
            if self.api.status == "ready" and not any(r["state"] in ("copying", "unpacking") for r in self.api._staged.values()):
                return
            time.sleep(0.02)

    def settled(self, body: dict) -> dict:
        for _ in range(400):
            self.wait_ready()
            got = self.api.post("/api/add", body)[1]
            if not got["looking"] and not got["unpacking"]:
                return got
            time.sleep(0.02)
        self.fail("it never settled")

    def dropped(self) -> dict:
        data = zipped(NEW_MOD)
        rec = self.api.upload("Heather-4711-2-1.zip", len(data), io.BytesIO(data))
        body = {"mods": ["Thistle"], "staged": [rec["id"]]}
        self.settled(body)
        return body

    def test_switched_off_the_paths_do_not_exist_and_the_module_is_not_loaded(self) -> None:
        body = self.dropped()
        for path in changes.PATHS:
            self.assertEqual(self.api.post(path, body)[0], 404)
        self.assertFalse(self.api.state()["changes"])
        self.assertEqual(snapshot(self.root), self.before)
        src = inspect.getsource(api)
        self.assertNotIn("import changes", src)
        self.assertNotIn("addjob", src)

    def test_a_fresh_start_without_the_flag_never_loads_it(self) -> None:
        import subprocess
        code = ("import sys; from modtrap import api, __main__; "
                "print(sorted(m for m in sys.modules if m in ('modtrap.changes', 'modtrap.addjob', 'modtrap.profile')))")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(Path(api.__file__).parent.parent))
        self.assertEqual(out.stdout.strip(), "[]")

    def test_switched_on_the_plan_says_what_would_be_done(self) -> None:
        self.api.changes = changes.Changes(self.api, require_probe=False)
        body = self.dropped()
        p = self.api.post("/api/add/plan", body)[1]
        self.assertEqual([(x["name"], x["staged"], x["before"]) for x in p["mods"]],
                         [("Thistle", False, "Outputs_separator"), ("Heather", True, "Outputs_separator")])
        self.assertEqual(sorted(x["name"] for x in p["plugins"]), ["Heather.esp", "Thistle.esp"])
        self.assertIs(p["mo2_closed"], True)
        self.assertEqual(snapshot(self.root), self.before)               # a plan changes nothing

    def test_add_it_then_revert(self) -> None:
        self.api.changes = changes.Changes(self.api, require_probe=False)
        body = self.dropped()
        done = self.api.post("/api/add/run", body)[1]
        self.wait_ready()
        inst = instance.load(self.root)
        self.assertTrue(inst.mod("Heather").enabled and inst.mod("Thistle").enabled)
        self.assertEqual(model.build(inst).issues, [])
        # the unpacked mod is now a mod of MO2's: the page is told, and the analysis shows the steps done
        got = self.settled({"mods": ["Thistle", "Heather"], "staged": body["staged"]})
        self.assertEqual(got["staged"][0]["state"], "installed")
        states = {s["key"]: s["state"] for s in got["steps"]}
        self.assertEqual((states["enable"], states["activate"], states["health"]), ("done", "done", "done"))
        self.assertEqual([(j["job"], j["state"]) for j in got["added"]], [(done["job"], "added")])
        back = self.api.post("/api/add/revert", {"job": done["job"]})[1]
        self.wait_ready()
        self.assertEqual(back["left"], [])
        self.assertEqual(snapshot(self.root), self.before)
        got = self.settled(body)
        self.assertEqual((got["staged"][0]["state"], got["added"][0]["state"]), ("ready", "reverted"))
        self.assertEqual([(j["what"], j["state"]) for j in self.api.get("/api/history", {})[1]["jobs"]], [("add", "reverted")])
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 1})
        self.assertEqual(self.api.get("/api/history", {})[1]["jobs"], [])
        self.assertEqual(self.settled(body)["added"], [])

    def test_taking_it_out_after_mo2_rewrote_the_lists_goes_line_by_line(self) -> None:
        self.api.changes = changes.Changes(self.api, require_probe=False)
        body = self.dropped()
        done = self.api.post("/api/add/run", body)[1]
        self.wait_ready()
        pdir = self.root / "profiles" / "Default"
        ml = pdir / "modlist.txt"
        ml.write_bytes(ml.read_bytes() + b"-Installed Meanwhile\r\n")       # what MO2 or the owner did since
        back = self.api.post("/api/add/revert", {"job": done["job"]})[1]
        self.wait_ready()
        self.assertEqual((back["left"], back["how"]), ([], "by line"))
        text = ml.read_bytes().decode()
        self.assertIn("-Installed Meanwhile", text)                          # theirs is kept
        self.assertNotIn("Heather", text)                                    # ModTrap's own mod is gone
        self.assertIn("-Thistle", text)                                      # MO2's mod is disabled again
        self.assertFalse((self.root / "mods" / "Heather").exists())
        plugins = (pdir / "plugins.txt").read_bytes().decode()
        self.assertNotIn("Heather.esp", plugins)
        self.assertIn("\r\nThistle.esp\r\n", plugins)                       # listed, no longer active
        self.assertEqual(model.build(instance.load(self.root)).issues, [])

    def test_mo2_open_or_unknown_changes_nothing(self) -> None:
        self.api.changes = changes.Changes(self.api, require_probe=False)
        body = self.dropped()
        for state in (True, None):
            self.mo2_running = state
            self.assertIsNot(self.api.post("/api/add/plan", body)[1]["mo2_closed"], True)
            with self.assertRaises(Bad):
                self.api.post("/api/add/run", body)
            self.assertEqual(snapshot(self.root), self.before)

    def test_only_this_sessions_own_adds_can_be_reverted(self) -> None:
        self.api.changes = changes.Changes(self.api, require_probe=False)
        for job in ("../../somewhere", "add-1", "dry-20260101-000000", 7):
            with self.assertRaises(Bad):
                self.api.post("/api/add/revert", {"job": job})


class DemasterThroughThePage(unittest.TestCase):
    """The same demaster as tests/test_demaster.py, driven by the calls the page makes (WHY§46)."""

    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")
        self.api = api.Api()
        self.api.poll = 0.03
        self.mo2_running: bool | None = False
        self.api.running = lambda image: self.mo2_running if image == "ModOrganizer.exe" else None
        self.tool = "clean"
        self.api.launcher = lambda cmd, cwd: subprocess.Popen(
            [sys.executable, FAKE, *cmd[1:-1], self.tool, "--mods", str(self.root / "mods")], cwd=cwd)
        self.api.changes = changes.Changes(self.api, require_probe=False)
        self.api.open(str(self.root), wait=True)
        self.before = snapshot(self.root)

    def tearDown(self) -> None:
        t = self.api.changes._dm_thread
        if t is not None:
            t.join(20)
        self.ready()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def ready(self) -> None:
        for _ in range(400):
            if self.api.status == "ready":
                return
            time.sleep(0.02)

    def dry_run(self) -> None:
        self.api.post("/api/dryrun/start", {"mods": ["Bramble"]})
        self.api.job.join(20)
        self.assertEqual(self.api.job.state, "done", self.api.job.message)

    def worked(self) -> dict:
        self.api.changes._dm_thread.join(20)
        return self.api.state()["demaster"]

    def test_without_a_dry_run_there_is_no_plan(self) -> None:
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/plan", {})
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/start", {})

    def test_modtrap_knows_whether_this_modlists_mo2_is_open(self) -> None:
        """WHY§58. What the page shows and asks about, and what a step that changes the lists goes by."""
        here = str(self.root / "ModOrganizer.exe")
        elsewhere = str(Path(self.tmp.name) / "Another List" / "ModOrganizer.exe")
        fx.write(Path(elsewhere), b"another modlist's MO2")
        mo2 = lambda: {k: v for k, v in self.api.mo2().items() if k != "ours"}        # noqa: E731
        self.assertEqual(mo2(), {"state": "closed", "other": False})          # as far as "is one running" tells
        self.mo2_running = True
        self.assertEqual((mo2()["state"], self.api.changes.closed()), ("open", False))
        self.mo2_running = None
        self.assertEqual((mo2()["state"], self.api.changes.closed()), ("unknown", None))
        # Where the running programs can be listed, only this modlist's own MO2 counts.
        running: list[str] = []
        self.api.program_paths = lambda image: list(running)
        self.assertEqual(mo2(), {"state": "closed", "other": False})
        running.append(elsewhere)
        self.assertEqual((mo2(), self.api.changes.closed()), ({"state": "closed", "other": True}, True))
        running.append(here)
        self.assertEqual((mo2(), self.api.changes.closed()), ({"state": "open", "other": False}, False))
        self.api._mo2_seen = (0.0, {})
        self.assertEqual(self.api.state()["mo2"]["state"], "open")
        # Closing is asked of this MO2 only, on the owner's word, and never while ModTrap runs something through it.
        asked: list[str] = []

        def ask(path: str) -> bool:
            asked.append(path)
            running.remove(here)
            return True

        self.api.ask_close = ask
        self.assertEqual(self.api.post("/api/mo2/close", {})[1]["mo2"]["state"], "closed")
        self.assertEqual(asked, [here])
        self.assertFalse(self.api.post("/api/mo2/close", {})[1]["asked"])       # already closed: nothing is asked
        self.assertEqual(asked, [here])
        running.append(here)
        self.api.ask_close = lambda path: False
        with self.assertRaises(Bad):
            self.api.post("/api/mo2/close", {})                                 # it could not be asked: said so
        # Opening starts this modlist's own MO2 with its profile.
        running.clear()
        started: list = []
        self.api.launcher = lambda cmd, cwd: started.append((cmd, cwd))
        self.assertTrue(self.api.post("/api/mo2/open", {})[1]["started"])
        self.assertEqual(started, [([here, "-p", self.api.model.instance.profile], str(self.root))])
        self.assertEqual(snapshot(self.root), self.before)

    def test_a_mo2_that_modtrap_started_is_waited_for_not_asked_about(self) -> None:
        """WHY§67. The MO2 of a run closes by itself; a step that needs MO2 closed waits for it, and closes its
        message. The owner's own MO2 is closed in a demaster only because the confirmed plan said so."""
        here = str(self.root / "ModOrganizer.exe")
        running: list[str] = []
        self.api.program_paths = lambda image: list(running)
        asked: list[str] = []
        self.api.ask_close = lambda path: (asked.append(path), running.clear())[0] is None
        self.api._launch(["x"], str(self.root)) if False else None
        # ModTrap starts MO2 for a run while none is open: that MO2 is ModTrap's own.
        self.api.launcher = lambda cmd, cwd: running.append(here)
        self.api._launch(["ModOrganizer.exe", "run"], str(self.root))
        self.assertEqual(self.api.mo2(), {"state": "open", "other": False, "ours": True})
        self.assertTrue(self.api.wait_mo2_gone(5, poll=0.01, ask_after=0.02))     # it is asked to leave, and leaves
        self.assertEqual((asked, self.api.mo2()["state"]), ([here], "closed"))
        # A MO2 the owner opened is not ModTrap's: nothing waits for it or closes it unasked ...
        running.append(here)
        asked.clear()
        self.assertEqual(self.api.mo2()["ours"], False)
        self.assertFalse(self.api.wait_mo2_gone(0.05, poll=0.01, ask_after=0.02))
        self.assertEqual(asked, [])
        # ... except where the owner's confirmed plan said ModTrap would: the last step of a demaster.
        self.assertTrue(self.api.wait_mo2_gone(5, poll=0.01, ask_after=0.02, owners_too=True))
        self.assertEqual(asked, [here])

    def test_an_update_without_a_restart_is_noticed_and_nothing_is_started(self) -> None:
        """WHY§67: the program in memory and the scripts on disk must be of one version."""
        self.assertFalse(self.api.state()["updated_on_disk"])
        self.api._code_seen = (time.time(), {"version": "9.9.9"})   # as if ModTrap's files had changed on disk
        self.assertTrue(self.api.state()["updated_on_disk"])
        for path in ("/api/dryrun/start", "/api/probe/start", "/api/demaster/start"):
            with self.assertRaises(Bad) as c:
                self.api.post(path, {"mods": ["Bramble"]})
            self.assertIn("Quit ModTrap and start it again", str(c.exception))
            self.assertIn("they are version 9.9.9 now", str(c.exception))
        self.assertEqual(snapshot(self.root), self.before)

    def test_new_plugins_that_wait_are_dropped_when_the_modlist_moves_on(self) -> None:
        """WHY§62: what waits to be put in place was made for the modlist as it was read then."""
        self.dry_run()
        self.api.post("/api/demaster/plan", {})
        self.api.post("/api/demaster/start", {})
        self.assertEqual(self.worked()["state"], "verified")
        self.assertEqual(self.api.post("/api/demaster/drop", {})[1]["state"], "")       # "Not now" on the page
        self.assertEqual(snapshot(self.root), self.before)
        self.dry_run()
        self.api.post("/api/demaster/plan", {})
        self.api.post("/api/demaster/start", {})
        self.assertEqual(self.worked()["state"], "verified")
        self.api.post("/api/rescan", {})                                                # the modlist is read again
        self.ready()
        self.assertEqual(self.api.state()["demaster"]["state"], "")
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/install", {})                                  # nothing waits any more
        self.assertEqual(snapshot(self.root), self.before)

    def test_plan_run_put_in_place_and_revert(self) -> None:
        self.dry_run()
        p = self.api.post("/api/demaster/plan", {})[1]
        self.assertEqual(sorted(x["plugin"] for x in p["demaster"]), ["Generated.esp", "Lantern.esp"])
        self.assertEqual((p["switch_off"], p["disable_mods"], p["needs_you"], p["mod_name"]),
                         (["BrambleLanternPatch.esp", "Collection - Bramble.esp"], ["Bramble - Lantern Patch"], [], "ModTrap - Bramble"))
        got = self.api.post("/api/demaster/start", {})[1]
        self.assertEqual(got["state"], "working")
        with self.assertRaises(Bad):
            self.api.post("/api/dryrun/start", {"mods": ["Bramble"]})          # one thing at a time
        d = self.worked()
        self.assertEqual((d["state"], sorted(d["written"]), d["mo2_closed"]),
                         ("verified", ["Generated.esp", "Lantern.esp"], True))
        self.assertEqual(snapshot(self.root), self.before)                    # verified, and still nothing changed
        self.mo2_running = True
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/install", {})                         # MO2 is open
        self.assertEqual(snapshot(self.root), self.before)
        self.mo2_running = False
        self.assertFalse(self.api.job_state()["job"]["stale"])                 # the dry run is of the modlist as it is
        d = self.api.post("/api/demaster/install", {})[1]
        self.ready()
        self.assertEqual((d["state"], d["check"]["ok"]), ("installed", True))
        self.assertTrue(self.api.job_state()["job"]["stale"])                  # the modlist was read again: said so
        m = model.build(instance.load(self.root))
        self.assertEqual(m.issues, [])
        self.assertFalse(m.instance.mod("Bramble").enabled)
        self.assertEqual(m.row("Lantern.esp").source, "ModTrap - Bramble")
        jobs = self.api.state()["demaster"]["jobs"]
        self.assertEqual([(j["state"], j["disabled"], j["deactivated"]) for j in jobs],
                         [("installed", ["Bramble - Lantern Patch", "Bramble"],
                           ["BrambleLanternPatch.esp", "Collection - Bramble.esp"])])
        # A tool making an original again after the demaster: ModTrap's copy would hide the newer file. It says so.
        original = self.root / "mods" / "Lantern" / "Lantern.esp"
        keep, times = original.read_bytes(), original.stat()
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["stale"], [])
        original.write_bytes(keep + b" made again by a tool")
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["stale"], ["Lantern.esp"])
        original.write_bytes(keep)
        os.utime(original, ns=(times.st_atime_ns, times.st_mtime_ns))
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["stale"], [])
        events = self.api.get("/api/history", {})[1]
        self.assertEqual(events["events"][0]["kind"], "verified")
        self.assertEqual([(j["what"], j["state"]) for j in events["jobs"]], [("demaster", "installed")])
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 0})   # a job in place is never cleared
        self.assertEqual(len(self.api.state()["demaster"]["jobs"]), 1)
        self.assertIn("mod disabled", [e["kind"] for e in events["events"]])
        back = self.api.post("/api/demaster/revert", {"job": jobs[0]["job"]})[1]
        self.ready()
        self.assertGreater(back["restored"], 0)
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["state"], "reverted")
        self.assertEqual(self.api.get("/api/history", {})[1]["events"][0]["kind"], "reverted")
        # A reverted job is only kept for looking at: the owner can clear it. Its folder and the history stay.
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 1})
        self.assertEqual(self.api.state()["demaster"]["jobs"], [])
        after = self.api.get("/api/history", {})[1]
        self.assertEqual((after["jobs"], after["events"][0]["kind"]), ([], "reverted"))
        self.assertTrue((self.api.changes._jobs_dir() / jobs[0]["job"] / "plan.json").is_file())

    def test_revert_after_mo2_rewrote_the_lists_goes_line_by_line(self) -> None:
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        pdir = self.root / "profiles" / "Default"
        ml = pdir / "modlist.txt"
        ml.write_bytes(ml.read_bytes() + b"-Installed Meanwhile\r\n")
        job = self.api.state()["demaster"]["jobs"][0]["job"]
        back = self.api.post("/api/demaster/revert", {"job": job})[1]
        self.ready()
        self.assertEqual((back["how"], back["left"]), ("by line", []))
        text = ml.read_bytes().decode()
        self.assertIn("-Installed Meanwhile", text)
        self.assertIn("+Bramble\r\n", text)
        self.assertNotIn("ModTrap - Bramble", text)
        m = model.build(instance.load(self.root))
        self.assertEqual(m.issues, [])
        self.assertTrue(m.row("BrambleLanternPatch.esp").active)
        self.assertEqual(m.row("Lantern.esp").source, "Lantern")
        self.assertFalse((self.root / "mods" / "ModTrap - Bramble").exists())
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["state"], "reverted")

    def test_a_run_that_fails_changes_nothing_and_says_why(self) -> None:
        self.dry_run()
        self.tool = "touch"                       # a run that alters an original on disk
        self.api.post("/api/demaster/start", {})
        d = self.worked()
        self.assertEqual(d["state"], "failed")
        self.assertIn("not the file it was", d["message"])
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/install", {})

    def test_only_this_sessions_own_demasters_can_be_reverted(self) -> None:
        for job in ("../x", "add-20260101-000000", "demaster-1", None):
            with self.assertRaises(Bad):
                self.api.post("/api/demaster/revert", {"job": job})
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/revert", {"job": "demaster-20260101-000000"})


if __name__ == "__main__":
    unittest.main()
