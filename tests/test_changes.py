"""The switch (WHY§44): without it nothing the page calls can change a modlist; with it, "Add it" and Revert work
through the same guarded job, on an invented modlist."""

from __future__ import annotations

import inspect
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, instance, logbook, model
from modtrap.server import Bad

from .test_adding import invented
from .test_intake import NEW_MOD, snapshot
from .test_unpack import zipped


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
        self.api.changes = changes.Changes(self.api)
        body = self.dropped()
        p = self.api.post("/api/add/plan", body)[1]
        self.assertEqual([(x["name"], x["staged"], x["before"]) for x in p["mods"]],
                         [("Thistle", False, "Outputs_separator"), ("Heather", True, "Outputs_separator")])
        self.assertEqual(sorted(x["name"] for x in p["plugins"]), ["Heather.esp", "Thistle.esp"])
        self.assertIs(p["mo2_closed"], True)
        self.assertEqual(snapshot(self.root), self.before)               # a plan changes nothing

    def test_add_it_then_revert(self) -> None:
        self.api.changes = changes.Changes(self.api)
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

    def test_mo2_open_or_unknown_changes_nothing(self) -> None:
        self.api.changes = changes.Changes(self.api)
        body = self.dropped()
        for state in (True, None):
            self.mo2_running = state
            self.assertIsNot(self.api.post("/api/add/plan", body)[1]["mo2_closed"], True)
            with self.assertRaises(Bad):
                self.api.post("/api/add/run", body)
            self.assertEqual(snapshot(self.root), self.before)

    def test_only_this_sessions_own_adds_can_be_reverted(self) -> None:
        self.api.changes = changes.Changes(self.api)
        for job in ("../../somewhere", "add-1", "dry-20260101-000000", 7):
            with self.assertRaises(Bad):
                self.api.post("/api/add/revert", {"job": job})


if __name__ == "__main__":
    unittest.main()
