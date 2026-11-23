"""Carrying out the adding of mods (DESIGN§16.8), on an invented modlist. Switched off: nothing the page calls
reaches it."""

from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path

from modtrap import adding, addjob, api, history, instance, logbook, model, plugin, profile

from ._fixtures import make_instance, write
from .test_adding import SKY, invented

b = plugin.build


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class PlacingInTheLists(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = invented(Path(self.tmp.name))
        self.pdir = self.root / "profiles" / "Default"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def mods(self) -> list[str]:
        return [ln for ln in (self.pdir / "modlist.txt").read_bytes().decode().split("\r\n") if ln and ln[0] != "#"]

    def test_a_listed_mod_is_moved_and_enabled(self) -> None:
        before = self.mods()
        ch = profile.place_mod(self.pdir, "Thistle", "Outputs_separator")
        now = self.mods()
        self.assertEqual(now[:3], ["+Tool Output", "+Outputs_separator", "+Thistle"])     # the file is highest first
        self.assertEqual(sorted(x[1:] for x in now), sorted(x[1:] for x in before))       # nobody else moved or changed
        self.assertEqual([x for x in now if x[1:] != "Thistle"], [x for x in before if x[1:] != "Thistle"])
        self.assertEqual((ch.lines[0]["from"], ch.lines[0]["to"]), ("-", "+"))

    def test_a_new_mod_is_added_at_its_place_or_on_top(self) -> None:
        profile.place_mod(self.pdir, "Heather", "Quill")
        now = self.mods()
        self.assertEqual(now[now.index("+Quill") + 1], "+Heather")
        ch = profile.place_mod(self.pdir, "Top Mod", "")
        self.assertEqual(self.mods()[0], "+Top Mod")
        self.assertEqual(ch.lines[0]["priority"], len(self.mods()) - 1)

    def test_what_cannot_be_placed_is_refused_and_nothing_is_written(self) -> None:
        old = (self.pdir / "modlist.txt").read_bytes()
        for name, before in (("Thistle", "Nobody"), ("Thistle", "Thistle"), ("+Bad", ""), ("Two\nLines", "")):
            with self.assertRaises(profile.Refused):
                profile.place_mod(self.pdir, name, before)
        self.assertEqual((self.pdir / "modlist.txt").read_bytes(), old)

    def test_plugins_go_into_both_lists_in_agreement(self) -> None:
        changes = profile.place_plugins(self.pdir, [("Dormant.esp", "Generated.esp"), ("Thistle.esp", "Generated.esp"),
                                                    ("Beacon.esm", "Quill.esp")])
        lo = [x for x in (self.pdir / "loadorder.txt").read_bytes().decode().split("\r\n") if x and x[0] != "#"]
        pl = [x for x in (self.pdir / "plugins.txt").read_bytes().decode().split("\r\n") if x and x[0] != "#"]
        self.assertEqual(lo[5:], ["Lantern.esm", "Beacon.esm", "Quill.esp", "Dormant.esp", "Thistle.esp", "Generated.esp"])
        self.assertEqual(pl, ["*Lantern.esm", "*Beacon.esm", "*Quill.esp", "*Dormant.esp", "*Thistle.esp", "*Generated.esp"])
        self.assertEqual([c.file for c in changes], ["loadorder.txt", "plugins.txt"])
        self.assertEqual(changes[0].lines[0]["position"], 8)
        inst = instance.load(self.root)
        self.assertEqual([n for n, a in inst.load_order if a][5:], lo[5:])

    def test_a_plugin_goes_last_when_no_place_is_named_and_a_listed_one_is_moved(self) -> None:
        profile.place_plugins(self.pdir, [("Thistle.esp", "")])
        profile.place_plugins(self.pdir, [("Quill.esp", "")])
        pl = [x for x in (self.pdir / "plugins.txt").read_bytes().decode().split("\r\n") if x and x[0] != "#"]
        self.assertEqual(pl, ["*Lantern.esm", "*Generated.esp", "*Thistle.esp", "*Quill.esp"])
        with self.assertRaises(profile.Refused):
            profile.place_plugins(self.pdir, [("Thistle.esp", "Nowhere.esp")])


class Adding(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = invented(Path(self.tmp.name) / "list")
        self.work = Path(self.tmp.name) / "session"
        self.heather = Path(self.tmp.name) / "unpacked" / "Heather"
        write(self.heather / "Heather.esp", b((SKY, "Quill.esp")))
        write(self.heather / "textures" / "shared" / "a.dds", b"newer")
        self.closed: bool | None = True
        self.before = snapshot(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()
        logbook.set_console(True)

    def job(self, names: list[str], staged: bool = True) -> addjob.AddJob:
        inst = instance.load(self.root)
        m = model.build(inst)
        extra = [adding.staged_mod("Heather", self.heather)] if staged else []
        rep = adding.analyse(m, names, staged=extra)
        p = addjob.plan(m, rep, {"Heather": {"root": str(self.heather), "archive": "Heather-1-0.zip"}})
        return addjob.AddJob(inst, m, p, self.work / "jobs" / "add-1", self.work, lambda: self.closed)

    def test_an_unpacked_mod_and_an_installed_one_are_added_in_place(self) -> None:
        j = self.job(["Thistle"])
        done = j.run()
        inst = instance.load(self.root)
        m = model.build(inst)
        order = [x.name for x in inst.mods if x.kind in ("mod", "separator")]
        self.assertEqual(order[-4:], ["Thistle", "Heather", "Outputs_separator", "Tool Output"])
        self.assertTrue(inst.mod("Thistle").enabled and inst.mod("Heather").enabled)
        active = [n for n, a in inst.load_order if a]
        self.assertEqual(active[-4:], ["Quill.esp", "Heather.esp", "Thistle.esp", "Generated.esp"])
        self.assertEqual(m.issues, [])
        self.assertEqual(m.row("Heather.esp").source, "Heather")
        self.assertIn(b"installationFile=Heather-1-0.zip", (self.root / "mods" / "Heather" / "meta.ini").read_bytes())
        self.assertEqual((self.root / "mods" / "Heather" / "textures" / "shared" / "a.dds").read_bytes(), b"newer")
        self.assertEqual([x["name"] for x in done["mods"]], ["Thistle", "Heather"])
        kinds = [e["kind"] for e in history.History(self.work).all()]
        self.assertEqual(kinds, ["mod enabled", "mod added", "plugin activated", "plugin activated", "verified"])
        events = history.History(self.work).all()
        self.assertEqual(events[1]["archive"], "Heather-1-0.zip")
        self.assertIsInstance(events[2]["position"], int)

    def newer(self, files: dict) -> addjob.AddJob:
        """A newer version of Quill, unpacked: planned as an update of it (MT40)."""
        root = Path(self.tmp.name) / "unpacked" / "Quill (1.4)"
        for rel, data in files.items():
            write(root / rel, data)
        inst = instance.load(self.root)
        m = model.build(inst)
        rep = adding.analyse(m, [], staged=[adding.staged_mod("Quill (1.4)", root)], updates={"Quill (1.4)": "Quill"})
        p = addjob.plan(m, rep, {"Quill (1.4)": {"root": str(root), "archive": "Quill-4321-1-4.7z",
                                                 "meta": {"game": "SkyrimSE", "mod_id": 4321, "file_id": 113, "version": "1.4"}}})
        return addjob.AddJob(inst, m, p, self.work / "jobs" / "add-2", self.work, lambda: self.closed)

    def test_a_newer_version_goes_right_above_the_old_one_which_is_disabled(self) -> None:
        j = self.newer({"Quill.esp": b((SKY,)), "textures/quill/only.dds": b"newer"})
        self.assertEqual([(x["name"], x["updates"], x["replaces"]) for x in j.plan.mods], [("Quill (1.4)", "Quill", "Quill")])
        order_before = [n for n, _a in instance.load(self.root).load_order]
        done = j.run()
        inst = instance.load(self.root)
        m = model.build(inst)
        old, new = inst.mod("Quill"), inst.mod("Quill (1.4)")
        self.assertEqual((old.enabled, new.enabled, new.priority), (False, True, old.priority + 1))
        self.assertTrue((self.root / "mods" / "Quill" / "Quill.esp").is_file())            # the old version is only disabled
        self.assertEqual([n for n, _a in inst.load_order], order_before)                   # the plugin keeps its place
        self.assertEqual(m.row("Quill.esp").source, "Quill (1.4)")
        self.assertEqual(m.issues, [])
        self.assertEqual(done["mods"][0]["replaces"], "Quill")
        # The new mod's own record names its source, so that it can be asked about for updates like the old one.
        record = (self.root / "mods" / "Quill (1.4)" / "meta.ini").read_bytes()
        for line in (b"installationFile=Quill-4321-1-4.7z", b"gameName=SkyrimSE", b"modid=4321", b"1\\fileid=113"):
            self.assertIn(line, record)
        kinds = [(e["kind"], e.get("mod")) for e in history.History(self.work).all()]
        self.assertEqual(kinds[:2], [("mod added", "Quill (1.4)"), ("mod disabled", "Quill")])
        # Revert: file for file as before, the old version enabled again, the new one gone.
        self.assertEqual(j.revert(), {"left": [], "how": "whole"})
        self.assertEqual(snapshot(self.root), self.before)
        self.assertIn(("mod enabled", "Quill"), [(e["kind"], e.get("mod")) for e in history.History(self.work).all()])

    def test_an_update_has_its_own_few_steps_and_is_not_judged_as_a_new_mod(self) -> None:
        """MT49: a newer version takes the older one's place; the place among all mods, the shared files, the
        records, the tools and a look in the game are a new mod's steps, not an update's. Before the add, after
        it, and when the add's own record is all that says the mod is an update."""
        root = Path(self.tmp.name) / "unpacked" / "Quill (1.4)"
        old_files = {p.relative_to(self.root / "mods" / "Quill").as_posix(): p.read_bytes()
                     for p in (self.root / "mods" / "Quill").rglob("*") if p.is_file() and p.name != "meta.ini"}
        self.assertIn("Quill.esp", old_files)
        j = self.newer({**old_files, "Quill.esp": old_files["Quill.esp"] + b"\0" * 8, "meshes/quill/added.nif": b"new", "textures/quill/only.dds": b"newer"})
        inst = instance.load(self.root)
        m = model.build(inst)
        rep = adding.analyse(m, [], staged=[adding.staged_mod("Quill (1.4)", root)], updates={"Quill (1.4)": "Quill"})
        self.assertTrue(rep["update"])
        self.assertEqual([st["key"] for st in rep["steps"]], ["install", "needs", "update", "differs", "health"])
        self.assertEqual([st["n"] for st in rep["steps"]], [1, 2, 3, 4, 5])
        self.assertFalse(any(st["manual"] for st in rep["steps"]))                       # nothing to tick off by hand
        update = rep["steps"][2]
        self.assertEqual(update["state"], "waiting")
        self.assertIn("Quill (1.4): to enable, right after “Quill”", [i["text"] for i in update["items"]])
        self.assertIn("“Quill”, the older version: to disable; it is not deleted", [i["text"] for i in update["items"]])
        d = rep["mods"][0]["differs"]
        self.assertEqual((d["added"], d["gone"], d["changed"], d["plugins"]["changed"]), (1, 0, 2, ["Quill.esp"]))
        self.assertEqual(d["same"], len(old_files) - 2)
        self.assertIn("1 file(s) are new, 0 are gone, 2 have another size", rep["steps"][3]["items"][0]["text"])
        # After the add: the same few steps, all done; nothing is left "to go".
        j.run()
        m = model.build(instance.load(self.root))
        rep = adding.analyse(m, ["Quill (1.4)"], updates={"Quill (1.4)": "Quill"})
        self.assertEqual([(st["key"], st["state"]) for st in rep["steps"]], [("needs", "done"), ("update", "done"), ("differs", "done"), ("health", "done")])
        self.assertEqual((rep["complete"], rep["summary"]), (True, "The newer version is in place and the older one disabled."))
        texts = [i["text"] for i in rep["steps"][1]["items"]]
        self.assertIn("“Quill”, the older version: disabled, and kept as it is", texts)
        self.assertTrue(any(t.startswith("Quill.esp: active, at position") for t in texts), texts)
        # Without the word that it is an update, the same mod is judged as a new one is.
        rep = adding.analyse(m, ["Quill (1.4)"])
        self.assertFalse(rep["update"])
        self.assertIn("play", [st["key"] for st in rep["steps"]])
        # The add's own record says which mod it was a newer version of.
        self.assertEqual(addjob.AddJob.summary(self.work / "jobs" / "add-2")["updates"], {"Quill (1.4)": "Quill"})

    def test_a_newer_version_that_lacks_a_plugin_others_need_is_put_back(self) -> None:
        """The newer file no longer brings Quill.esp, which a plugin of the modlist needs: the check after the add
        finds the missing master, and everything is as it was."""
        j = self.newer({"QuillRenamed.esp": b((SKY,)), "textures/quill/only.dds": b"newer"})
        with self.assertRaisesRegex(addjob.Refused, "put back"):
            j.run()
        self.assertEqual(snapshot(self.root), self.before)
        self.assertTrue(instance.load(self.root).mod("Quill").enabled)

    def test_a_newer_version_is_undone_by_line_when_the_lists_changed_since(self) -> None:
        j = self.newer({"Quill.esp": b((SKY,))})
        j.run()
        lo = self.root / "profiles" / "Default" / "loadorder.txt"
        lo.write_bytes(lo.read_bytes() + b"# touched by something else\r\n")              # as MO2 does when it runs
        self.assertEqual(j.revert()["how"], "by line")
        inst = instance.load(self.root)
        self.assertTrue(inst.mod("Quill").enabled)
        self.assertIsNone(inst.mod("Quill (1.4)"))
        self.assertEqual(model.build(inst).issues, [])

    def test_revert_puts_the_modlist_back_file_for_file(self) -> None:
        j = self.job(["Thistle"])
        j.run()
        self.assertNotEqual(snapshot(self.root), self.before)
        self.assertEqual(j.revert(), {"left": [], "how": "whole"})
        self.assertEqual(snapshot(self.root), self.before)
        self.assertFalse((self.root / "mods" / "Heather").exists())
        self.assertTrue(self.heather.is_dir())                      # ModTrap's unpacked copy is still there

    def test_a_copy_changed_since_is_left_and_said(self) -> None:
        j = self.job([])
        j.run()
        write(self.root / "mods" / "Heather" / "notes of mine.txt", b"kept")
        self.assertEqual(j.revert(), {"left": ["Heather"], "how": "whole"})
        self.assertTrue((self.root / "mods" / "Heather" / "notes of mine.txt").is_file())
        for n in addjob.LISTS:
            self.assertEqual((self.root / "profiles" / "Default" / n).read_bytes(), self.before["profiles/Default/" + n])

    def test_mo2_open_or_not_known_to_be_closed_refuses_before_anything(self) -> None:
        for state in (False, None):
            self.closed = state
            with self.assertRaises(addjob.Refused):
                self.job(["Thistle"]).run()
            self.assertEqual(snapshot(self.root), self.before)

    def test_a_list_changed_since_the_plan_refuses(self) -> None:
        j = self.job(["Thistle"])
        p = self.root / "profiles" / "Default" / "modlist.txt"
        p.write_bytes(p.read_bytes() + b"-Someone Else\r\n")
        with self.assertRaises(addjob.Refused):
            j.run()
        self.assertFalse((self.root / "mods" / "Heather").exists())

    def test_what_a_mod_needs_must_be_there_first(self) -> None:
        with self.assertRaises(addjob.Refused) as c:
            self.job(["Needs Absent"], staged=False)
        self.assertIn("Nowhere.esp", str(c.exception))

    def test_a_mod_of_that_name_is_never_overwritten(self) -> None:
        j = self.job([])
        write(self.root / "mods" / "Heather" / "theirs.txt", b"someone else's")
        with self.assertRaises(addjob.Refused):
            j.run()
        self.assertEqual((self.root / "mods" / "Heather" / "theirs.txt").read_bytes(), b"someone else's")
        for n in addjob.LISTS:
            self.assertEqual((self.root / "profiles" / "Default" / n).read_bytes(), self.before["profiles/Default/" + n])

    def test_a_failure_part_way_puts_everything_back(self) -> None:
        j = self.job(["Thistle"])
        real = profile.place_plugins

        def fail(*a, **k):
            raise profile.Refused("the list could not be written (invented)")
        profile.place_plugins = fail
        try:
            with self.assertRaises(addjob.Refused) as c:
                j.run()
        finally:
            profile.place_plugins = real
        self.assertIn("everything was put back", str(c.exception))
        self.assertEqual(snapshot(self.root), self.before)
        self.assertEqual(history.History(self.work).all()[-1]["kind"], "reverted")

    def test_a_mod_with_no_output_in_the_list_goes_last(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_instance(Path(d) / "l", [("-", "Thistle", {"Thistle.esp": b((SKY,))}),
                                                 ("+", "Quill", {"Quill.esp": b((SKY,))})], load_order=["Quill.esp"])
            inst = instance.load(root)
            m = model.build(inst)
            p = addjob.plan(m, adding.analyse(m, ["Thistle"]))
            addjob.AddJob(inst, m, p, Path(d) / "w" / "j", Path(d) / "w", lambda: True).run()
            inst = instance.load(root)
            self.assertEqual([x.name for x in inst.mods if x.kind == "mod"], ["Quill", "Thistle"])
            self.assertEqual([n for n, a in inst.load_order if a][-2:], ["Quill.esp", "Thistle.esp"])


class SwitchedOff(unittest.TestCase):
    def test_nothing_the_page_calls_reaches_it(self) -> None:
        imports = [ln for ln in inspect.getsource(api).splitlines() if ln.startswith(("from ", "import ")) or ln.startswith("               ")]
        named = " ".join(imports).replace(",", " ").replace("(", " ").replace(")", " ").split()
        self.assertNotIn("addjob", named)
        self.assertNotIn("profile", named)
        src = inspect.getsource(adding) + inspect.getsource(__import__("modtrap.unpack", fromlist=["x"]))
        self.assertNotIn("addjob", src)


if __name__ == "__main__":
    unittest.main()
