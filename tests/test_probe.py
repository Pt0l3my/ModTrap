"""The probe (DESIGN§9, WHY§47): the whole cycle on invented plugins, with stand-ins for MO2 and xEdit; and the
gate it puts in front of real work."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, logbook, probe, probejob
from modtrap.server import Bad

from . import _fixtures as fx
from .test_adding import invented
from .test_intake import NEW_MOD, snapshot
from .test_unpack import zipped

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


class Probing(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")
        self.api = api.Api()
        self.api.poll = 0.03
        self.mo2_running: bool | None = False
        self.api.running = lambda image: self.mo2_running if image == "ModOrganizer.exe" else None
        self.tool = "clean"
        self.after_xedit = None                # what "MO2" does to its lists when it has run
        self.api.launcher = self.launch
        self.api.changes = changes.Changes(self.api)
        self.api.open(str(self.root), wait=True)
        self.before = snapshot(self.root)

    def tearDown(self) -> None:
        if self.api.changes.probe is not None:
            self.api.changes.probe.join(30)
        self.ready()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def launch(self, cmd, cwd):
        if self.after_xedit is not None:
            self.after_xedit()
        return subprocess.Popen([sys.executable, FAKE, *cmd[1:-1], self.tool, "--mods", str(self.root / "mods")], cwd=cwd)

    def ready(self) -> None:
        for _ in range(500):
            if self.api.status == "ready":
                return
            time.sleep(0.02)

    def run_probe(self) -> dict:
        self.api.post("/api/probe/start", {})
        self.api.changes.probe.join(60)
        self.ready()
        return self.api.state()["probe"]

    def results(self, p: dict) -> dict:
        return {s["key"]: s["result"] for s in p["steps"]}

    def test_the_probe_passes_and_leaves_the_modlist_as_it_was(self) -> None:
        p = self.run_probe()
        self.assertEqual(p["state"], "passed", p)
        self.assertEqual(set(self.results(p).values()), {"passed"})
        self.assertEqual([s["key"] for s in p["steps"]], ["write", "dry", "kept", "apply", "untouched", "install", "revert"])
        self.assertEqual(p["xedit"], "67175680")
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(p["reason"], "")                          # real work is now allowed

    def test_real_work_waits_for_the_probe(self) -> None:
        data = zipped(NEW_MOD)
        rec = self.api.upload("Heather.zip", len(data), io.BytesIO(data))
        body = {"mods": [], "staged": [rec["id"]]}
        for _ in range(300):
            got = self.api.post("/api/add", body)[1]
            if not got["looking"] and not got["unpacking"]:
                break
            time.sleep(0.02)
        with self.assertRaises(Bad) as c:
            self.api.post("/api/add/run", body)
        self.assertIn("probe", str(c.exception))
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(self.run_probe()["state"], "passed")
        for _ in range(300):                                       # the modlist was read again after the probe
            got = self.api.post("/api/add", body)[1]
            if not got["looking"]:
                break
            time.sleep(0.02)
        self.api.post("/api/add/run", body)                        # allowed now
        self.ready()
        self.assertTrue((self.root / "mods" / "Heather").is_dir())

    def test_xedit_reading_the_plugins_otherwise_fails_the_probe_and_says_how(self) -> None:
        self.tool = "probe-odd"                                    # this xEdit calls the list something else
        p = self.run_probe()
        self.assertEqual(p["state"], "failed")
        r = self.results(p)
        self.assertEqual((r["write"], r["dry"], r["kept"]), ("passed", "failed", ""))
        detail = next(s["detail"] for s in p["steps"] if s["key"] == "dry")
        self.assertIn("Odd Name", detail)
        self.assertEqual(snapshot(self.root), self.before)         # and everything was put back
        self.assertIn("did not pass", p["reason"])
        self.assertEqual(p["left_behind"], [])

    def test_mo2_reordering_the_lists_fails_the_probe(self) -> None:
        def scramble() -> None:
            f = self.root / "profiles" / "Default" / "plugins.txt"
            lines = f.read_bytes().split(b"\r\n")
            head, rest = lines[0], [x for x in lines[1:] if x]
            f.write_bytes(b"\r\n".join([head] + rest[::-1]) + b"\r\n")
            os.utime(f, None)                                      # the newer of the two lists gives the order
            self.after_xedit = None
        self.after_xedit = scramble
        modlist_before = (self.root / "profiles" / "Default" / "modlist.txt").read_bytes()
        p = self.run_probe()
        r = self.results(p)
        self.assertEqual((p["state"], r["dry"], r["kept"]), ("failed", "passed", "failed"))
        self.assertIn("load order differs", next(s["detail"] for s in p["steps"] if s["key"] == "kept"))
        # MO2 had rewritten a list, so the old files are not put back over it: only ModTrap's lines are taken out.
        self.assertFalse((self.root / "mods" / probejob.BAD_MOD).exists())
        self.assertEqual(p["left_behind"], [])
        text = (self.root / "profiles" / "Default" / "modlist.txt").read_bytes()
        self.assertNotIn(b"ModTrap Probe", text)
        self.assertEqual(text, modlist_before)
        plugins = (self.root / "profiles" / "Default" / "plugins.txt").read_bytes()
        self.assertNotIn(b"ModTrap Probe", plugins)
        self.assertEqual(plugins.split(b"\r\n")[1], b"*Generated.esp")          # "MO2's" own reordering is kept

    def test_mo2_open_the_probe_does_not_begin(self) -> None:
        for running in (True, None):
            self.mo2_running = running
            with self.assertRaises(Bad):
                self.api.post("/api/probe/start", {})
        self.assertEqual(snapshot(self.root), self.before)

    def test_an_earlier_probes_mod_is_named_not_overwritten(self) -> None:
        fx.write(self.root / "mods" / probejob.BAD_MOD / probe.BAD, b"left by an earlier probe")
        p = self.run_probe()
        self.assertEqual((p["state"], self.results(p)["write"]), ("failed", "failed"))
        self.assertEqual((self.root / "mods" / probejob.BAD_MOD / probe.BAD).read_bytes(), b"left by an earlier probe")

    def test_the_outcome_is_kept_for_the_next_start(self) -> None:
        self.run_probe()
        again = api.Api()
        again.changes = changes.Changes(again)
        again.running = self.api.running
        self.assertTrue(again.restore())
        for _ in range(500):
            if again.status == "ready":
                break
            time.sleep(0.02)
        p = again.state()["probe"]
        self.assertEqual((p["state"], p["reason"]), ("passed", ""))

    def test_a_pass_counts_only_for_the_scripts_it_ran(self) -> None:
        from unittest import mock
        self.run_probe()
        self.assertEqual(self.api.state()["probe"]["reason"], "")
        with mock.patch.object(probejob, "scripts_mark", lambda: "another version of the scripts"):
            self.assertIn("scripts have changed", self.api.state()["probe"]["reason"])
            with self.assertRaises(Bad):
                self.api.post("/api/demaster/plan", {})


if __name__ == "__main__":
    unittest.main()
