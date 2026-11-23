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
        # Thistle and the tool's output: nobody has both. A conflict, told from each side.
        clash = thistle[("conflict", "Tool Output")]
        self.assertEqual((clash["weight"], clash["lines"]), (1, ["Thistle.esp loses to Generated.esp in 1 record (GLOB 1)"]))
        self.assertIn(("conflict", "Quill - Lantern Patch"), thistle)
        # The patch changes what Quill changes and has Quill as a master: how a patch works, and no conflict.
        self.assertEqual(quill[("loses", "Quill - Lantern Patch")]["text"], "its change wins over this mod's in 1 record")
        self.assertNotIn(("conflict", "Quill - Lantern Patch"), quill)

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
            if self.api.updating.work["state"] != "going" and self.api.updating.reading["state"] != "going" and self.api._listscan["state"] != "going":
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
