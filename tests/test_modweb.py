"""One mod and the mods it has to do with (MT62), on an invented modlist: what it needs, what needs it, a patch made
for it, a tool's output, files overwritten either way, records two plugins both change (a conflict, one that a third
plugin settles, and a patch's own way of working), the link to its page, and its one picture."""

import base64
import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, model, modweb, probe, updates
from tests import _fixtures as fx
from tests.test_updates import FakeNet, meta

CORE = "Core.esm"
A, B, C = 0x00000A00, 0x00000B00, 0x00000C00
PNG = b"\x89PNG\r\n\x1a\n" + b"an invented picture, not a real one" * 4


def pf(masters, *globs):
    recs = [probe.glob(form, "MT_%X" % (form & 0xFFFFFF), value) for form, value in globs]
    return probe.plugin_file(list(masters), [probe.group(b"GLOB", recs)] if recs else [], len(recs), 0x900, "invented")


def invented(root: Path) -> Path:
    fx.make_instance(root, [
        ("+", "Tool Output", {"Generated.esp": pf((CORE, "Quill.esp"), (B, 4.0))}),
        ("+", "Outputs_separator", {}),
        ("+", "Bridge", {"Bridge.esp": pf((CORE, "Quill.esp", "Thistle.esp"), (C, 5.0))}),
        ("+", "Quill - Lantern Patch", {"QuillLanternPatch.esp": pf((CORE, "Quill.esp", "Lantern.esp"), (A, 6.0))}),
        ("+", "Thistle", {"Thistle.esp": pf((CORE,), (A, 7.0), (B, 7.0)), "textures/shared/a.dds": b"new", "meshes/thistle/own.nif": b"new"}),
        ("+", "Lantern", {"Lantern.esp": pf((CORE, "Quill.esp"))}),
        ("+", "Quill", {"Quill.esp": pf((CORE,), (A, 2.0)), "textures/shared/a.dds": b"old",
                        "meta.ini": meta(gameName="SkyrimSE", modid=4321, version="1.2", installationFile="Quill-4321-1-2.7z").encode()}),
        ("+", "Core", {CORE: pf((), (A, 1.0), (B, 1.0), (C, 1.0))}),
    ], load_order=[CORE, "Quill.esp", "Lantern.esp", "Thistle.esp", "QuillLanternPatch.esp", "Bridge.esp", "Generated.esp"],
        profile_settings="[custom_overwrites]\r\nInvented%20Patcher=Tool Output\r\n")
    return root


