"""The tool check through xEdit (MT23) and the owner's choice on a tool's step (MT24)."""

import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, model, probe, records, steps, toolcheck
from modtrap.server import Bad
from tests import _fixtures as fx
from tests.test_steps import dry_done

FAKE = str(Path(__file__).with_name("fake_xedit.py"))
CORE = ("Core.esp",)
A, B, C, D = 0x00000A00, 0x00000B00, 0x00000C00, 0x00000D00
TOLD = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}],
        "Inn - Bramble Patch.esp": [{"form": "02000C00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}


def pf(masters, *globs):
    recs = [probe.glob(form, "MT_%X" % (form & 0xFFFFFF), value) for form, value in globs]
    return probe.plugin_file(list(masters), [probe.group(b"GLOB", recs)], len(recs), 0x900, "invented")


def invented(root: Path) -> Path:
    """The mod Bramble changes a record of Core's; a patch made for it changes another. Three plugins tools made
    hold those records: two of a patcher that writes in its own form, one of a merging tool."""
    fx.make_instance(root, [
        ("+", "PG Output", {"PGPatcher.esp": pf(CORE, (D, 1.0))}),
        ("+", "Patcher Output", {"Synthesis.esp": pf(CORE, (A, 7.0), (B, 1.0)), "Synthesis Gameplay.esp": pf(CORE, (A, 3.0)),
                                 "Bashed Patch, 0.esp": pf(CORE, (B, 1.0), (C, 9.0))}),
        ("+", "Inn Patches", {"Inn - Bramble Patch.esp": pf(CORE + ("Bramble.esp",), (C, 9.0))}),
        ("+", "Bramble", {"Bramble.esp": pf(CORE, (A, 7.0), (B, 1.0), (0x01000800, 5.0))}),
        ("-", "Thorn", {"Thorn.esp": pf(CORE, (A, 2.0))}),
        ("+", "Core", {"Core.esp": pf((), (A, 1.0), (B, 1.0), (C, 1.0), (D, 1.0))}),
    ], load_order=["Core.esp", "Bramble.esp", "Inn - Bramble Patch.esp", "Synthesis.esp", "Synthesis Gameplay.esp", "Bashed Patch, 0.esp", "PGPatcher.esp"],
        profile_settings="[custom_overwrites]\r\nParallaxGen=PG Output\r\n")
    fx.write(root / "ModOrganizer.exe", b"not a real program")
    return root


class ThePlanAndTheReport(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "List")
        self.m = model.build(instance.load(self.root))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_plan_names_the_tools_plugins_the_leaving_ones_and_loads_everything(self):
        p = toolcheck.plan(self.m, ["Bramble"], TOLD)
        self.assertEqual(p.new, ["Synthesis.esp", "Synthesis Gameplay.esp", "Bashed Patch, 0.esp"])     # a tool that works on files is not asked
        self.assertEqual(p.gone, ["Bramble.esp", "Inn - Bramble Patch.esp"])                            # the mod's, and the patch made for it
        self.assertEqual(sorted(p.made), ["Bashed Patch, 0.esp", "PGPatcher.esp", "Synthesis Gameplay.esp", "Synthesis.esp"])
        self.assertEqual(p.load[-7:], ["Core.esp", "Bramble.esp", "Inn - Bramble Patch.esp", "Synthesis.esp", "Synthesis Gameplay.esp",
                                       "Bashed Patch, 0.esp", "PGPatcher.esp"])                     # the whole active load order
        self.assertEqual(toolcheck.plan(self.m, ["Bramble"]).gone, ["Bramble.esp"])                     # without a dry run: the mod's own
        with self.assertRaises(toolcheck.Refused) as e:
            toolcheck.plan(self.m, ["Thorn"])                   # disabled: xEdit cannot read its records
        self.assertIn("before the demaster is put in place", str(e.exception))
        with self.assertRaises(toolcheck.Refused):
            toolcheck.plan(self.m, ["Nobody"])

    def test_the_job_tells_the_script_what_to_compare(self):
        p = toolcheck.plan(self.m, ["Bramble"], TOLD)
        job_dir = Path(self.tmp.name) / "job"
        man = toolcheck.prepare(self.m, p, job_dir)
        text = (job_dir / "script" / "modtrap-job.txt").read_text(encoding="utf-8-sig")
        for line in ("mode=tools", "tool.count=3", "tool.0=Synthesis.esp", "gone.count=2", "gone.1=Inn - Bramble Patch.esp", "made.count=4"):
            self.assertIn(line + "\n", text)
        self.assertTrue((job_dir / "script" / "ModTrapTools.pas").is_file())
        self.assertEqual((man["mods"], sorted(man["sha256"]), man["stamp"]["Synthesis.esp"]),
                         (["Bramble"], sorted(p.new), toolcheck.stamp(self.m.row("Synthesis.esp").path)))
        self.assertIn("ModTrapTools.pas", " ".join(toolcheck.command(p, job_dir)))

    def test_the_report_gives_each_plugin_one_of_three_verdicts(self):
        got = toolcheck.parse_report("\r\n".join([
            "H\tmodtrap-tools/1\ttools\t67175680", "P\tC:\\Game\\Data\\\t12", "N\tGone.esp",
            "F\tOne.esp\t40", "K\tOne.esp\t00000A00\tGLOB\tCore.esp\tBramble.esp\tCore.esp\tFLTV\tEDID\t",
            "Y\tOne.esp\t00000A00\tmod\tFLTV - Value\t7.0\t7.0\t1.0", "S\tOne.esp\t5\t2\t1\t0\t1\t1",
            "F\tTwo.esp\t9", "K\tTwo.esp\t00000C00\tGLOB\tCore.esp\tBramble.esp\t\t\t\tFLTV,?", "S\tTwo.esp\t1\t0\t0\t1\t0\t0",
            "F\tThree.esp\t3", "S\tThree.esp\t2\t1\t0\t0\t1\t0", "F\tFour.esp\t1", "M\tAbsent.esp", "U\tHeld.esp", "X\tok\t"]))
        by = {f["name"]: f for f in got["files"]}
        self.assertEqual({n: f["verdict"] for n, f in by.items()}, {"One.esp": "mod", "Two.esp": "own", "Three.esp": "clear", "Four.esp": ""})
        one = by["One.esp"]
        self.assertEqual((one["held"], one["last_else"], one["mod"], one["own"], one["next"], one["same"]), (5, 2, 1, 0, 1, 1))
        self.assertEqual(one["rows"], [{"form": "00000A00", "kind": "GLOB", "owner": "Core.esp", "by": "Bramble.esp", "next_by": "Core.esp",
                                        "mod": ["FLTV"], "next": ["EDID"], "own": []}])
        self.assertEqual(one["values"], [{"form": "00000A00", "what": "mod", "part": "FLTV - Value", "tool": "7.0", "mod": "7.0", "next": "1.0"}])
        self.assertEqual(by["Two.esp"]["rows"][0]["own"], ["FLTV", "?"])
        self.assertEqual((got["missing"], got["held_changed"], got["end"], got["xedit"]), (["Gone.esp", "Absent.esp"], ["Held.esp"], "ok", "67175680"))


class TheScript(unittest.TestCase):
    def test_it_only_reports(self):
        text = toolcheck.SCRIPT.read_text(encoding="utf-8")
        for word in ("Remove(", "RemoveElement", "SetElementEditValues", "SetEditValue", "AddMasterIfMissing", "CleanMasters",
                     "wbCopyElementToFile", "FileWriteToStream", "RemoveNode", "AddElement", "Add(f"):
            self.assertNotIn(word, text)
        self.assertIn("ClearElementState(f, esUnsaved)", text)

    def test_it_calls_nothing_the_scripts_that_have_run_on_a_real_xedit_do_not_call(self):
        """No xEdit runs here. So the new script is held to what the dry run's and the record check's scripts use,
        which have run on the owner's PC: every name it calls is one of theirs, or its own."""
        def code(path: Path) -> str:
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"\{.*?\}", " ", text, flags=re.S)        # comments
            text = re.sub(r"//[^\n]*", " ", text)
            return re.sub(r"'(?:[^']|'')*'", "''", text)             # what is in quotes is no code
        new = code(toolcheck.SCRIPT)
        proven = code(records.SCRIPT) + code(records.SCRIPT.with_name("ModTrap.pas"))
        own = set(re.findall(r"\b(?:function|procedure)\s+(\w+)", new))
        calls = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", new)) | set(re.findall(r"\.([A-Za-z_]\w*)", new))
        known = set(re.findall(r"\b([A-Za-z_]\w*)\b", proven))
        self.assertEqual(sorted(calls - own - known), [])
        for word in re.findall(r"\b(Continue|Break)\b", new):       # the proven scripts use neither
            self.fail("the script uses %s, which no script that has run uses" % word)
        # Every begin and every try has its end, and the unit its own: as in the scripts that run.
        def balance(text: str) -> int:
            words = re.findall(r"\b(begin|try|end)\b", text, flags=re.I)
            return sum(1 for w in words if w.lower() != "end") + 1 - sum(1 for w in words if w.lower() == "end")
        self.assertEqual((balance(code(records.SCRIPT)), balance(code(records.SCRIPT.with_name("ModTrap.pas"))), balance(new)), (0, 0, 0))


class ThroughThePage(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "List")
        self.api = api.Api()
        self.api.poll = 0.03
        self.api.running = lambda image: None
        self.api.launcher = lambda cmd, cwd: subprocess.Popen([sys.executable, FAKE, *cmd[1:]], cwd=cwd)
        self.api.open(str(self.root), wait=True)
        self.m = self.api.model

    def tearDown(self):
        if self.api.checkjob is not None:
            self.api.checkjob.join(10)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def steps(self, **more):
        deep = steps.look_deeper(self.m, ["Bramble"], TOLD)
        got = steps.compile_steps(self.m, ["Bramble"], dry_done("Bramble"), deep, auto=True, **more)["steps"]
        return {x["key"]: x for x in got}

    def checked(self):
        got = self.api.post("/api/toolcheck/start", {"mods": ["Bramble"]})[1]
        self.assertEqual((got["mods"], got["plugins"]), (["Bramble"], 3))
        self.api.checkjob.join(10)
        self.assertEqual(self.api.checkjob.state, "done", self.api.checkjob.message)
        return self.api._checked_for(["Bramble"])

    def test_before_a_check_the_step_offers_one_where_bytes_could_not_settle_it(self):
        by = self.steps()
        self.assertEqual((by["tool:Synthesis"]["check"], by["tool:Synthesis"]["tool"], by["tool:Synthesis"]["values"]), ("offer", "Synthesis", []))
        self.assertEqual(by["tool:Wrye Bash"]["check"], "offer")
        # With the mod disabled the check cannot be made: said, not offered.
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Bramble\r\n", b"-Bramble\r\n"))
        self.m = model.build(instance.load(self.root))
        told = dict(TOLD)
        deep = steps.look_deeper(self.m, ["Bramble"], told)
        by = {x["key"]: x for x in steps.compile_steps(self.m, ["Bramble"], dry_done("Bramble"), deep, auto=True)["steps"]}
        self.assertIn(by.get("tool:Synthesis", {}).get("check", "needs the mod"), ("needs the mod", ""))

    def test_the_check_runs_through_xedit_changes_nothing_and_its_verdicts_stand_in_the_steps(self):
        files = {n: (self.root / "mods" / "Patcher Output" / n).read_bytes() for n in ("Synthesis.esp", "Synthesis Gameplay.esp", "Bashed Patch, 0.esp")}
        found = self.checked()
        self.assertEqual({k: v["verdict"] for k, v in found["files"].items()},
                         {"synthesis.esp": "mod", "synthesis gameplay.esp": "clear", "bashed patch, 0.esp": "own"})
        self.assertEqual({n: (self.root / "mods" / "Patcher Output" / n).read_bytes() for n in files}, files)
        self.assertEqual(self.api._check_public()["state"], "done")
        self.assertIsNone(self.api._checked_for(["Bramble", "Core"]))               # a check is for the mods it was made for
        by = self.steps(checked=found)
        syn = by["tool:Synthesis"]
        # Proof, by what the fields mean: the title has no "to be sure", the values are shown, nothing more to check.
        self.assertEqual((syn["title"], syn["check"]), ("Run Synthesis again", "done"))
        self.assertIn("Synthesis.esp holds, in 1 record(s), what the mod says where the next in line says something else", syn["why"])
        self.assertIn("What speaks against it: Synthesis Gameplay.esp, compared through xEdit by what the fields mean", syn["why"])
        self.assertEqual(syn["values"], [{"plugin": "Synthesis.esp", "form": "00000A00", "part": "FLTV - Value", "tool": "7.000000", "mod": "7.000000", "next": "1.000000"}])
        folds = [i["details"] for i in syn["items"] if "details" in i]
        self.assertTrue(folds[0]["summary"].startswith("Synthesis.esp (") and "checked through xEdit" in folds[0]["summary"])
        self.assertIn("GLOB 00000A00 of Core.esp · Bramble.esp has the last word, next in line is Core.esp · as the mod: FLTV · of its own: nothing · as the next in line: nothing",
                      folds[0]["lines"])
        # A value of the tool's own where the mod has the last word: it cannot be ruled out, and is said so.
        bash = by["tool:Wrye Bash"]
        self.assertEqual(bash["title"], "Run Wrye Bash again, to be sure")
        self.assertIn("neither the mod's nor the next in line's", bash["why"])

    def test_a_patcher_whose_every_copy_says_what_the_next_in_line_says_is_cleared(self):
        found = self.checked()
        for f in found["files"].values():                       # as if xEdit had found nothing of the mod anywhere
            f.update(verdict="clear", mod=0, own=0, rows=[], values=[])
        by = self.steps(checked=found)
        self.assertNotIn("tool:Synthesis", by)
        self.assertNotIn("tool:Wrye Bash", by)
        cleared = [i["text"] for i in by["tools-clear"]["items"]]
        self.assertTrue(any(t.startswith("Synthesis: Synthesis.esp, compared through xEdit by what the fields mean") for t in cleared))

    def test_a_plugin_written_anew_since_is_judged_by_its_bytes_again(self):
        found = self.checked()
        path = self.root / "mods" / "Patcher Output" / "Synthesis.esp"
        path.write_bytes(pf(CORE, (A, 7.0), (B, 1.0), (D, 1.0)))            # the tool ran: another file
        self.m = model.build(instance.load(self.root))
        by = self.steps(checked=found)
        self.assertIn("Synthesis.esp holds, in 1 record(s), a value it has from the mod: without the mod the load order", by["tool:Synthesis"]["why"])
        self.assertEqual(by["tool:Synthesis"]["check"], "offer")

    def test_a_run_that_changes_a_plugin_fails_the_check(self):
        self.api.launcher = lambda cmd, cwd: subprocess.Popen([sys.executable, FAKE, *cmd[1:-1], "touch", str(self.root / "mods" / "Patcher Output" / "Synthesis.esp")], cwd=cwd)
        self.api.post("/api/toolcheck/start", {"mods": ["Bramble"]})
        self.api.checkjob.join(10)
        self.assertEqual(self.api.checkjob.state, "failed")
        self.assertIn("not the files they were before the check", self.api.checkjob.message)
        self.assertIsNone(self.api._checked_for(["Bramble"]))

    def test_what_cannot_be_checked_is_refused(self):
        for body in ({}, {"mods": []}, {"mods": ["Thorn"]}, {"mods": ["Nobody"]}):
            with self.assertRaises(Bad):
                self.api.post("/api/toolcheck/start", body)
        with self.assertRaises(Bad):
            self.api.post("/api/toolcheck/stop", {})

    def test_the_owner_may_leave_a_tool_until_its_next_run_and_take_that_back(self):
        """MT24."""
        self.assertEqual((self.steps()["tool:Synthesis"]["state"], self.steps()["tool:Synthesis"]["leave"]), ("to do", True))
        self.assertEqual(self.api.post("/api/steps/tool/leave", {"mods": ["Bramble"], "tool": "Synthesis", "leave": True})[1], {"tool": "Synthesis", "left": True})
        left = self.api._tools_left(["Bramble"])
        self.assertEqual(list(left), ["Synthesis"])
        self.assertEqual(self.api._tools_left(["Bramble", "Core"]), {})             # for these mods only
        by = self.steps(left=left)
        syn = by["tool:Synthesis"]
        self.assertEqual((syn["state"], syn["left"]), ("not needed", True))
        self.assertIn("Left by you", syn["note"])
        self.assertEqual(by["tool:Wrye Bash"]["state"], "to do")
        # Through the steps' own route too, and back.
        got = None
        for _ in range(300):
            got = self.api.post("/api/steps", {"mods": ["Bramble"]})[1]
            if not got["looking"]:
                break
            time.sleep(0.02)
        self.assertIsNone(got["toolcheck"])
        self.api.post("/api/steps/tool/leave", {"mods": ["Bramble"], "tool": "Synthesis", "leave": False})
        self.assertEqual(self.api._tools_left(["Bramble"]), {})
        for body in ({"mods": ["Bramble"], "tool": "", "leave": True}, {"mods": [], "tool": "Synthesis", "leave": True}, {"mods": ["Bramble"], "tool": "Synthesis"}):
            with self.assertRaises(Bad):
                self.api.post("/api/steps/tool/leave", body)


if __name__ == "__main__":
    unittest.main()
