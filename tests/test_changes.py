"""The switch (WHY§44): without it nothing the page calls can change a modlist; with it, "Add it" and Revert work
through the same guarded job, on an invented modlist."""

from __future__ import annotations

import inspect
import json
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

    def test_another_modlists_mo2_stops_a_start_before_anything_is_begun(self) -> None:
        """WHY§77: MO2 hands a command to the MO2 that is already open, whichever modlist that one is for."""
        elsewhere = str(Path(self.tmp.name) / "Another List" / "ModOrganizer.exe")
        self.api.program_paths = lambda image: [elsewhere]
        self.assertEqual((self.api.mo2()["state"], self.api.mo2()["other"]), ("closed", True))
        for path, body in (("/api/dryrun/start", {"mods": ["Bramble"]}), ("/api/probe/start", {}), ("/api/demaster/start", {}),
                           ("/api/mo2/open", {})):
            with self.assertRaises(Bad) as c:
                self.api.post(path, body)
            self.assertIn("Another Mod Organizer is open, for another modlist", str(c.exception))
        self.assertIsNone(self.api.job)
        self.assertEqual(snapshot(self.root), self.before)
        self.api.program_paths = lambda image: []                 # closed: nothing stands in the way any more
        self.assertFalse(self.api.mo2()["other"])

    def test_the_owners_settings_are_kept_and_only_known_ones(self) -> None:
        self.assertEqual(self.api.state()["settings"], {"auto_go": False, "close_mo2": False, "open_mo2_after": False,
                                                        "follow": True, "script_props": True, "retire_copies": True,
                                                        "auto_tools": False, "tools_self": True, "tool_versions": True, "tool_prebuild": True, "mo2_leave_alone": True,
                                                    "updates_at_launch": True, "updates_go": False, "site_window": False, "site_window_closes": True, "downloads_move": True, "stay_on_tab": True, "manual_placement": False, "install_on_drop": False})
        self.assertTrue(self.api.post("/api/settings", {"name": "auto_go", "value": True})[1]["auto_go"])
        self.assertTrue(self.api.state()["settings"]["auto_go"])
        for bad in ({"name": "anything", "value": True}, {"name": "auto_go", "value": "yes"}, {}):
            with self.assertRaises(Bad):
                self.api.post("/api/settings", bad)
        self.assertEqual(self.api.settings()["follow"], True)

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
        # The Process tab's stages (DESIGN§18): the dry run is done, the plan waits for the owner, the rest is to come.
        stages = {x["key"]: x for x in self.api.state()["process"]}
        self.assertEqual([(k, v["state"]) for k, v in stages.items()],
                         [("dry", "done"), ("plan", "yours"), ("change", "waiting"), ("install", "waiting")])
        self.assertIn("2 can be demastered; 2 patch only", stages["plan"]["tasks"][0]["note"])
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
        stages = {x["key"]: x for x in self.api.state()["process"]}
        self.assertEqual((stages["plan"]["state"], stages["change"]["state"], stages["install"]["state"]),
                         ("done", "done", "yours"))          # it was refused above: MO2 was open
        self.assertIn("MO2 must be closed", stages["install"]["tasks"][0]["note"])
        self.assertEqual([(t["text"], t["state"], t["note"]) for t in stages["change"]["tasks"] if t["key"].startswith("v:")],
                         [("Lantern.esp", "done", "verified"), ("Generated.esp", "done", "verified")])
        d = self.api.post("/api/demaster/install", {})[1]
        self.ready()
        self.assertEqual((d["state"], d["check"]["ok"]), ("installed", True))
        self.assertEqual({x["key"]: x["state"] for x in self.api.state()["process"]},
                         {"dry": "done", "plan": "done", "change": "done", "install": "done"})   # the modlist was read again:
        placed = {x["key"]: x for x in self.api.state()["process"]}["install"]                    # the run stays shown
        self.assertEqual((placed["state"], {t["key"]: t["state"] for t in placed["tasks"]}),
                         ("done", {"mo2": "done", "mod": "done", "off": "done", "disable": "done", "reread": "done", "health": "done"}))
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
        # Put back: the Process tab shows a demaster still to come, and the dry run of the modlist as it was no
        # longer counts as this one's (WHY§71).
        stages = {x["key"]: x for x in self.api.state()["process"]}
        self.assertEqual([v["state"] for v in stages.values()], ["waiting"] * 4)
        self.assertIn("a new one is made", stages["dry"]["note"])
        # A reverted job is only kept for looking at: the owner can clear it. Its folder and the history stay.
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 1})
        self.assertEqual(self.api.state()["demaster"]["jobs"], [])
        after = self.api.get("/api/history", {})[1]
        self.assertEqual((after["jobs"], after["events"][0]["kind"]), ([], "reverted"))
        self.assertTrue((self.api.changes._jobs_dir() / jobs[0]["job"] / "plan.json").is_file())

    def test_modtraps_copy_is_retired_once_a_tool_has_made_the_plugin_anew(self) -> None:
        """WHY§80: ModTrap's demastered copy has the higher priority and would hide the plugin a tool makes anew.
        It goes only when the new original stands without the mod; it is kept in the job's folder, not deleted."""
        from modtrap import plugin
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        job = self.api.state()["demaster"]["jobs"][0]
        mine = self.root / "mods" / "ModTrap - Bramble" / "Generated.esp"
        original = self.root / "mods" / "Tool Output" / "Generated.esp"
        self.assertTrue(mine.is_file() and original.is_file())
        self.assertEqual((job["remade"], job["retired"]), ([], []))
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/retire", {"job": job["job"]})          # nothing was made anew
        # A tool run while the mod was still named: the new original needs the mod. ModTrap's copy stays.
        original.write_bytes(original.read_bytes() + b" made again, still with the mod")
        job = self.api.state()["demaster"]["jobs"][0]
        self.assertEqual([(x["plugin"], x["ok"]) for x in job["remade"]], [("Generated.esp", False)])
        self.assertIn("still names Bramble.esp as a master", job["remade"][0]["why"])
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/retire", {"job": job["job"]})
        self.assertTrue(mine.is_file())
        # The tool's run without the mod: the new original names the game's plugin only.
        original.write_bytes(plugin.build(("Skyrim.esm",)))
        job = self.api.state()["demaster"]["jobs"][0]
        self.assertEqual([(x["plugin"], x["ok"], x["original"]) for x in job["remade"]], [("Generated.esp", True, "Tool Output")])
        self.mo2_running = True
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/retire", {"job": job["job"]})          # MO2 is open
        self.mo2_running = False
        got = self.api.post("/api/demaster/retire", {"job": job["job"]})[1]
        self.ready()
        self.assertEqual(got, {"retired": ["Generated.esp"]})
        self.assertFalse(mine.exists())
        self.assertTrue((self.api.changes._jobs_dir() / job["job"] / "retired" / "Generated.esp").is_file())   # kept
        m = model.build(instance.load(self.root))
        self.assertEqual((m.row("Generated.esp").source, m.issues), ("Tool Output", []))      # the new one counts, in its place
        job = self.api.state()["demaster"]["jobs"][0]
        self.assertEqual((job["retired"], job["remade"], job["stale"]), (["Generated.esp"], [], []))
        self.assertEqual(self.api.get("/api/history", {})[1]["events"][0]["kind"], "copy retired")
        # After a tool's run that ModTrap started this happens by itself, unless the owner's setting says no.
        self.api.changes.retire_remade()                                          # nothing left to retire: no harm

    def test_revert_brings_back_the_state_before_the_demaster_whatever_came_after(self) -> None:
        """WHY§81: after the demaster a tool ran (started by ModTrap), made a demastered plugin anew, changed and added
        files in its output mod; ModTrap retired its copy; MO2 rewrote the lists. Revert still ends where it began."""
        from modtrap import plugin
        lists_before = {k: (self.root / k).read_bytes() for k in
                        ("profiles/Default/modlist.txt", "profiles/Default/plugins.txt", "profiles/Default/loadorder.txt")}
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        job = self.api.state()["demaster"]["jobs"][0]
        out_mod = self.root / "mods" / "Tool Output"
        original = out_mod / "Generated.esp"
        # ModTrap starts the tool: what the tool may write over is kept first, once.
        self.api.changes.before_tool("Invented Tool", [original], out_mod)
        kept = self.api.changes._jobs_dir() / job["job"] / "tool-before" / "Invented_Tool" / "manifest.json"
        self.assertTrue(kept.is_file())
        # The tool's run: the plugin anew without the mod, a file changed, a file added.
        original.write_bytes(plugin.build(("Skyrim.esm",)))
        (out_mod / "meta.ini").write_bytes(b"[General]\r\nchanged by the tool\r\n") if (out_mod / "meta.ini").is_file() else None
        (out_mod / "made by the run.txt").write_bytes(b"new")
        self.api.changes.before_tool("Invented Tool", [original], out_mod)       # a second start keeps the first copy
        self.assertNotIn("made by the run.txt", kept.read_text(encoding="utf-8"))
        self.api.post("/api/demaster/retire", {"job": job["job"]})
        self.ready()
        # MO2 ran in between and wrote its lists again: the whole-file way back is closed, the line-by-line one is taken.
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"# This file was automatically generated by Mod Organizer.", b"# This file was automatically generated by Mod Organizer. "))
        # Clearing the job history never takes a job in place away: its Revert stays.
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 0})
        back = self.api.post("/api/demaster/revert", {"job": job["job"]})[1]
        self.ready()
        self.assertEqual((back["how"], back["tools"], back["tools_not_kept"]), ("by line", ["Invented Tool"], []))
        lists = {"profiles/Default/modlist.txt", "profiles/Default/plugins.txt", "profiles/Default/loadorder.txt"}
        self.assertEqual({k: v for k, v in snapshot(self.root).items() if k not in lists},
                         {k: v for k, v in self.before.items() if k not in lists})    # every file as it was, dates and all
        now = {k: (self.root / k).read_bytes() for k in lists}
        now["profiles/Default/modlist.txt"] = now["profiles/Default/modlist.txt"].replace(b"Organizer. ", b"Organizer.")   # MO2's own touch aside
        self.assertEqual(now, lists_before)                                          # and the three lists say what they said
        aside = self.api.changes._jobs_dir() / job["job"] / "set-aside-by-revert"
        self.assertTrue((aside / "Generated.esp").is_file() and (aside / "Invented_Tool" / "made by the run.txt").is_file())   # nothing lost
        m = model.build(instance.load(self.root))
        self.assertTrue(m.instance.mod("Bramble").enabled)
        self.assertEqual(m.issues, [])

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

    def _mo2_drops_the_disabled_mods_plugins(self) -> list[str]:
        """What a MO2 that runs while a mod is disabled does to its lists (WHY§83): the mod's plugins are no longer
        named in either. Returns the names dropped."""
        pdir = self.root / "profiles" / "Default"
        m = model.build(instance.load(self.root))
        gone = {p.lower() for mod in m.instance.mods if mod.kind == "mod" and not mod.enabled for p in mod.plugins
                if m.row(p) is None or m.row(p).source is None}
        self.assertTrue(gone)
        for fname in ("plugins.txt", "loadorder.txt"):
            lines = (pdir / fname).read_bytes().split(b"\r\n")
            (pdir / fname).write_bytes(b"\r\n".join(ln for ln in lines if ln.decode().lstrip("*").lower() not in gone))
        return sorted(gone)

    def test_revert_puts_back_the_plugin_lines_mo2_dropped(self) -> None:
        """WHY§83: a tool was run through MO2 after the demaster, so MO2 wrote its lists without the disabled mod's
        plugins. Revert enables the mod and puts each plugin back where it stood, active as it was."""
        pdir = self.root / "profiles" / "Default"
        lists_before = {k: (pdir / k).read_bytes() for k in ("modlist.txt", "plugins.txt", "loadorder.txt")}
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        gone = self._mo2_drops_the_disabled_mods_plugins()
        job = self.api.state()["demaster"]["jobs"][0]["job"]
        back = self.api.post("/api/demaster/revert", {"job": job})[1]
        self.ready()
        self.assertEqual((back["how"], back["placed"], back["notes"]), ("by line", len(gone), []))
        self.maxDiff = None
        self.assertEqual({k: (pdir / k).read_bytes().decode() for k in lists_before}, {k: v.decode() for k, v in lists_before.items()})     # the three lists, to the byte
        m = model.build(instance.load(self.root))
        self.assertEqual(m.issues, [])
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["unfinished"], [])
        self.assertIn("placed", self.api.get("/api/history", {})[1]["events"][0])

    def test_a_revert_that_left_plugins_out_can_be_finished(self) -> None:
        """A Revert made by a ModTrap that did not put the lines back: the mods are enabled, their plugins are in no
        list, or MO2 has since added them at the end. The job says so, stays listed, and one press puts them back."""
        pdir = self.root / "profiles" / "Default"
        lists_before = {k: (pdir / k).read_bytes() for k in ("modlist.txt", "plugins.txt", "loadorder.txt")}
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        gone = self._mo2_drops_the_disabled_mods_plugins()
        job = self.api.state()["demaster"]["jobs"][0]["job"]
        from modtrap import demaster as dm, safe as safe_mod
        work = self.api.changes._jobs_dir() / job
        done = json.loads((work / "installed.json").read_text(encoding="utf-8"))
        dm.undo_by_line(pdir, safe_mod.Safe(work / "safe"), done)                  # the old way: no lines put back
        self.api.open(str(self.root), None, session=self.api.session)
        self.ready()
        j = self.api.state()["demaster"]["jobs"][0]
        self.assertEqual((j["state"], sorted(x.lower() for x in j["unfinished"])), ("reverted", gone))
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 0})           # it stays until finished
        # MO2 opened since: it added the plugins at the end, not active.
        for fname in ("plugins.txt", "loadorder.txt"):
            (pdir / fname).write_bytes((pdir / fname).read_bytes() + b"".join(n.encode() + b"\r\n" for n in j["unfinished"]))
        self.api.open(str(self.root), None, session=self.api.session)
        self.ready()
        self.assertEqual(len(self.api.state()["demaster"]["jobs"][0]["unfinished"]), len(gone))
        with self.assertRaises(Bad):
            self.api.post("/api/demaster/revert", {"job": job})                    # a second whole Revert is not this
        out = self.api.post("/api/demaster/revert", {"job": job, "finish": True})[1]
        self.ready()
        self.assertEqual((out["how"], out["placed"], out["notes"]), ("finish", len(gone), []))
        self.assertEqual({k: (pdir / k).read_bytes() for k in lists_before}, lists_before)
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["unfinished"], [])
        self.assertEqual(self.api.get("/api/history", {})[1]["events"][0]["kind"], "revert finished")

    def test_a_tools_run_counts_for_the_demaster_in_place_and_no_longer_after_a_revert(self) -> None:
        """MT29, WHY§91: what makes a tool's step done is ModTrap's own note of the tool's run, kept with the demaster
        that was in place. No demaster in place, no note; a Revert takes it away; a new demaster starts afresh."""
        ch = self.api.changes
        ch.tool_ran("Invented Tool", 3)                                   # nothing in place: nothing to note it with
        self.assertEqual(ch.tools_run(), {})
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        self.assertEqual(ch.tools_run(), {})
        ch.tool_ran("Invented Tool", 0)                                   # closed without output: not a run that counts
        self.assertEqual(ch.tools_run(), {})
        ch.tool_ran("Invented Tool", 3)
        self.assertEqual(ch.tools_run()["Invented Tool"]["files"], 3)
        job = self.api.state()["demaster"]["jobs"][0]["job"]
        self.api.post("/api/demaster/revert", {"job": job})
        self.ready()
        self.assertEqual(ch.tools_run(), {})                              # reverted: every tool is to run again next time

    def test_nothing_is_started_while_modtrap_is_still_reading_or_scanning(self) -> None:
        """WHY§92: ModTrap's own scans are told in its state, and while one goes every start is refused in words the
        one go waits on. When it has finished, the same start goes through."""
        import threading
        from modtrap import steps
        hold, real = threading.Event(), steps.look_deeper

        def slow(*args, **kw):
            hold.wait(10)
            return real(*args, **kw)

        steps.look_deeper = slow
        try:
            self.assertEqual(self.api.state()["working"], [])
            self.api.post("/api/steps", {"mods": ["Bramble"]})                       # the page asks for the steps: a scan begins
            self.assertEqual([w["key"] for w in self.api.state()["working"]], ["steps"])
            self.assertIn("still at work", self.api.unsettled())
            for path, body in (("/api/dryrun/start", {"mods": ["Bramble"]}), ("/api/demaster/start", {}),
                               ("/api/tool/start", {"title": "xEdit"}), ("/api/probe/start", {})):
                with self.assertRaises(Bad) as refused:
                    self.api.post(path, body)
                self.assertIn("still at work", str(refused.exception), path)
        finally:
            hold.set()
            steps.look_deeper = real
        for _ in range(300):
            if not self.api.state()["working"]:
                break
            time.sleep(0.02)
        self.assertEqual((self.api.state()["working"], self.api.unsettled()), ([], ""))
        self.dry_run()                                                              # and now it starts

    def test_revert_sets_aside_a_plugin_a_tool_wrote_anew_in_modtraps_own_mod(self) -> None:
        """WHY§95: a tool run through MO2 writes its plugin to the file that wins, which after a demaster is ModTrap's
        copy in ModTrap's mod. Revert does not leave that file behind: it is set aside, and ModTrap's mod goes."""
        lists = {k: (self.root / "profiles" / "Default" / k).read_bytes() for k in ("modlist.txt", "plugins.txt", "loadorder.txt")}
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        job = self.api.state()["demaster"]["jobs"][0]
        own = self.root / "mods" / job["mod_name"] / "Generated.esp"
        self.assertTrue(own.is_file())
        own.write_bytes(own.read_bytes() + b"written anew by the tool")
        back = self.api.post("/api/demaster/revert", {"job": job["job"]})[1]
        self.ready()
        self.assertEqual(back["left"], [])
        self.assertFalse((self.root / "mods" / job["mod_name"]).exists())
        aside = self.api.changes._jobs_dir() / job["job"] / "set-aside-by-revert" / "modtraps-own-mod" / "Generated.esp"
        self.assertTrue(aside.read_bytes().endswith(b"written anew by the tool"))                 # kept, not lost
        self.assertEqual({k: v for k, v in lists.items()}, {k: (self.root / "profiles" / "Default" / k).read_bytes() for k in lists})
        self.assertEqual(sorted(snapshot(self.root)), sorted(self.before))                       # the same files as it began with

    def test_a_mod_folder_an_earlier_revert_left_behind_is_tidied_with_one_press(self) -> None:
        """WHY§96: a Revert made before 0.3.25 left a plugin that a tool had written anew in ModTrap's own mod, and
        the mod's folder with it. The job says so, stays listed, and one press sets the plugin aside and takes the
        folder away; nothing else is touched."""
        self.dry_run()
        self.api.post("/api/demaster/start", {})
        self.worked()
        self.api.post("/api/demaster/install", {})
        self.ready()
        job = self.api.state()["demaster"]["jobs"][0]
        own = self.root / "mods" / job["mod_name"] / "Generated.esp"
        own.write_bytes(own.read_bytes() + b"written anew by the tool")
        # The earlier Revert: by line, leaving what was no longer as ModTrap made it.
        from modtrap import demaster as dm, safe as safe_mod
        work = self.api.changes._jobs_dir() / job["job"]
        done = json.loads((work / "installed.json").read_text(encoding="utf-8"))
        m = model.build(instance.load(self.root))
        left = dm.undo_by_line(self.root / "profiles" / "Default", safe_mod.Safe(work / "safe"), done, m.instance)["left"]
        self.assertEqual([Path(p).name for p in left], ["Generated.esp"])
        self.api.open(str(self.root), None, session=self.api.session)
        self.ready()
        j = self.api.state()["demaster"]["jobs"][0]
        self.assertEqual((j["state"], j["unfinished"], j["left_behind"]), ("reverted", [], ["Generated.esp"]))
        self.assertEqual(self.api.post("/api/jobs/clear", {})[1], {"cleared": 0})              # it stays until tidied
        lists = {k: (self.root / "profiles" / "Default" / k).read_bytes() for k in ("modlist.txt", "plugins.txt", "loadorder.txt")}
        out = self.api.post("/api/demaster/revert", {"job": job["job"], "finish": True})[1]
        self.ready()
        self.assertEqual((out["how"], out["placed"], out["set_aside"], out["notes"]), ("finish", 0, 1, []))
        self.assertFalse((self.root / "mods" / job["mod_name"]).exists())
        self.assertTrue((work / "set-aside-by-revert" / "modtraps-own-mod" / "Generated.esp").is_file())
        self.assertEqual(lists, {k: (self.root / "profiles" / "Default" / k).read_bytes() for k in lists})   # the lists untouched
        self.assertEqual(self.api.state()["demaster"]["jobs"][0]["left_behind"], [])

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
