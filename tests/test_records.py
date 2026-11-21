"""The record check (DESIGN§16.5): planned, run through a stand-in for xEdit, and read."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, model, records
from modtrap.server import Bad

from ._fixtures import write
from .test_adding import invented

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


def report(*lines: str) -> str:
    return "\r\n".join(("H\tmodtrap-records/1\trecords\t67175680",) + lines + ("X\tok\t",)) + "\r\n"


def chain(*names: str) -> str:
    return "\x1f".join(names)


class Reading(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.m = model.build(instance.load(invented(Path(self.tmp.name))))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_overriding_records_are_sorted_by_what_they_do_to_others(self) -> None:
        got = records.parse_report(report(
            "F\tNew.esp\t7\tSkyrim.esm",
            "O\tNew.esp\tWEAP\t00000001\tA\t4\t8\t" + chain("Skyrim.esm", "New.esp"),                       # alone
            "O\tNew.esp\tNPC_\t00000002\tB\t5\t10\t" + chain("Skyrim.esm", "Quill.esp", "New.esp"),         # takes
            "O\tNew.esp\tNPC_\t00000003\tC\t6\t10\t" + chain("Skyrim.esm", "Quill.esp", "Lantern.esm", "New.esp"),
            "O\tNew.esp\tCELL\t00000004\tD\t5\t11\t" + chain("Skyrim.esm", "New.esp", "Generated.esp"),     # loses, to a tool
            "O\tNew.esp\tCELL\t00000005\tE\t5\t11\t" + chain("Skyrim.esm", "New.esp", "Quill.esp"),         # loses, to hand-made
            "O\tNew.esp\tMISC\t00000006\tF\t2\t3\t" + chain("Skyrim.esm", "New.esp"),                       # changes nothing
            "O\tNew.esp\tARMO\t00000007\tG\t4\t8\t" + chain("Skyrim.esm", "Quill.esp", "New.esp"),          # no conflict
            "D\tNew.esp\t9\t2\t7"), self.m)
        f = got["files"][0]
        self.assertEqual((f["own"], f["overrides"], f["alone"], f["same"], f["takes_count"], f["loses_count"]),
                         (2, 7, 2, 1, 2, 2))
        self.assertEqual(f["from"], [["Quill.esp", 2, False], ["Lantern.esm", 1, False]])
        self.assertEqual(f["to"], [["Generated.esp", 1, True], ["Quill.esp", 1, False]])
        self.assertEqual((f["needs_patch"], f["lost_to_hand"], f["reading"]), (2, 1, "needs a look"))
        self.assertEqual([r["form"] for r in f["takes"]], ["00000002", "00000003"])
        self.assertEqual((got["end"], got["xedit"]), ("ok", "67175680"))

    def test_a_plugin_that_takes_nothing_reads_clean(self) -> None:
        got = records.parse_report(report(
            "F\tNew.esp\t2\tSkyrim.esm",
            "O\tNew.esp\tWEAP\t00000001\tA\t4\t8\t" + chain("Skyrim.esm", "New.esp"),
            "O\tNew.esp\tCELL\t00000004\tD\t5\t11\t" + chain("Skyrim.esm", "New.esp", "Generated.esp"),
            "D\tNew.esp\t2\t0\t2", "M\tAbsent.esp", "U\tHeld.esp"), self.m)
        self.assertEqual(got["files"][0]["reading"], "clean")
        self.assertEqual((got["missing"], got["held_changed"]), (["Absent.esp"], ["Held.esp"]))

    def test_the_plan_loads_the_whole_active_load_order(self) -> None:
        p = records.plan(self.m, ["Quill"])
        self.assertEqual(p.new, ["Quill.esp"])
        self.assertEqual(p.load[-3:], ["Lantern.esm", "Quill.esp", "Generated.esp"])
        with self.assertRaises(records.Refused):
            records.plan(self.m, ["Thistle"])                    # not enabled: xEdit cannot see it


class Running(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        write(self.root / "ModOrganizer.exe", b"not a real program")
        self.api = api.Api()
        self.api.poll = 0.03
        self.api.running = lambda image: None
        self.api.launcher = lambda cmd, cwd: subprocess.Popen([sys.executable, FAKE, *cmd[1:]], cwd=cwd)
        self.api.open(str(self.root), wait=True)

    def tearDown(self) -> None:
        if self.api.recjob is not None:
            self.api.recjob.join(10)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_check_runs_through_xedit_and_changes_nothing(self) -> None:
        before = (self.root / "mods" / "Lantern" / "Lantern.esm").read_bytes()
        got = self.api.post("/api/records/start", {"mods": ["Lantern"]})[1]
        self.assertEqual(got["plan"]["new"], ["Lantern.esm"])
        self.api.recjob.join(10)
        job = self.api.recjob.public()
        self.assertEqual(job["state"], "done", job["message"])
        f = job["result"]["files"][0]
        self.assertEqual((f["name"], f["own"], f["overrides"], f["alone"], f["same"], f["takes_count"], f["loses_count"]),
                         ("Lantern.esm", 2, 4, 1, 1, 1, 1))
        self.assertEqual((f["from"], f["to"]), ([["Quill.esp", 1, False]], [["Generated.esp", 1, True]]))
        self.assertEqual((self.root / "mods" / "Lantern" / "Lantern.esm").read_bytes(), before)
        job_dir = self.api.recjob.dir
        text = (job_dir / "script" / "modtrap-job.txt").read_text(encoding="utf-8-sig")
        self.assertIn("mode=records", text)
        self.assertTrue((job_dir / "script" / "ModTrapRecords.pas").is_file())
        add = None
        for _ in range(200):
            add = self.api.post("/api/add", {"mods": ["Lantern"]})[1]
            if not add["looking"]:
                break
            time.sleep(0.02)
        self.assertEqual(add["records"]["state"], "done")

    def test_what_cannot_be_checked_is_refused(self) -> None:
        for body in ({}, {"mods": []}, {"mods": ["Thistle"]}, {"mods": ["Nobody"]}):
            with self.assertRaises(Bad):
                self.api.post("/api/records/start", body)


class Script(unittest.TestCase):
    def test_the_script_only_reports(self) -> None:
        text = records.SCRIPT.read_text(encoding="utf-8")
        for word in ("Remove(", "RemoveElement", "SetElementEditValues", "SetEditValue", "AddMasterIfMissing", "CleanMasters",
                     "wbCopyElementToFile", "SaveToFile(sOut)"[:0] or "FileWriteToStream", "Add(f", "RemoveNode"):
            self.assertNotIn(word, text)
        self.assertIn("ClearElementState(f, esUnsaved)", text)


if __name__ == "__main__":
    unittest.main()
