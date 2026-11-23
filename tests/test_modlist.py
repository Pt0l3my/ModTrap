"""The Modlist page's own changes (MT56), on an invented modlist: mods enabled and disabled as MO2 does, their plugins
placed by MO2's rule (MO03), what is not safe about it, a mod moved, a separator renamed, each undone again; and
the scanner of what a mod's plugins overwrite."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, history, instance, loadcheck, logbook, model, probe, profile
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
                     {"name": "Quill", "to": "Other"}, {"name": "Arms and Armour_separator", "to": ""}):
            with self.assertRaises(api.Bad):
                self.post("/api/list/rename", body)
        self.post("/api/list/undo", {})
        self.assertEqual((self.lists(), (other / "modlist.txt").read_bytes()), (before, second))
        self.assertTrue((self.root / "mods" / "Gear_separator").is_dir())

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


if __name__ == "__main__":
    unittest.main()
