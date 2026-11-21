import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modtrap import api, dryrun, instance, logbook, model
from modtrap.server import Bad
from tests import _fixtures as fx

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


def fake_chain(*steps):
    """The chain the script writes for an element: its steps from the element up to its record."""
    return "\x1e".join("\x1f".join(str(x) for x in st) for st in steps)


def fake_launcher(extra=()):
    def start(cmd, cwd):
        return subprocess.Popen([sys.executable, FAKE, *cmd[1:], *extra], cwd=cwd)
    return start


class DryRunTests(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")
        self.m = model.build(instance.load(self.root))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def snapshot(self):
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in self.root.rglob("*"))

    def test_plan(self):
        p = dryrun.plan(self.m, ["Bramble"])
        self.assertEqual(p.trapped, ["Bramble.esp"])
        self.assertEqual(p.dependants, ["Lantern.esp", "BrambleLanternPatch.esp", "Collection - Bramble.esp",
                                        "Generated.esp"])
        # The dependants and every master under them, in load order, and nothing else.
        self.assertEqual(p.load, ["Skyrim.esm", "Update.esm", "Bramble.esp", "Lantern.esp", "Quill.esp",
                                  "BrambleLanternPatch.esp", "Collection - Bramble.esp", "Generated.esp"])
        self.assertEqual((p.tool, p.profile), ("xEdit", "Default"))

    def test_plan_refusals(self):
        for mods, word in ((["Nobody"], "not a mod"), (["Old Lantern"], "disabled"), (["Tool Output"], "nothing depends"),
                           ([], "tick")):
            with self.subTest(mods=mods):
                with self.assertRaises(dryrun.Refused) as c:
                    dryrun.plan(self.m, mods)
                self.assertIn(word, str(c.exception))

    def test_command_and_job_files(self):
        p = dryrun.plan(self.m, ["Bramble"])
        job_dir = dryrun.new_job_dir()
        manifest = dryrun.prepare(self.m, p, job_dir)
        cmd = dryrun.command(p, job_dir)
        self.assertEqual(cmd[1:6], ["-p", "Default", "run", "-e", "-a"])
        self.assertEqual(cmd[-1], "xEdit")
        for part in ("-sse", '-script:"', '-P:"', "-nobuildrefs", '-B:"', '-R:"'):
            self.assertIn(part, cmd[6])
        # Where MO2 puts the modlist's files: without it xEdit looks the game up in the registry (XE01§11).
        self.assertIn('-D:"%s"' % (self.root / "Game" / "Data"), cmd[6])
        self.assertNotIn("-auto", cmd[6])                           # neither switch does anything with a script
        raw = (job_dir / "script" / "modtrap-job.txt").read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))             # so that xEdit reads it as UTF-8
        job = raw.decode("utf-8-sig")
        self.assertIn("mode=report", job)
        self.assertIn("trap.0=Bramble.esp", job)
        self.assertIn("dep.3=Generated.esp", job)
        # xEdit's plugin list: the game's own plugins are not listed, the rest are starred, in load order.
        self.assertEqual((job_dir / "plugins.txt").read_bytes().decode().split(),
                         ["*Bramble.esp", "*Lantern.esp", "*Quill.esp", "*BrambleLanternPatch.esp",
                          "*Collection", "-", "Bramble.esp", "*Generated.esp"])
        self.assertEqual([f["name"] for f in manifest["dependants"]], p.dependants)
        self.assertEqual((job_dir / "safe" / "Lantern.esp").read_bytes(),
                         (self.root / "mods" / "Lantern" / "Lantern.esp").read_bytes())
        self.assertTrue((job_dir / "script" / "ModTrap.pas").is_file())

    def test_the_executables_own_arguments_are_carried_over(self):
        """MO2's -a replaces an executable's arguments, so what the modlist set for its xEdit must come along:
        its data folder above all. What would put xEdit into another mode, or clash with ModTrap's own, does not."""
        j = Path("C:/Work/job")
        own = '-D:"C:\\Modlists\\Example List\\Stock Game\\Data" -IgnoreESL -quickautoclean -autoexit -P:"other.txt" "Loose.esp" -cp:utf-8'
        got = dryrun.arguments(j, "ModTrap.pas", own, "C:\\Somewhere Else\\Data")
        parts = dryrun.split_arguments(got)
        self.assertEqual(parts[:3], ['-D:"C:\\Modlists\\Example List\\Stock Game\\Data"', "-IgnoreESL", "-cp:utf-8"])
        self.assertEqual([x for x in parts if dryrun.switch_name(x) == "d"], parts[:1])      # theirs, and only theirs
        self.assertEqual(len([x for x in parts if dryrun.switch_name(x) == "p"]), 1)
        for gone in ("quickautoclean", "autoexit", "Loose.esp", "other.txt"):
            self.assertNotIn(gone, got)
        # None of their own: MO2's game folder is named, without a closing slash before the quote.
        got = dryrun.arguments(j, "ModTrap.pas", "", "C:\\Modlists\\Example List\\Stock Game\\Data\\")
        self.assertIn('-D:"C:\\Modlists\\Example List\\Stock Game\\Data" ', got)
        self.assertEqual(dryrun.split_arguments('-x "a b" -D:"c d\\e"  y'), ["-x", '"a b"', '-D:"c d\\e"', "y"])
        self.assertEqual([dryrun.switch_name(x) for x in ("-D:x", "/IgnoreESL", "-cp=1", "plain", "")], ["d", "ignoreesl", "cp", "", ""])

    def test_of_several_entries_for_xedit_the_plain_one_is_taken(self):
        ini = self.root / "ModOrganizer.ini"
        text = ini.read_bytes().decode()
        head = text.split("[customExecutables]")[0]
        exe = (self.root / "tools/SSEEdit/SSEEdit64.exe").as_posix()
        ini.write_bytes((head + "[customExecutables]\r\nsize=3\r\n"
                         "1\\title=xEdit QAC\r\n1\\binary=%s\r\n1\\arguments=-quickautoclean\r\n1\\workingDirectory=\r\n"
                         "2\\title=xEdit64\r\n2\\binary=%s\r\n2\\arguments=-IgnoreESL\r\n2\\workingDirectory=\r\n"
                         "3\\title=xEdit VQSC\r\n3\\binary=%s\r\n3\\arguments=-vqsc\r\n3\\workingDirectory=\r\n" % (exe, exe, exe)).encode())
        p = dryrun.plan(model.build(instance.load(self.root)), ["Bramble"])
        self.assertEqual((p.tool, p.tool_args), ("xEdit64", "-IgnoreESL"))

    def test_xedit_is_closed_after_the_script_and_ended_if_it_stays(self):
        """It stays open after a script (XE01§11): asked to close; ended if it does not go."""
        calls = []
        alive = {"n": 3}

        def running(image):
            alive["n"] -= 1
            return alive["n"] > 0

        dryrun.close_xedit("SSEEdit64.exe", running, lambda image, force: calls.append((image, force)), poll=0.01, grace=5)
        self.assertEqual(calls, [("SSEEdit64.exe", False)])                 # it went when asked
        calls.clear()
        dryrun.close_xedit("SSEEdit64.exe", lambda image: True, lambda image, force: calls.append((image, force)), poll=0.01, grace=0.2)
        self.assertEqual(calls, [("SSEEdit64.exe", False), ("SSEEdit64.exe", True)])
        calls.clear()
        dryrun.close_xedit("SSEEdit64.exe", lambda image: False, lambda image, force: calls.append((image, force)))
        self.assertEqual(calls, [])                                         # already gone
        dryrun.close_xedit("SSEEdit64.exe", lambda image: None, lambda image, force: calls.append((image, force)))
        self.assertEqual(calls, [("SSEEdit64.exe", False)])                 # cannot be watched: asked once

    def test_a_mo2_started_for_the_run_that_stops_at_a_message_is_asked_to_close(self):
        """A plugin of MO2 failing at the end of a command-line run leaves MO2 showing a message (MO01§9)."""
        calls = []
        state = {"xedit": True, "mo2": True}

        def running(image):
            return state["mo2"] if image == dryrun.MO2_EXE else state["xedit"]

        def closer(image, force):
            calls.append((image, force))
            if image == "SSEEdit64.exe":
                state["xedit"] = False

        dryrun.close_xedit("SSEEdit64.exe", running, closer, poll=0.01, mo2_was_running=False, mo2_grace=0.1)
        self.assertEqual(calls, [("SSEEdit64.exe", False), (dryrun.MO2_EXE, False)])       # asked; never ended
        calls.clear()
        state.update(xedit=True, mo2=True)
        dryrun.close_xedit("SSEEdit64.exe", running, closer, poll=0.01, mo2_was_running=True, mo2_grace=0.1)
        self.assertEqual(calls, [("SSEEdit64.exe", False)])                                # the owner's own MO2: left alone
        calls.clear()
        state.update(xedit=True, mo2=False)
        dryrun.close_xedit("SSEEdit64.exe", running, closer, poll=0.01, mo2_was_running=False, mo2_grace=0.1)
        self.assertEqual(calls, [("SSEEdit64.exe", False)])                                # it closed by itself
        # Its message is closed the moment it shows, and MO2 then goes by itself: no need to ask MO2 to close.
        calls.clear()
        state.update(xedit=True, mo2=True)

        def dismiss(image):
            calls.append(("message", image))
            state["mo2"] = False
            return True

        dryrun.close_xedit("SSEEdit64.exe", running, closer, poll=0.01, mo2_was_running=False, mo2_grace=2, dismiss=dismiss)
        self.assertEqual(calls, [("SSEEdit64.exe", False), ("message", dryrun.MO2_EXE)])

    def test_xedit_loading_none_of_the_plugins_is_a_failure_that_says_where_it_looked(self):
        job = self.run_job(tool="absent")
        self.assertEqual(job.state, "failed")
        self.assertIn("did not load", job.message)
        self.assertIn("Elsewhere", job.message)                             # the folder xEdit read
        self.assertIn("Bramble.esp", job.message)

    def run_job(self, extra=(), tool=None):
        p = dryrun.plan(self.m, ["Bramble"])
        if tool:
            p.tool = tool
        job = dryrun.Job(self.m, p, dryrun.new_job_dir(), launcher=fake_launcher(extra), running=lambda image: None,
                         poll=0.05)
        job.start()
        job.join(20)
        return job

    def test_a_run_reads_reports_and_changes_nothing(self):
        before = self.snapshot()
        job = self.run_job()
        self.assertEqual((job.state, job.unchanged), ("done", True), job.message)
        self.assertEqual(before, self.snapshot())                    # nothing in the instance was touched
        r = job.result
        self.assertEqual([f["name"] for f in r["files"]], job.plan.dependants)
        lantern = r["files"][0]
        self.assertEqual((lantern["own"], lantern["entries"], lantern["needs_you"], lantern["reading"]),
                         (1, 1, 1, "needs you"))
        gen = r["files"][3]
        self.assertEqual((gen["own"], gen["entries"], gen["needs_you"], gen["reading"]), (1, 1, 0, "can be demastered"))
        self.assertEqual([i["would"] for i in gen["items"]], ["record", "entry"])
        self.assertTrue((job.dir / "result.json").is_file())
        self.assertIn("xEdit: finished", " ".join(ln["text"] for ln in logbook.lines_after(0)[0]))

    def test_xedit_closing_early_is_a_failure_that_says_so(self):
        p = dryrun.plan(self.m, ["Bramble"])
        p.tool = "crash"
        job = dryrun.Job(self.m, p, dryrun.new_job_dir(), launcher=fake_launcher(), running=lambda image: False,
                         poll=0.05)
        orig, grace = dryrun.time.time, dryrun.GONE_GRACE
        try:
            dryrun.time.time = lambda: orig() + 60                   # past the grace for a slow start
            dryrun.GONE_GRACE = 0.2
            job.start()
            job.join(30)
        finally:
            dryrun.time.time, dryrun.GONE_GRACE = orig, grace
        self.assertEqual(job.state, "failed")
        self.assertIn("closed before the script finished", job.message)
        self.assertIn("xEdit left no log of its own", " ".join(ln["text"] for ln in logbook.lines_after(0)[0]))

    def test_a_changed_dependant_is_caught(self):
        job = self.run_job(extra=[str(self.root / "mods" / "Lantern" / "Lantern.esp")], tool="touch")
        self.assertEqual((job.state, job.unchanged), ("failed", False))
        self.assertIn("Lantern.esp", job.message)
        self.assertIn("safe folder", job.message)

    def test_through_the_api(self):
        a = api.Api()
        a.launcher, a.running, a.poll = fake_launcher(), (lambda image: None), 0.05
        a.open(str(self.root), wait=True)
        plan = a.dry_plan({"mods": ["Bramble"]})
        self.assertEqual((plan["load"], plan["tool_file"]), (8, "SSEEdit64.exe"))
        with self.assertRaises(Bad):
            a.dry_plan({"mods": ["Tool Output"]})
        a.dry_start({"mods": ["Bramble"]})
        a.job.join(20)
        state = a.job_state()["job"]
        self.assertEqual(state["state"], "done", state["message"])
        json.dumps(state)                                             # the page gets it as JSON
        text = " ".join(ln["text"] for ln in logbook.lines_after(0)[0])
        self.assertIn("-script:'<job>", text)
        self.assertNotIn(self.tmp.name, text)                         # every path in the log is masked


