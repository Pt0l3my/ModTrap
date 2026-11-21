"""The demaster, end to end, against the stand-in for xEdit (WHY§39). It is switched off in ModTrap itself: these
tests are the only thing that calls it."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modtrap import api, demaster, dryrun, history, instance, logbook, model, safe
from tests import _fixtures as fx

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


class DemasterTests(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")
        self.session = Path(self.tmp.name) / "home" / "sessions" / "s1"
        self.m = model.build(instance.load(self.root))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def launcher(self, cmd, cwd):
        return subprocess.Popen([sys.executable, FAKE, *cmd[1:], "--mods", str(self.root / "mods")], cwd=cwd)

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in sorted(self.root.rglob("*")) if p.is_file()}

    def dry(self, tool="clean"):
        p = dryrun.plan(self.m, ["Bramble"])
        p.tool = tool
        job = dryrun.Job(self.m, p, dryrun.new_job_dir(self.session / "jobs"), launcher=self.launcher,
                         running=lambda image: None, poll=0.05)
        job.start()
        job.join(20)
        self.assertEqual(job.state, "done", job.message)
        return p, job.public()

    def job(self, tool="clean", closed=True):
        dp, dry = self.dry(tool if tool in ("clean", "xEdit") else "clean")
        dp.tool = tool
        pl = demaster.plan(self.m, dry)
        d = demaster.Demaster(self.m, dp, pl, dryrun.new_job_dir(self.session / "jobs"), self.session,
                              launcher=self.launcher, running=lambda image: None, closed=lambda: closed, poll=0.05)
        return d

    def test_plan_from_a_dry_run(self):
        _, dry = self.dry("clean")
        pl = demaster.plan(self.m, dry)
        # A patch named for the mod is switched off whether or not anything of it would remain (WHY§52): the one
        # in a collection is deactivated alone; the mod that is nothing but such a patch is disabled whole.
        self.assertEqual(sorted(pl.demaster), ["Generated.esp", "Lantern.esp"])
        self.assertEqual(pl.switch_off, ["BrambleLanternPatch.esp", "Collection - Bramble.esp"])
        self.assertEqual(pl.disable_mods, ["Bramble - Lantern Patch"])
        self.assertEqual((pl.needs_you, pl.blocked), ([], False))
        # An entry is reached by its route and named; the record of the trapped plugin's own comes last.
        self.assertEqual(pl.demaster["Lantern.esp"], ["00012345|E|1/2|LNAM - FormID", "05000801|R"])
        self.assertEqual(pl.mod_name, "ModTrap - Bramble")
        _, dry = self.dry("xEdit")                                  # here two dependants need the owner
        pl = demaster.plan(self.m, dry)
        self.assertEqual((sorted(pl.needs_you), pl.blocked), (["Lantern.esp"], True))

    def test_entries_of_one_list_go_highest_first(self):
        el = lambda route: {"route": route, "entry": "LNAM - FormID"}   # noqa: E731
        f = {"items": [{"form": "0001", "would": "entry", "elements": [el([1, 0]), el([1, 3]), el([1, 2])]},
                       {"form": "0002", "would": "record", "elements": []}]}
        self.assertEqual(demaster.actions_for(f), ["0001|E|1/3|LNAM - FormID", "0001|E|1/2|LNAM - FormID",
                                                   "0001|E|1/0|LNAM - FormID", "0002|R"])
        with self.assertRaises(demaster.Refused):
            demaster.actions_for({"items": [{"form": "1", "would": "needs you", "elements": []}]})

    def test_the_whole_demaster_and_back(self):
        before = self.tree()
        d = self.job()
        d.make_safe()
        d.run_xedit()
        self.assertEqual(sorted(d.verify()), ["Generated.esp", "Lantern.esp"])
        self.assertEqual(self.tree(), before)                       # up to here nothing in the modlist has changed
        done = d.install()
        self.assertEqual((done["disabled"], done["deactivated"]),
                         (["Bramble - Lantern Patch", "Bramble"], ["BrambleLanternPatch.esp", "Collection - Bramble.esp"]))
        check = d.check()
        self.assertEqual((check["ok"], check["new_problems"], check["needs_you"]), (True, [], []))
        # The modlist as MO2 will see it: ModTrap's mod on top provides the demastered plugins, Bramble is off.
        m = model.build(instance.load(self.root))
        self.assertEqual(m.issues, [])
        self.assertFalse(m.instance.mod("Bramble").enabled)
        top = max((x for x in m.instance.mods if x.kind == "mod"), key=lambda x: x.priority)
        self.assertEqual(top.name, "ModTrap - Bramble")
        lantern = m.row("Lantern.esp")
        self.assertEqual((lantern.source, lantern.also_in, lantern.masters, lantern.position),
                         ("ModTrap - Bramble", ("Lantern",), ("Skyrim.esm",), 6))
        self.assertFalse(m.row("BrambleLanternPatch.esp").active)
        # The originals are still what they were.
        self.assertEqual((self.root / "mods" / "Lantern" / "Lantern.esp").read_bytes(), before["mods/Lantern/Lantern.esp"])
        # The history says what was done and where things were.
        events = history.History(self.session).all()
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds.count("plugin demastered"), 2)
        self.assertEqual([k for k in kinds if k != "plugin demastered"],
                         ["mod added", "plugin deactivated", "plugin deactivated", "mod disabled", "mod disabled",
                          "verified"])
        patches = next(e for e in events if e["kind"] == "mod disabled")
        self.assertEqual((patches["mod"], patches["why"]), ("Bramble - Lantern Patch", "patches made only for the mod"))
        off = next(e for e in events if e["kind"] == "mod disabled" and e["mod"] == "Bramble")
        self.assertEqual((off["mod"], off["priority"], off["plugins"]),
                         ("Bramble", 1, [{"name": "Bramble.esp", "position": 5, "kind": "esp"}]))
        dem = next(e for e in events if e["kind"] == "plugin demastered" and e["plugin"] == "Lantern.esp")
        self.assertEqual((dem["masters_before"], dem["masters_after"]), (["Skyrim.esm", "Bramble.esp"], ["Skyrim.esm"]))
        # Revert: the modlist is, byte for byte and file for file, what it was.
        d.revert()
        self.assertEqual(self.tree(), before)
        self.assertEqual(history.History(self.session).all()[-1]["kind"], "reverted")

    def test_mo2_open_refuses_before_anything_is_written(self):
        before = self.tree()
        d = self.job(closed=False)
        d.make_safe()
        d.run_xedit()
        d.verify()
        with self.assertRaises(demaster.Refused) as c:
            d.install()
        self.assertIn("MO2 must be closed", str(c.exception))
        self.assertEqual(self.tree(), before)
        d2 = self.job(closed=None)                                  # cannot be told: the same as open
        d2.make_safe(); d2.run_xedit(); d2.verify()                 # noqa: E702
        with self.assertRaises(demaster.Refused):
            d2.install()

    def test_a_new_plugin_that_still_lists_the_mod_is_not_installed(self):
        d = self.job("keepmaster")
        d.make_safe()
        d.run_xedit()
        self.assertEqual(d.verify(), [])
        self.assertEqual(sorted(d.plan.needs_you), ["Generated.esp", "Lantern.esp"])
        done = d.install()                                          # only the patch is switched off
        self.assertEqual((done["plugins"], done["disabled"], done["deactivated"]),
                         ([], ["Bramble - Lantern Patch"], ["BrambleLanternPatch.esp", "Collection - Bramble.esp"]))
        self.assertFalse((self.root / "mods" / "ModTrap - Bramble").exists())
        self.assertTrue(model.build(instance.load(self.root)).instance.mod("Bramble").enabled)   # the mod stays on
        self.assertFalse(d.check()["disabled"])

    def test_a_refused_action_keeps_that_dependant_out(self):
        d = self.job("refuse")
        d.make_safe()
        d.run_xedit()
        good = d.verify()
        self.assertEqual(len(good), 1)
        self.assertEqual(len(d.plan.needs_you), 1)
        self.assertIn("refused", " ".join(d.plan.notes))
        d.install()
        self.assertTrue(model.build(instance.load(self.root)).instance.mod("Bramble").enabled)

    def test_an_original_changed_by_the_run_stops_everything(self):
        d = self.job("touch")
        d.make_safe()
        d.run_xedit()
        with self.assertRaises(demaster.Refused) as c:
            d.verify()
        self.assertIn("safe folder", str(c.exception))
        with self.assertRaises(demaster.Refused):
            d.install()
        self.assertTrue(d.safe.check()["foreign"])                  # and the safe folder can still put them back

    def test_a_failed_install_puts_everything_back(self):
        before = self.tree()
        d = self.job()
        d.make_safe(); d.run_xedit(); d.verify()                    # noqa: E702
        d.plan.trapped_mods.append("A Mod That Is Not There")       # the last write of the install will be refused
        with self.assertRaises(demaster.Refused) as c:
            d.install()
        self.assertIn("everything was put back", str(c.exception))
        self.assertEqual(self.tree(), before)

    def test_order_is_enforced_and_names_never_clash(self):
        d = self.job()
        with self.assertRaises(demaster.Refused):
            d.prepare()
        d.make_safe(); d.run_xedit()                                # noqa: E702
        with self.assertRaises(demaster.Refused):
            d.install()
        d.verify()
        (self.root / "mods" / "ModTrap - Bramble").mkdir()
        with self.assertRaises(demaster.Refused) as c:
            d.install()
        self.assertIn("already exists", str(c.exception))

    def test_the_page_cannot_reach_it(self):
        import inspect
        named = " ".join(ln for ln in inspect.getsource(api).splitlines() if ln.startswith(("from ", "import "))).replace(",", " ").split()
        self.assertNotIn("demaster", named)
        self.assertTrue(safe.Safe)


if __name__ == "__main__":
    unittest.main()