class TheWebOfAMod(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "Example List")
        self.m = model.build(instance.load(self.root))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def links(self, name: str, deep: bool = True) -> dict:
        got = modweb.web(self.m, self.m.instance.mod(name), deep)
        return {(x["kind"], x["mod"]): x for x in got["links"]}

    def test_what_the_headers_say_needs_needed_a_patch_and_a_tools_output(self):
        got = self.links("Quill", deep=False)
        self.assertEqual(sorted(got), [("needed", "Bridge"), ("needed", "Lantern"), ("needs", "Core"), ("output", "Tool Output"), ("patch", "Quill - Lantern Patch")])
        self.assertEqual(got[("needs", "Core")]["lines"], ["Quill.esp needs Core.esm"])
        self.assertEqual((got[("patch", "Quill - Lantern Patch")]["text"], got[("patch", "Quill - Lantern Patch")]["between"]), ("a patch for it: between it and Lantern", ["Lantern"]))
        # A mod that needs it and another, without saying "patch": told as needing it, with the other named.
        self.assertEqual((got[("needed", "Bridge")]["text"], got[("needed", "Lantern")]["text"]), ("1 of its plugins needs it, and Thistle", "1 of its plugins needs it"))
        self.assertEqual((got[("output", "Tool Output")]["tools"], got[("output", "Tool Output")]["lines"]), (["Invented Patcher"], ["Generated.esp needs Quill.esp"]))
        whole = modweb.web(self.m, self.m.instance.mod("Quill"), False)
        self.assertEqual((whole["deep"], whole["mod"]["priority"], [p["name"] for p in whole["mod"]["plugins"]]), (False, self.m.instance.mod("Quill").priority, ["Quill.esp"]))

    def test_files_overwritten_either_way_with_what_kind_they_are(self):
        quill, thistle = self.links("Quill"), self.links("Thistle")
        lost = quill[("overwritten", "Thistle")]
        self.assertEqual((lost["weight"], lost["kinds"], lost["lines"]), (1, {"textures": 1}, ["1 textures", "e.g. textures/shared/a.dds"]))
        won = thistle[("overwrites", "Quill")]
        self.assertEqual((won["weight"], won["text"]), (1, "1 file of it overwritten"))
        self.assertNotIn(("overwrites", "Thistle"), quill)

    def test_records_two_plugins_both_change_a_conflict_a_settled_one_and_a_patchs_own_way(self):
        quill, thistle = self.links("Quill"), self.links("Thistle")
        # Quill and Thistle both change a record of Core, neither knowing the other; Bridge has both as masters.
        settled = quill[("settled", "Thistle")]
        self.assertEqual((settled["weight"], settled["settled_by"], settled["loses"]), (1, ["Bridge.esp"], 1))
        self.assertIn("Bridge.esp has both as masters", settled["text"])
        self.assertEqual(thistle[("settled", "Quill")]["wins"], 1)
        # Thistle and the patch for Quill and Lantern: nobody has both. A conflict.
        clash = thistle[("conflict", "Quill - Lantern Patch")]
        self.assertEqual((clash["weight"], clash["lines"], clash["made"]), (1, ["Thistle.esp loses to QuillLanternPatch.esp in 1 record (GLOB 1)"], ""))
        # Thistle and the tool's output, which does not name it: a tool made that plugin from the load order as a
        # whole, to have the last word. Its work, and no conflict (MT73).
        self.assertNotIn(("conflict", "Tool Output"), thistle)
        last = thistle[("loses", "Tool Output")]
        self.assertEqual((last["weight"], last["lines"]), (1, ["Thistle.esp loses to Generated.esp in 1 record (GLOB 1)"]))
        self.assertEqual(last["text"], "its change wins over this mod's in 1 record: made by a tool to have the last word")
        self.assertTrue(last["made"].startswith("No conflict: a tool made Generated.esp from the load order as a whole. Such a plugin gathers"))
        out = self.links("Tool Output")
        self.assertEqual((out[("wins", "Thistle")]["made"], [k for k in out if k[0] == "conflict"]), (last["made"], []))
        # The patch changes what Quill changes and has Quill as a master: how a patch works, and no conflict.
        self.assertEqual(quill[("loses", "Quill - Lantern Patch")]["text"], "its change wins over this mod's in 1 record")
        self.assertNotIn(("conflict", "Quill - Lantern Patch"), quill)

    def test_a_plugin_after_a_tools_output_that_does_not_know_it_is_a_conflict_still(self):
        fx.write(self.root / "mods" / "Late" / "Late.esp", pf((CORE,), (B, 9.0)))
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Bridge\r\n", b"+Late\r\n+Bridge\r\n"))        # an ordinary mod, below the outputs' heading
        for n in ("plugins.txt", "loadorder.txt"):
            f = self.root / "profiles" / "Default" / n
            f.write_bytes(f.read_bytes() + (b"*" if n == "plugins.txt" else b"") + b"Late.esp\r\n")
        self.m = model.build(instance.load(self.root))
        late = self.links("Late")
        self.assertEqual(late[("conflict", "Tool Output")]["lines"], ["Late.esp wins over Generated.esp in 1 record (GLOB 1)"])      # it undoes the tool's work, unseen
        self.assertEqual(self.links("Tool Output")[("conflict", "Late")]["made"], "")

    def copies(self, files: dict) -> None:
        """ModTrap's own mod with demastered copies, above everything; made an hour ago, after every other mod."""
        for name, data in files.items():
            fx.write(self.root / "mods" / "ModTrap - Lantern" / name, data)
        fx.write(self.root / "mods" / "Demaster_separator" / "meta.ini", b"[General]\r\n")
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Tool Output\r\n", b"+ModTrap - Lantern\r\n+Demaster_separator\r\n+Tool Output\r\n"))
        then = time.time() - 3600
        for folder in (self.root / "mods").iterdir():
            os.utime(folder, (then - 3600, then - 3600))
        for name in files:
            os.utime(self.root / "mods" / "ModTrap - Lantern" / name, (then, then))
        self.m = model.build(instance.load(self.root))

    def test_modtraps_demastered_copy_stands_for_the_plugin_it_was_made_from(self):
        """MT74."""
        # Before: Thistle and the patch for Quill and Lantern change the same record, neither knowing the other.
        self.assertIn(("conflict", "Quill - Lantern Patch"), self.links("Thistle"))
        self.copies({"QuillLanternPatch.esp": pf((CORE, "Quill.esp"), (A, 6.0)), "Generated.esp": pf((CORE,), (B, 4.0))})
        self.assertEqual((self.m.row("QuillLanternPatch.esp").source, self.m.row("Generated.esp").source), ("ModTrap - Lantern", "ModTrap - Lantern"))
        got = modweb.web(self.m, self.m.instance.mod("ModTrap - Lantern"), True)
        self.assertEqual((got["mod"]["modtrap"], got["mod"]["copies"]), (True, ["Quill - Lantern Patch", "Tool Output"]))
        mine = {(x["kind"], x["mod"]): x for x in got["links"]}
        # The copy shares with Thistle what the plugin it stands for shared: as before, and not the demaster's doing.
        self.assertEqual([k for k in mine if k[0] == "conflict"], [])
        won = mine[("wins", "Thistle")]
        self.assertEqual((won["weight"], won["text"]), (2, "this mod's change wins in 2 records: as before the demaster"))
        self.assertTrue(won["made"].startswith("Not the demaster's doing: QuillLanternPatch.esp is ModTrap's demastered copy of the plugin in “Quill - Lantern Patch”, with the same records"))
        self.assertIn(("overwrites", "Tool Output"), mine)                      # the files it stands in for
        # And from the other mod's side the same.
        thistle = self.links("Thistle")
        self.assertEqual(([k for k in thistle if k[0] == "conflict"], thistle[("loses", "ModTrap - Lantern")]["text"]),
                         ([], "its change wins over this mod's in 2 records: as before the demaster"))

    def test_a_mod_that_came_after_the_copy_was_made_is_weighed_anew(self):
        """MT74."""
        self.copies({"QuillLanternPatch.esp": pf((CORE, "Quill.esp"), (A, 6.0)), "Generated.esp": pf((CORE,), (B, 4.0))})
        os.utime(self.root / "mods" / "Thistle")                                # installed now: after the demaster
        self.m = model.build(instance.load(self.root))
        got = self.links("ModTrap - Lantern")
        # The hand-made patch's copy never stood beside it: a conflict, as between any two such plugins.
        clash = got[("conflict", "Thistle")]
        self.assertEqual((clash["lines"], clash["made"]), (["QuillLanternPatch.esp wins over Thistle.esp in 1 record (GLOB 1)"], ""))
        # The copy of the tool's output has the last word as the tool's output has.
        last = got[("wins", "Thistle")]
        self.assertEqual(last["text"], "this mod's change wins in 1 record: made by a tool to have the last word")
        self.assertTrue(last["made"].startswith("No conflict: Generated.esp is ModTrap's demastered copy of a plugin a tool made from the load order as a whole."))

    def test_what_it_needs_is_counted_and_only_a_master_that_is_absent_or_off_is_a_fault(self):
        got = modweb.web(self.m, self.m.instance.mod("Bridge"), False)
        self.assertEqual((got["needs"], got["lacking"], got["lacks"]), (3, 0, []))
        profile_dir = self.root / "profiles" / "Default"
        f = profile_dir / "plugins.txt"
        f.write_bytes(f.read_bytes().replace(b"*Thistle.esp", b"Thistle.esp"))
        self.m = model.build(instance.load(self.root))
        got = modweb.web(self.m, self.m.instance.mod("Bridge"), False)
        self.assertEqual((got["needs"], got["lacking"], got["lacks"]), (3, 1, ["Bridge.esp needs Thistle.esp, which is not active"]))

    def test_the_links_come_in_the_order_of_their_kinds_and_are_counted(self):
        got = modweb.web(self.m, self.m.instance.mod("Quill"), True)
        kinds = [x["kind"] for x in got["links"]]
        self.assertEqual(kinds, sorted(kinds, key=modweb.KINDS.index))
        self.assertEqual(got["counts"], {"needs": 1, "needed": 2, "patch": 1, "output": 1, "overwritten": 1, "settled": 1, "loses": 1})
        self.assertTrue(got["deep"])