class ReportTests(unittest.TestCase):
    def test_reading_of_a_file(self):
        ch = lambda *steps: "\x1e".join("\x1f".join(str(x) for x in st) for st in steps)   # noqa: E731
        alias = ch(("ALFR - Forced Reference", "etSubRecord", "dtFormID", 0, 3), ("Alias", "etSubRecordStruct", "dtStruct", 6, 1),
                   ("Aliases", "etSubRecordArray", "dtSubRecordArray", 3, 12))
        text = "\r\n".join([
            "H\tmodtrap-report/2\treport\t1", "F\tPatch.esp\t2\tSkyrim.esm,Bad.esp",
            "R\tPatch.esp\tMISC\t05000801\tBad.esp\t1\tA", "R\tPatch.esp\tMISC\t05000802\tBad.esp\t1\tB",
            "D\tPatch.esp\t2\t2", "F\tOther.esp\t9\tSkyrim.esm,Bad.esp",
            "R\tOther.esp\tQUST\t00011111\tSkyrim.esm\t0\tQ",
            "E\tOther.esp\t00011111\tQUST \\ Aliases \\ Alias \\ ALFR\tBad.esp\t05000801\t" + alias,
            "D\tOther.esp\t9\t1", "U\tOther.esp", "X\tok\t"])
        r = dryrun.parse_report(text)
        self.assertEqual([(f["name"], f["reading"]) for f in r["files"]],
                         [("Patch.esp", "patch only"), ("Other.esp", "needs you")])   # an alias list is not a safe list
        self.assertEqual((r["end"], r["held_changed"]), ("ok", ["Other.esp"]))
        e = r["files"][1]["items"][0]["elements"][0]
        self.assertEqual((e["kind"], e["entry"], e["array"], e["array_length"]), ("entry", "Alias", "Aliases", 3))

    def test_a_patch_named_for_the_mod_is_switched_off_whatever_it_holds(self):
        # Invented names. A patch says in its name what it is for: the mod's or the plugin's whole name, or their
        # initials as a word of its own (WHY§52).
        for name in ("Inn - Thorn Hedge Addon Patch.esp", "ThornHedgeAddon - Inn.esp", "THA_Inn.esp",
                     "Inn - THA patch.esp", "Inns Wear Hats - THA Patch.esp"):
            self.assertTrue(dryrun.named_for(name, ["ThornHedgeAddon.esp"], ["Thorn Hedge Add-On"]), name)
        for name in ("Big Patch - Gameplay.esp", "Thatch.esp", "Hedge Inn.esp", "PG_1.esp"):
            self.assertFalse(dryrun.named_for(name, ["ThornHedgeAddon.esp"], ["Thorn Hedge Add-On"]), name)
        self.assertFalse(dryrun.named_for("A - B.esp", ["B.esp"], ["B"]))          # too short a name to go by

        def report(name, masters):
            return "\r\n".join(["H\tmodtrap-report/3\treport\t1", "F\t%s\t9\t%s" % (name, ",".join(masters)),
                                 "R\t%s\tNPC_\t00054321\tSkyrim.esm\t0\tInventedPerson" % name,
                                 "E\t%s\t00054321\tNPC_ \\ RNAM - Race\tThornHedgeAddon.esp\t05000802\t%s" % (
                                     name, fake_chain(("RNAM - Race", "etSubRecord", "dtFormID", 0, 9))),
                                 "D\t%s\t9\t1" % name, "X\tok\t"])

        def read(name, masters):
            return dryrun.parse_report(report(name, masters), ["ThornHedgeAddon.esp"], ["Thorn Hedge Add-On"],
                                       ["Skyrim.esm", "Update.esm"])["files"][0]

        few = ["Skyrim.esm", "Update.esm", "Inn.esp", "ThornHedgeAddon.esp"]
        f = read("Inn - THA Patch.esp", few)
        self.assertEqual((f["reading"], f["why"], f["made_for"]), ("patch only", "named for the mod", True))
        # The same name on a plugin with many masters is one of the list's big patches: it is not switched off.
        f = read("Everything - THA Merge.esp", few + ["One.esp", "Two.esp", "Three.esp"])
        self.assertEqual((f["reading"], f["made_for"]), ("needs you", False))
        # And few masters without the name is a plugin that must go on working.
        self.assertEqual(read("Inn Overhaul.esp", few)["reading"], "needs you")
        # Without the trapped names (an old report read again) nothing is guessed.
        self.assertEqual(dryrun.parse_report(report("Inn - THA Patch.esp", few))["files"][0]["reading"], "needs you")

    def test_where_a_part_that_needs_the_owner_came_from(self):
        head = ["H\tmodtrap-report/3\treport\t1", "F\tBig Patch.esp\t9\tSkyrim.esm,Fixes.esp,Bad.esp,Other.esp"]
        rec = lambda form: "R\tBig Patch.esp\tINFO\t%s\tSkyrim.esm\t0\t" % form        # noqa: E731
        el = lambda form: "E\tBig Patch.esp\t%s\tINFO \\ Conditions \\ Condition \\ CTDA \\ Parameter #1\tBad.esp\t05000802\t%s" % (   # noqa: E731
            form, fake_chain(("Parameter #1", "etValue", "dtInteger", 0, 3), ("CTDA", "etSubRecord", "dtStruct", 9, 0),
                             ("Condition", "etSubRecordStruct", "dtStruct", 1, 2), ("Conditions", "etSubRecordArray", "dtSubRecordArray", 3, 4)))
        part = lambda form, same, prev, state, rest: "C\tBig Patch.esp\t%s\tConditions\tetSubRecordArray\t%s\t%s\t%s\t1\t%s" % (   # noqa: E731
            form, same, prev, state, rest)
        lines = head + [
            rec("00000A01"), el("00000A01"), part("00000A01", "Bad.esp", "Fixes.esp", "present", "0"),    # carried on
            rec("00000A02"), el("00000A02"), part("00000A02", "", "Fixes.esp", "present", "1"),           # added on top
            rec("00000A03"), el("00000A03"), part("00000A03", "", "Fixes.esp", "present", "0"),           # its own doing
            rec("00000A04"), el("00000A04"), part("00000A04", "Bad.esp", "", "", "0"),                    # nothing to go back to
            rec("00000A05"), el("00000A05"), part("00000A05", "Bad.esp", "Fixes.esp", "needs Elsewhere.esp", "0"),
            rec("00000A06"), el("00000A06"), part("00000A06", "Fixes.esp", "Skyrim.esm", "absent", "0"),  # same as a plugin that stays
            rec("00000A07"), el("00000A07"),                                                              # an older script: no C line
            "D\tBig Patch.esp\t9\t7", "X\tok\t"]
        f = dryrun.parse_report("\r\n".join(lines), ["Bad.esp"], ["Bad"], ["Skyrim.esm"])["files"][0]
        came = {it["form"]: (it["elements"][0]["came"], it["carried"]) for it in f["items"]}
        self.assertEqual(came, {"00000A01": ("carried", True), "00000A02": ("added", True), "00000A03": ("", False),
                                "00000A04": ("", False), "00000A05": ("", False), "00000A06": ("", False),
                                "00000A07": ("", False)})
        self.assertEqual((f["reading"], f["needs_you"], f["carried"]), ("needs you", 7, 2))   # reported, not yet acted on
        e = f["items"][0]["elements"][0]
        self.assertEqual((e["part"], e["same_as"], e["without"], e["without_state"]), ("Conditions", "Bad.esp", "Fixes.esp", "present"))

    def test_chains(self):
        ch = lambda *steps: "\x1e".join("\x1f".join(str(x) for x in st) for st in steps)   # noqa: E731
        # A keyword: the list is the value of one field (the field holds an array).
        kw = dryrun.read_chain(ch(("Keyword", "etValue", "dtFormID", 0, 2), ("KWDA - Keywords", "etSubRecord", "dtArray", 5, 4)))
        self.assertEqual((kw["kind"], kw["entry"], kw["array"], kw["array_length"]), ("entry", "Keyword", "KWDA - Keywords", 5))
        self.assertTrue(dryrun._safe_array("ARMO", kw["array"]))
        # A form list entry: the list is an element of its own.
        fl = dryrun.read_chain(ch(("LNAM - FormID", "etSubRecord", "dtFormID", 0, 0), ("FormIDs", "etSubRecordArray", "dtSubRecordArray", 9, 1)))
        self.assertEqual((fl["kind"], fl["array"]), ("entry", "FormIDs"))
        self.assertTrue(dryrun._safe_array("FLST", "FormIDs"))
        self.assertFalse(dryrun._safe_array("QUST", "FormIDs"))
        # A single field, with no list between it and its record.
        one = dryrun.read_chain(ch(("RNAM - Race", "etSubRecord", "dtFormID", 0, 9)))
        self.assertEqual(one["kind"], "field")
        self.assertEqual(dryrun.read_chain("")["kind"], "field")


if __name__ == "__main__":
    unittest.main()
