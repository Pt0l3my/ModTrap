"""The Modlist page's own changes (MT56), on an invented modlist: mods enabled and disabled as MO2 does, their plugins
placed by MO2's rule (MO03), what is not safe about it, a mod moved, a separator renamed, each undone again; and
the scanner of what a mod's plugins overwrite."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, history, instance, listjob, loadcheck, logbook, model, probe, profile
from tests import _fixtures as fx

CORE = "Core.esm"
A, B, C = 0x00000A00, 0x00000B00, 0x00000C00            # Core's own records; 00 is Core in every plugin here


def pf(masters, *globs):
    recs = [probe.glob(form, "MT_%X" % (form & 0xFFFFFF), value) for form, value in globs]
    return probe.plugin_file(list(masters), [probe.group(b"GLOB", recs)] if recs else [], len(recs), 0x900, "invented")


def invented(root: Path) -> Path:
    """Core is the list's master, Quill and Lantern its ordinary mods, an invented patcher's output last. Disabled:
    Thistle (a plugin that changes what Quill and the output change), Beacon (a master), Needs Absent (a master
    nobody has), Twin (a second file of Quill's plugin)."""
    fx.make_instance(root, [
        ("+", "Tool Output", {"Generated.esp": pf((CORE, "Quill.esp"), (B, 4.0))}),
        ("+", "Outputs_separator", {}),
        ("-", "Thistle", {"Thistle.esp": pf((CORE, "Quill.esp"), (A, 7.0), (B, 7.0), (0x02000800, 1.0)), "textures/shared/a.dds": b"new",
                          "textures/thistle/own.dds": b"new"}),
        ("-", "Beacon", {"Beacon.esm": pf((CORE,))}),
        ("-", "Needs Absent", {"NeedsAbsent.esp": pf((CORE, "Nowhere.esp"))}),
        ("-", "Twin", {"Quill.esp": pf((CORE,))}),
        ("+", "Gear_separator", {}),
        ("+", "Quill", {"Quill.esp": pf((CORE,), (A, 2.0)), "textures/shared/a.dds": b"old"}),
        ("+", "Lantern", {"Lantern.esp": pf((CORE, "Quill.esp"))}),
        ("+", "Core", {CORE: pf((), (A, 1.0), (B, 1.0), (C, 1.0))}),
        ("*", "DLC: Dawnguard", {}),
    ], load_order=[CORE, "Quill.esp", "Lantern.esp", "Generated.esp"],
        profile_settings="[custom_overwrites]\r\nInvented%20Patcher=Tool Output\r\n")
    return root


class MO2sRule(unittest.TestCase):
    """MO03§2 to §4: a new plugin at the end, a master in the masters' block, nothing before its own masters."""

    ORDER = [("Skyrim.esm", True), (CORE, True), ("Quill.esp", False), ("Lantern.esp", False)]

    def test_a_new_plugin_goes_to_the_end_and_a_master_to_the_end_of_the_masters_block(self):
        got, followed = loadcheck.place(self.ORDER, [{"name": "New.esp", "master": False, "masters": (CORE,), "listed": False},
                                                     {"name": "New.esm", "master": True, "masters": ("Skyrim.esm",), "listed": False}])
        self.assertEqual(got, ["Skyrim.esm", CORE, "New.esm", "Quill.esp", "Lantern.esp", "New.esp"])
        self.assertEqual(followed, {})

    def test_no_plugin_loads_before_a_master_of_its_own(self):
        # Two that come together, the master named second: the one that needs it follows it.
        got, followed = loadcheck.place(self.ORDER, [{"name": "A Patch.esp", "master": False, "masters": ("Zed.esp",), "listed": False},
                                                     {"name": "Zed.esp", "master": False, "masters": (CORE,), "listed": False}])
        self.assertEqual(got[-2:], ["Zed.esp", "A Patch.esp"])
        self.assertEqual(followed, {"a patch.esp": "Zed.esp"})
        # One already in the list keeps its place, unless a master of its own loads after it.
        got, _ = loadcheck.place(self.ORDER, [{"name": "Quill.esp", "master": False, "masters": (CORE,), "listed": True}])
        self.assertEqual(got, [n for n, _m in self.ORDER])
        got, followed = loadcheck.place(self.ORDER, [{"name": "Quill.esp", "master": False, "masters": ("Lantern.esp",), "listed": True}])
        self.assertEqual((got, followed), (["Skyrim.esm", CORE, "Lantern.esp", "Quill.esp"], {"quill.esp": "Lantern.esp"}))
        # A master that needs a plugin which is no master stays in its block: the game loads masters first.
        got, _ = loadcheck.place(self.ORDER, [{"name": "Odd.esm", "master": True, "masters": ("Lantern.esp",), "listed": False}])
        self.assertEqual(got, ["Skyrim.esm", CORE, "Odd.esm", "Quill.esp", "Lantern.esp"])


class AMovedPlugin(unittest.TestCase):
    """MO03§3, §4: the limits MO2 keeps when a plugin is moved by hand."""

    ORDER = [{"name": "Skyrim.esm", "master": True, "primary": True, "masters": ()}, {"name": CORE, "master": True, "primary": False, "masters": ("Skyrim.esm",)},
             {"name": "Quill.esp", "master": False, "primary": False, "masters": (CORE,)}, {"name": "Lantern.esp", "master": False, "primary": False, "masters": ("Quill.esp",)},
             {"name": "Other.esp", "master": False, "primary": False, "masters": ()}]

    def test_where_it_may_stand(self):
        go = lambda name, before: loadcheck.place_moved(self.ORDER, name, before)       # noqa: E731
        self.assertEqual(go("Other.esp", "Quill.esp"), ("Quill.esp", ""))
        self.assertEqual(go("Other.esp", "Lantern.esp"), ("Lantern.esp", ""))
        self.assertEqual(go("Lantern.esp", "Quill.esp"), ("Other.esp", "it needs Quill.esp, which must load before it"))
        self.assertEqual(go("Quill.esp", ""), ("Lantern.esp", "Lantern.esp needs it, and must load after it"))
        self.assertEqual(go("Other.esp", CORE), ("Quill.esp", "it is no master, and the game loads masters before every other plugin"))
        self.assertEqual(go(CORE, ""), ("Quill.esp", "it is a master, and the game loads masters before every other plugin"))
        self.assertEqual(go(CORE, "Skyrim.esm"), ("Quill.esp", "the game's own plugins come first"))
        for name, before in (("Skyrim.esm", ""), ("Nobody.esp", ""), ("Other.esp", "Nobody.esp"), ("Other.esp", "Other.esp")):
            with self.assertRaises(loadcheck.Refused):
                go(name, before)


class TheModlistPage(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "Example List")
        self.pdir = self.root / "profiles" / "Default"
        self.api = api.Api()
        self.closed = True
        self.api.running = lambda image: not self.closed
        self.api.open(str(self.root), wait=True)
        self.api.changes = changes.Changes(self.api, require_probe=False)

    def tearDown(self):
        self.settle()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def settle(self):
        for _ in range(600):
            if self.api.status == "ready":
                return
            time.sleep(0.01)
        self.fail("the modlist was not read again")

    def post(self, path, body):
        self.settle()
        got = self.api.post(path, body)[1]
        self.settle()
        return got

    def lists(self):
        return {n: (self.pdir / n).read_bytes() for n in ("modlist.txt", "plugins.txt", "loadorder.txt")}

    def order(self):
        return [(n, a) for n, a in instance.load(self.root).load_order if n not in fx.GAME_PLUGINS]

    def events(self):
        return [(e["kind"], e.get("plugin") or e.get("mod")) for e in history.History(self.api.store.dir(self.api.session.id)).all()]

    # --- enabling and disabling ------------------------------------------------------------------------------------

    def test_a_mod_is_enabled_and_its_plugin_goes_to_the_end_as_in_mo2(self):
        before = self.lists()
        got = self.post("/api/list/set", {"mods": ["Thistle"], "on": True})
        self.assertTrue(got["done"])
        self.assertTrue(instance.load(self.root).mod("Thistle").enabled)
        self.assertEqual(self.order(), [(CORE, True), ("Quill.esp", True), ("Lantern.esp", True), ("Generated.esp", True), ("Thistle.esp", True)])
        self.assertIn(b"*Thistle.esp\r\n", self.lists()["plugins.txt"])
        plug = got["plan"]["plugins"][0]
        self.assertEqual((plug["name"], plug["how"], plug["why"]), ("Thistle.esp", "placed", "at the end of the load order"))
        # MO2's rule puts it after what the tools made: said, not asked about.
        self.assertFalse(got["plan"]["ask"])
        self.assertTrue(any("after what the tools made" in w["text"] for w in got["plan"]["warnings"]))
        self.assertEqual(self.events()[-2:], [("mod enabled", "Thistle"), ("plugin activated", "Thistle.esp")])
        self.assertEqual(self.api.get("/api/list", {})[1]["undo"]["text"], "Enabled “Thistle”: 1 plugin activated")
        # Undo: the three lists exactly as they were.
        back = self.post("/api/list/undo", {})
        self.assertEqual((back["how"], self.lists()), ("whole", before))
        self.assertIsNone(self.api.get("/api/list", {})[1]["undo"])
        with self.assertRaises(api.Bad):
            self.post("/api/list/undo", {})

    def test_a_master_goes_to_the_end_of_the_masters_block(self):
        got = self.post("/api/list/set", {"mods": ["Beacon"], "on": True})
        self.assertEqual(got["plan"]["plugins"][0]["why"], "at the end of the masters' block")
        self.assertEqual([n for n, _a in self.order()], [CORE, "Beacon.esm", "Quill.esp", "Lantern.esp", "Generated.esp"])
        self.assertEqual(got["plan"]["warnings"], [])

    def test_what_is_not_safe_is_asked_first_and_done_on_the_owners_word(self):
        before = self.lists()
        got = self.post("/api/list/set", {"mods": ["Needs Absent"], "on": True})
        self.assertEqual((got["done"], got["ask"]), (False, True))
        self.assertIn("NeedsAbsent.esp needs Nowhere.esp, which no enabled mod provides", got["plan"]["warnings"][0]["text"])
        self.assertEqual(self.lists(), before)
        got = self.post("/api/list/set", {"mods": ["Needs Absent"], "on": True, "sure": True})
        self.assertTrue(got["done"] and instance.load(self.root).mod("Needs Absent").enabled)
        # Disabling a mod whose plugin others need: asked, with who needs it.
        got = self.post("/api/list/set", {"mods": ["Quill"], "on": False})
        self.assertTrue(got["ask"])
        self.assertIn("Quill.esp is a master of 2 active plugins", got["plan"]["warnings"][0]["text"])
        self.assertIn("Lantern.esp", got["plan"]["warnings"][0]["text"])
        self.assertTrue(instance.load(self.root).mod("Quill").enabled)

    def test_a_disabled_mods_plugin_keeps_its_line_and_comes_back_to_its_place(self):
        got = self.post("/api/list/set", {"mods": ["Quill"], "on": False, "sure": True})
        self.assertEqual([(p["name"], p["how"]) for p in got["plan"]["plugins"]], [("Quill.esp", "deactivated")])
        self.assertFalse(instance.load(self.root).mod("Quill").enabled)
        self.assertEqual(self.order()[:2], [(CORE, True), ("Quill.esp", False)])           # the line stays, without its star
        got = self.post("/api/list/set", {"mods": ["Quill"], "on": True})
        self.assertEqual([(p["name"], p["how"], p["why"]) for p in got["plan"]["plugins"]], [("Quill.esp", "in place", "at the place it had in the load order")])
        self.assertEqual(self.order()[:3], [(CORE, True), ("Quill.esp", True), ("Lantern.esp", True)])
        # A mod already as wanted: nothing is done, and nothing is written.
        self.assertTrue(self.post("/api/list/set", {"mods": ["Quill"], "on": True})["nothing"])

    def test_a_second_file_of_a_plugin_leaves_the_plugin_alone(self):
        before = self.lists()
        got = self.post("/api/list/set", {"mods": ["Twin"], "on": True})
        self.assertEqual(got["plan"]["plugins"], [])
        self.assertIn("this mod's file replaces the one of “Quill”", got["plan"]["notes"][0])
        now = self.lists()
        self.assertEqual((now["plugins.txt"], now["loadorder.txt"]), (before["plugins.txt"], before["loadorder.txt"]))
        # Disabling Quill now leaves the plugin too: Twin's file takes over.
        got = self.post("/api/list/set", {"mods": ["Quill"], "on": False})
        self.assertEqual((got["done"], got["plan"]["plugins"]), (True, []))

    def test_nothing_is_changed_while_mo2_is_open_and_only_mods_can_be_ticked(self):
        before = self.lists()
        self.closed = False
        with self.assertRaises(api.Bad) as e:
            self.post("/api/list/set", {"mods": ["Thistle"], "on": True})
        self.assertIn("MO2 must be closed", str(e.exception))
        self.closed = True
        for body in ({"mods": ["Gear_separator"], "on": True}, {"mods": ["DLC: Dawnguard"], "on": False}, {"mods": ["Nobody"], "on": True},
                     {"mods": [], "on": True}, {"mods": ["Thistle"]}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/set", body)
        self.assertEqual(self.lists(), before)

    def test_an_undo_after_something_else_changed_the_lists_turns_back_only_its_own_lines(self):
        self.post("/api/list/set", {"mods": ["Thistle"], "on": True})
        profile.set_mods(self.pdir, {"Beacon": True})              # something else since: MO2, or another job
        self.api.open(str(self.root), wait=True)
        back = self.post("/api/list/undo", {})
        inst = instance.load(self.root)
        self.assertEqual((back["how"], inst.mod("Thistle").enabled, inst.mod("Beacon").enabled), ("by line", False, True))
        self.assertNotIn("Thistle.esp", [n for n, _a in self.order()])

    # --- moving ----------------------------------------------------------------------------------------------------

    def names(self):
        return [m.name for m in instance.load(self.root).mods if m.kind in ("mod", "separator", "foreign")]

    def test_a_mod_is_moved_and_keeps_its_state(self):
        start = self.names()
        self.assertEqual(start, ["DLC: Dawnguard", "Core", "Lantern", "Quill", "Gear_separator", "Twin", "Needs Absent", "Beacon", "Thistle",
                                 "Outputs_separator", "Tool Output"])
        before = self.lists()
        got = self.post("/api/list/move", {"mods": ["Thistle"], "before": "Quill"})
        self.assertEqual(self.names(), ["DLC: Dawnguard", "Core", "Lantern", "Thistle", "Quill", "Gear_separator", "Twin", "Needs Absent", "Beacon",
                                        "Outputs_separator", "Tool Output"])
        self.assertEqual(got["text"], "Moved “Thistle” to priority 3")
        inst = instance.load(self.root)
        self.assertEqual((inst.mod("Thistle").enabled, inst.mod("Quill").enabled), (False, True))
        self.assertEqual({n: v for n, v in self.lists().items() if n != "modlist.txt"}, {n: v for n, v in before.items() if n != "modlist.txt"})
        self.assertEqual(self.events()[-1], ("mod moved", "Thistle"))
        # A separator with the mods under it, as one block, to the highest priority.
        self.post("/api/list/move", {"mods": ["Gear_separator", "Twin", "Needs Absent"], "before": ""})
        self.assertEqual(self.names()[-5:], ["Outputs_separator", "Tool Output", "Gear_separator", "Twin", "Needs Absent"])
        self.assertEqual(instance.load(self.root).mod("Gear_separator").kind, "separator")
        # Undone one after the other, the newest first.
        self.post("/api/list/undo", {})
        self.post("/api/list/undo", {})
        self.assertEqual((self.names(), self.lists()), (start, before))

    def test_what_cannot_be_moved_is_refused(self):
        before = self.lists()
        for body in ({"mods": ["DLC: Dawnguard"], "before": "Quill"}, {"mods": ["Quill"], "before": "Quill"}, {"mods": ["Quill"], "before": "Nobody"},
                     {"mods": ["Lantern"], "before": "Quill"}, {"mods": ["Tool Output"], "before": ""}, {"mods": ["Nobody"], "before": ""}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/move", body)
        self.assertEqual(self.lists(), before)

    def test_a_move_is_undone_by_its_own_line_when_the_list_changed_since(self):
        self.post("/api/list/move", {"mods": ["Lantern"], "before": "Tool Output"})
        profile.set_mods(self.pdir, {"Beacon": True})
        self.api.open(str(self.root), wait=True)
        back = self.post("/api/list/undo", {})
        self.assertEqual((back["how"], self.names()[1:3], instance.load(self.root).mod("Beacon").enabled), ("by line", ["Core", "Lantern"], True))

    # --- a separator's name ----------------------------------------------------------------------------------------

    def test_a_separator_is_renamed_in_every_profile_and_back(self):
        other = self.root / "profiles" / "Second"
        fx.write(other / "modlist.txt", (self.pdir / "modlist.txt").read_bytes().replace(b"+Quill\r\n", b"-Quill\r\n"))
        self.api.open(str(self.root), wait=True)
        before, second = self.lists(), (other / "modlist.txt").read_bytes()
        at = instance.load(self.root).mod("Gear_separator").priority
        got = self.post("/api/list/rename", {"name": "Gear_separator", "to": "  Arms and   Armour "})
        self.assertEqual(got["name"], "Arms and Armour_separator")
        inst = instance.load(self.root)
        sep = inst.mod("Arms and Armour_separator")
        self.assertEqual((sep.kind, sep.priority, inst.mod("Gear_separator")), ("separator", at, None))
        self.assertTrue((self.root / "mods" / "Arms and Armour_separator").is_dir())
        self.assertFalse((self.root / "mods" / "Gear_separator").exists())
        self.assertIn(b"+Arms and Armour_separator\r\n", (other / "modlist.txt").read_bytes())
        self.assertEqual(self.events()[-1][0], "separator renamed")
        for body in ({"name": "Arms and Armour_separator", "to": "Outputs"}, {"name": "Arms and Armour_separator", "to": "a/b"},
                     {"name": "Arms and Armour_separator", "to": ""}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/rename", body)
        self.post("/api/list/undo", {})
        self.assertEqual((self.lists(), (other / "modlist.txt").read_bytes()), (before, second))
        self.assertTrue((self.root / "mods" / "Gear_separator").is_dir())

    def test_a_mod_is_renamed_as_mo2_does_and_back_and_a_tools_output_mod_is_not(self):
        """MT66: the folder, and the line in every profile's list; in the history, and undone by its job."""
        other = self.root / "profiles" / "Second"
        fx.write(other / "modlist.txt", (self.pdir / "modlist.txt").read_bytes().replace(b"+Lantern\r\n", b"-Lantern\r\n"))
        self.api.open(str(self.root), wait=True)
        before, second = self.lists(), (other / "modlist.txt").read_bytes()
        at = instance.load(self.root).mod("Lantern").priority
        got = self.post("/api/list/rename", {"name": "Lantern", "to": " Lantern  of the North "})
        self.assertEqual((got["name"], got["text"]), ("Lantern of the North", "Renamed the mod “Lantern” to “Lantern of the North”"))
        inst = instance.load(self.root)
        self.assertEqual((inst.mod("Lantern of the North").priority, inst.mod("Lantern of the North").enabled, inst.mod("Lantern")), (at, True, None))
        self.assertTrue((self.root / "mods" / "Lantern of the North" / "Lantern.esp").is_file())
        self.assertIn(b"-Lantern of the North\r\n", (other / "modlist.txt").read_bytes())
        self.assertEqual(self.events()[-1][0], "mod renamed")
        for body in ({"name": "Lantern of the North", "to": "Quill"}, {"name": "Lantern of the North", "to": "x_separator_y/z"}, {"name": "Tool Output", "to": "Made"}):
            with self.assertRaises(api.Bad) as c:
                self.post("/api/list/rename", body)
        self.assertIn("is the mod the tool “Invented Patcher” writes into", str(c.exception))
        job = self.api.get("/api/history", {})[1]["list_jobs"][0]
        self.assertEqual((job["op"], job["undone"], job["mods"]), ("rename", "", ["Lantern of the North"]))
        self.post("/api/list/undo", {"job": job["job"]})
        self.assertEqual((self.lists(), (other / "modlist.txt").read_bytes()), (before, second))
        self.assertTrue((self.root / "mods" / "Lantern" / "Lantern.esp").is_file())
        self.assertNotEqual(self.api.get("/api/history", {})[1]["list_jobs"][0]["undone"], "")

    def test_a_mod_is_uninstalled_by_moving_it_aside_and_put_back_from_the_history(self):
        """MT66: out of every profile's list and out of the mods folder; nothing deleted; its plugin leaves the load
        order; asked first; the job stays in the history and its Revert puts everything back."""
        other = self.root / "profiles" / "Second"
        fx.write(other / "modlist.txt", (self.pdir / "modlist.txt").read_bytes().replace(b"+Lantern\r\n", b"-Lantern\r\n"))
        self.api.open(str(self.root), wait=True)
        before, second = self.lists(), (other / "modlist.txt").read_bytes()
        asked = self.post("/api/list/uninstall", {"mods": ["Quill"]})
        self.assertEqual((asked["done"], asked["original"], asked["unknown"]), (False, [], ["Quill"]))
        self.assertTrue(asked["ask"] and "Lantern.esp" in str(asked["plan"]))               # a plugin that needs it loses its master: said first
        self.assertEqual(self.lists(), before)
        got = self.post("/api/list/uninstall", {"mods": ["Lantern"], "sure": True})
        self.assertEqual(got["text"], "Uninstalled “Lantern”: 1 plugin left the load order")
        inst = instance.load(self.root)
        self.assertIsNone(inst.mod("Lantern"))
        self.assertFalse((self.root / "mods" / "Lantern").exists())
        kept = self.root / listjob.REMOVED / got["job"] / "Lantern"
        self.assertTrue((kept / "Lantern.esp").is_file())                                    # moved, whole: nothing deleted
        self.assertNotIn(b"Lantern", (other / "modlist.txt").read_bytes())
        self.assertNotIn(b"Lantern.esp", (self.pdir / "plugins.txt").read_bytes() + (self.pdir / "loadorder.txt").read_bytes())
        self.assertEqual(self.events()[-1][0], "mod uninstalled")
        job = self.api.get("/api/history", {})[1]["list_jobs"][0]
        self.assertEqual((job["op"], job["mods"], job["kept"].replace("\\", "/")), ("uninstall", ["Lantern"], listjob.REMOVED + "/" + got["job"]))
        self.api.post("/api/jobs/clear", {})                                                 # clearing the job list does not touch it
        self.assertEqual(self.api.get("/api/history", {})[1]["list_jobs"][0]["job"], got["job"])
        for bad in ({"mods": ["Gear_separator"]}, {"mods": ["Nobody"]}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/uninstall", bad)
        self.post("/api/list/undo", {"job": got["job"]})
        self.assertEqual((self.lists(), (other / "modlist.txt").read_bytes()), (before, second))
        self.assertTrue((self.root / "mods" / "Lantern" / "Lantern.esp").is_file())
        self.assertFalse((self.root / listjob.REMOVED).exists())
        self.assertEqual([e[0] for e in self.events()[-2:]], ["mod put back", "reverted"])

    def test_a_mod_that_came_with_the_modlist_is_named_as_such_before_it_is_uninstalled(self):
        rows = [{"mod": "Lantern", "origin": "list"}, {"mod": "Thistle", "origin": "added"}, {"mod": "Beacon", "origin": ""}]
        self.api._rows = lambda m: rows
        asked = self.post("/api/list/uninstall", {"mods": ["Lantern", "Thistle", "Beacon"]})
        self.assertEqual((asked["done"], asked["original"], asked["unknown"]), (False, ["Lantern"], ["Beacon"]))
        got = self.post("/api/list/uninstall", {"mods": ["Lantern", "Thistle"], "sure": True})
        self.assertEqual(got["text"], "Uninstalled “Lantern” and 1 more: 1 plugin left the load order")
        said = [e for e in history.History(self.api.store.dir(self.api.session.id)).all() if e["kind"] == "mod uninstalled"]
        self.assertEqual([(e["mod"], e["original"], e["was"]) for e in said], [("Lantern", True, "enabled"), ("Thistle", False, "disabled")])

    def test_an_uninstall_is_put_back_by_its_own_lines_when_the_lists_changed_since(self):
        got = self.post("/api/list/uninstall", {"mods": ["Lantern"], "sure": True})
        self.settle()
        self.post("/api/list/set", {"mods": ["Beacon"], "on": True, "sure": True})          # a later change of the same lists
        self.settle()
        done = self.post("/api/list/undo", {"job": got["job"]})
        self.assertEqual(done["how"], "by line")
        inst = instance.load(self.root)
        m = model.build(inst)
        lantern = inst.mod("Lantern")
        self.assertTrue(lantern.enabled and inst.mod("Beacon").enabled)                      # both stand: the later change was not undone with it
        self.assertEqual(lantern.priority, inst.mod("Quill").priority - 1)                    # back where it stood: directly below Quill
        row = m.row("Lantern.esp")
        self.assertTrue(row.active and row.position is not None and row.position > m.row("Quill.esp").position)

    # --- the scanner -----------------------------------------------------------------------------------------------

    def test_the_scanner_tells_what_a_mods_plugins_overwrite(self):
        # Disabled: what enabling it would do.
        got = self.post("/api/list/scan", {"mod": "Thistle"})
        self.assertEqual((got["enabled"], [p["name"] for p in got["plan"]["plugins"]]), (False, ["Thistle.esp"]))
        self.post("/api/list/set", {"mods": ["Thistle"], "on": True})
        got = self.post("/api/list/scan", {"mod": "Thistle"})
        p = got["plugins"][0]
        self.assertEqual((p["name"], p["position"], p["records"], p["own"], p["problems"]), ("Thistle.esp", len(fx.GAME_PLUGINS) + 4, 3, 1, []))
        self.assertEqual(p["masters"], [{"name": CORE, "records": 2, "kinds": {"GLOB": 2}}])
        self.assertEqual(sorted((x["plugin"], x["mod"], x["records"]) for x in p["overwrites"]), [("Generated.esp", "Tool Output", 1), ("Quill.esp", "Quill", 1)])
        self.assertEqual(p["overwritten_by"], [])
        self.assertTrue(any("which a tool made" in n for n in p["notes"]))
        self.assertTrue(got["safe"])
        # Its files: it stands above Quill and has one file of Quill's name.
        self.assertEqual([(w["mod"], w["files"]) for w in got["files"]["wins"]], [("Quill", 1)])
        self.assertEqual(got["files"]["loses"], [])
        # Seen from Quill: Thistle, which loads later, overwrites its change; and its file.
        got = self.post("/api/list/scan", {"mod": "Quill"})
        q = got["plugins"][0]
        self.assertEqual([(x["plugin"], x["records"]) for x in q["overwritten_by"]], [("Thistle.esp", 1)])
        self.assertEqual([(w["mod"], w["files"]) for w in got["files"]["loses"]], [("Thistle", 1)])

    def test_the_scanner_names_a_master_that_is_missing(self):
        self.post("/api/list/set", {"mods": ["Needs Absent"], "on": True, "sure": True})
        got = self.post("/api/list/scan", {"mod": "Needs Absent"})
        self.assertEqual((got["safe"], got["plugins"][0]["problems"]), (False, ["its master Nowhere.esp is missing"]))

    # --- the Plugins tab (MT58) ------------------------------------------------------------------------------------

    def plugin_rows(self):
        return {r["name"]: r for r in self.api.get("/api/plugins", {})[1]["plugins"]}

    def test_a_plugin_is_switched_off_without_a_question_and_what_follows_shows_on_the_rows(self):
        before = self.lists()
        got = self.post("/api/list/plugins/set", {"plugins": ["Quill.esp"], "on": False})
        self.assertEqual((got["done"], got["text"], sorted(got["lack"])), (True, "Deactivated Quill.esp", ["Generated.esp", "Lantern.esp"]))
        self.assertEqual(self.order()[:2], [(CORE, True), ("Quill.esp", False)])
        rows = self.plugin_rows()
        self.assertEqual((rows["Lantern.esp"]["inactive"], rows["Generated.esp"]["inactive"], rows["Quill.esp"]["active"]), (["Quill.esp"], ["Quill.esp"], False))
        self.assertEqual(self.lists()["modlist.txt"], before["modlist.txt"])
        self.assertEqual(self.events()[-1], ("plugin deactivated", "Quill.esp"))
        self.assertTrue(self.post("/api/list/plugins/set", {"plugins": ["Quill.esp"], "on": False})["nothing"])
        self.post("/api/list/undo", {})
        self.assertEqual(self.lists(), before)
        for body in ({"plugins": ["Skyrim.esm"], "on": False}, {"plugins": ["Nobody.esp"], "on": True}, {"plugins": [], "on": True}, {"plugins": ["Quill.esp"]}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/plugins/set", body)

    def test_a_plugin_the_load_order_does_not_name_yet_is_activated_at_the_end(self):
        profile.set_mods(self.pdir, {"Thistle": True})              # enabled elsewhere: its plugin has a file, and no line yet
        self.api.open(str(self.root), wait=True)
        self.assertIsNone(self.plugin_rows()["Thistle.esp"]["position"])
        got = self.post("/api/list/plugins/set", {"plugins": ["Thistle.esp"], "on": True})
        self.assertTrue(got["done"])
        self.assertEqual(self.order()[-1], ("Thistle.esp", True))
        # A plugin whose mod is not enabled has no file to load: refused, in words.
        with self.assertRaises(api.Bad) as e:
            self.post("/api/list/plugins/set", {"plugins": ["Beacon.esm"], "on": True})
        self.assertIn("not a plugin of this modlist", str(e.exception))

    def test_a_plugin_is_moved_and_keeps_its_state(self):
        before = self.lists()
        got = self.post("/api/list/plugins/move", {"plugin": "Generated.esp", "before": "Lantern.esp"})
        self.assertEqual((got["done"], got["why"], got["position"]), (True, "", len(fx.GAME_PLUGINS) + 2))
        self.assertEqual([n for n, _a in self.order()], [CORE, "Quill.esp", "Generated.esp", "Lantern.esp"])
        self.assertTrue(all(a for _n, a in self.order()))
        self.assertEqual((self.events()[-1], self.lists()["modlist.txt"]), (("plugin moved", "Generated.esp"), before["modlist.txt"]))
        self.assertEqual(self.api.get("/api/list", {})[1]["undo"]["text"], "Moved Generated.esp to place %d of the load order" % (len(fx.GAME_PLUGINS) + 2))
        # An inactive plugin stays inactive when it is moved.
        self.post("/api/list/plugins/set", {"plugins": ["Lantern.esp"], "on": False})
        self.post("/api/list/plugins/move", {"plugin": "Lantern.esp", "before": "Generated.esp"})
        self.assertEqual(self.order(), [(CORE, True), ("Quill.esp", True), ("Lantern.esp", False), ("Generated.esp", True)])
        for _ in range(3):
            self.post("/api/list/undo", {})
        self.assertEqual(self.lists(), before)

    def test_a_moved_plugin_stays_within_the_limits_mo2_keeps(self):
        before = self.lists()
        # Above its own master: it stays right after it, which is where it is.
        got = self.post("/api/list/plugins/move", {"plugin": "Lantern.esp", "before": "Quill.esp"})
        self.assertEqual((got["done"], got["nothing"]), (False, True))
        self.assertIn("it needs Quill.esp", got["why"])
        # A master's plugin below a plugin that needs it: it stops right above the first that does.
        got = self.post("/api/list/plugins/move", {"plugin": "Quill.esp", "before": ""})
        self.assertTrue(got["nothing"])
        self.assertIn("Lantern.esp needs it", got["why"])
        # No master among the masters, and nothing above the game's own plugins.
        got = self.post("/api/list/plugins/move", {"plugin": "Generated.esp", "before": CORE})
        self.assertEqual((got["done"], got["before"]), (True, "Lantern.esp"))
        self.assertIn("it needs Quill.esp", got["why"])
        self.assertEqual(self.lists()["modlist.txt"], before["modlist.txt"])
        for body in ({"plugin": "Skyrim.esm", "before": ""}, {"plugin": "Nobody.esp", "before": ""}, {"plugin": "Quill.esp", "before": "Nobody.esp"},
                     {"plugin": "Quill.esp", "before": "Quill.esp"}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/plugins/move", body)

    def test_a_plugin_that_loads_before_its_master_is_marked_and_one_plugin_is_scanned(self):
        lo = self.pdir / "loadorder.txt"
        lo.write_bytes(lo.read_bytes().replace(b"Quill.esp\r\nLantern.esp\r\n", b"Lantern.esp\r\nQuill.esp\r\n"))
        self.api.open(str(self.root), wait=True)
        rows = self.plugin_rows()
        self.assertEqual((rows["Lantern.esp"]["early"], rows["Quill.esp"]["early"]), (["Quill.esp"], []))
        got = self.post("/api/list/scan", {"plugin": "Lantern.esp"})
        self.assertEqual(([p["name"] for p in got["plugins"]], got["plugins"][0]["problems"], got["safe"]),
                         (["Lantern.esp"], ["it loads before its master Quill.esp"], False))
        got = self.post("/api/list/scan", {"plugin": "Generated.esp"})
        self.assertEqual(got["plugins"][0]["masters"], [{"name": CORE, "records": 1, "kinds": {"GLOB": 1}}])


if __name__ == "__main__":
    unittest.main()