class ThePopUpsRoutes(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "Example List")
        self.api = api.Api()
        self.net = FakeNet({})
        self.pictures = []

        def public(query):
            if "game(domainName" in query:
                return 200, {}, {"data": {"game": {"id": 1704}}}
            if "thumbnailLargeUrl" in query:
                return 200, {}, {"data": {"mod": {"thumbnailLargeUrl": "https://images.nexusmods.com/mod-images/1704/t/large/43/4321/4321-1-2.png",
                                                  "pictureUrl": "https://staticdelivery.nexusmods.com/mods/1704/images/4321/4321-1-2.png"}}}
            return 404, {}, None

        def picture(url):
            self.pictures.append(url)
            return PNG, "image/png"
        self.net.public, self.net.picture = public, picture
        self.api.updating.net = self.net
        self.api.updating.by_itself = False
        self.api.running = lambda image: False
        self.api.open(str(self.root), wait=True)

    def tearDown(self):
        for _ in range(400):                              # what was begun when the modlist opened ends before its folder goes
            if self.api.updating.work["state"] != "going" and self.api.updating.reading["state"] != "going" and self.api._listscan["state"] not in ("going", "looking"):
                break
            time.sleep(0.01)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_web_comes_with_the_mods_page(self):
        got = self.api.post("/api/mod/web", {"mod": "Quill"})[1]
        self.assertEqual((got["deep"], got["source"]["host"], got["source"]["page"], got["source"]["picture"]),
                         (False, "nexus", "https://www.nexusmods.com/skyrimspecialedition/mods/4321", True))
        deep = self.api.post("/api/mod/web", {"mod": "Quill", "deep": True})[1]
        self.assertTrue(deep["deep"] and deep["counts"]["overwritten"] == 1)
        self.assertIsNone(self.api.post("/api/mod/web", {"mod": "Lantern"})[1]["source"])           # no record of where it came from
        for bad in ({"mod": "Nobody"}, {"mod": "Outputs_separator"}, {}):
            with self.assertRaises(api.Bad):
                self.api.post("/api/mod/web", bad)

    def test_the_one_picture_is_fetched_once_and_kept(self):
        got = self.api.post("/api/mod/picture", {"mod": "Quill"})[1]
        self.assertEqual((got["type"], base64.b64decode(got["data"])), ("image/png", PNG))
        self.assertEqual(self.pictures, ["https://images.nexusmods.com/mod-images/1704/t/large/43/4321/4321-1-2.png"])
        self.api.post("/api/mod/picture", {"mod": "Quill"})
        self.assertEqual(len(self.pictures), 1)                              # the second time from ModTrap's own keep
        # A mod without a site that gives one; and the setting.
        self.assertIn("none", self.api.post("/api/mod/picture", {"mod": "Lantern"})[1])
        self.api.post("/api/settings", {"name": "mod_pictures", "value": False})
        self.assertEqual(self.api.post("/api/mod/picture", {"mod": "Quill"})[1], {"none": "pictures are switched off in the settings"})
        self.assertFalse(self.api.post("/api/mod/web", {"mod": "Quill"})[1]["source"]["picture"])

    def test_a_picture_comes_only_from_the_picture_hosts_and_must_be_one(self):
        net = updates.Net("test")
        for url in ("https://example.com/a.png", "http://images.nexusmods.com/a.png", "https://images.nexusmods.com:8443/a.png", "https://www.nexusmods.com/a.png"):
            with self.assertRaises(updates.Refused) as c:
                net.picture(url)
            self.assertIn("not one ModTrap fetches a picture from", str(c.exception))
        self.assertEqual(updates.picture_address({"host": "github", "repo": "invented-owner/lantern"}, self.net), "https://opengraph.githubassets.com/1/invented-owner/lantern")
        self.assertEqual(updates.picture_address({"host": "loverslab", "url": "https://www.loverslab.com/files/file/1-x/"}, self.net), "")
        self.assertEqual(updates.home_of({"host": "github", "repo": "invented-owner/lantern"}), "https://github.com/invented-owner/lantern")


if __name__ == "__main__":
    unittest.main()
