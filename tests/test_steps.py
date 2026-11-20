import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, model, plugin, steps
from tests import _fixtures as fx


class StepsTests(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        mods = self.root / "mods"
        # What Bramble carries beside its plugin, and two mods that exist only because of it.
        for rel in ("meshes/actors/character/animations/BrambleAnim/wave.hkx", "meshes/bramble/leaf.nif",
                    "textures/bramble/leaf.dds", "scripts/bramblequest.pex", "SKSE/Plugins/Bramble.ini"):
            fx.write(mods / "Bramble" / rel, b"invented")
        for rel in ("meshes/bramble/leaf.nif", "textures/bramble/leaf.dds"):
            fx.write(mods / "Bramble Hotfix" / rel, b"invented, newer")
        fx.write(mods / "Quill" / "SKSE" / "Plugins" / "Quill_DISTR.ini", "Keyword = 0x801~Bramble.esp|ActorTypeNPC\n")
        fx.write(mods / "Quill" / "Quill_KID.ini", "nothing of interest\n")
        p = self.root / "profiles" / "Default" / "modlist.txt"
        p.write_bytes(p.read_bytes().replace(b"+Tool Output", b"+Bramble Hotfix\r\n+Tool Output"))
        ini = self.root / "ModOrganizer.ini"
        ini.write_bytes(ini.read_bytes() + b"[customExecutables]\r\nsize=2\r\n1\\title=xEdit\r\n1\\binary=C:/T/SSEEdit64.exe\r\n"
                        b"2\\title=Invented Behaviour Engine\r\n2\\binary=C:/T/Pandora Behaviour Engine+.exe\r\n")

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def build(self):
        return model.build(instance.load(self.root))

    def test_contents_and_what_they_feed(self):
        c = steps.contents(self.root / "mods" / "Bramble")
        self.assertEqual({k: v["count"] for k, v in c["kinds"].items()},
                         {"animations": 1, "meshes": 1, "textures": 1, "scripts": 1,
                          "settings for a script extender plugin": 1, "other files": 1})
        self.assertEqual(steps.tools_for(self.build().instance, "animations"), ["Invented Behaviour Engine"])

    def test_a_mod_that_only_replaces_the_ticked_mods_files_is_found(self):
        m = self.build()
        deep = steps.look_deeper(m, ["Bramble"])
        self.assertEqual([(r["mod"], r["shared"], r["files"]) for r in deep["replacements"]], [("Bramble Hotfix", 2, 2)])
        self.assertEqual(deep["mentions"], [{"mod": "Quill", "file": "SKSE/Plugins/Quill_DISTR.ini", "names": ["Bramble.esp"]}])

    def test_steps_before_and_after(self):
        m = self.build()
        deep = steps.look_deeper(m, ["Bramble"])
        s = steps.compile_steps(m, ["Bramble"], None, deep)
        by = {x["key"]: x for x in s["steps"]}
        self.assertEqual([x["key"] for x in s["steps"]],
                         ["dry", "switch-off", "demaster", "regenerate", "disable", "tool:animations", "mentions",
                          "health", "play"])
        self.assertEqual((by["dry"]["state"], by["demaster"]["state"], by["disable"]["state"]),
                         ("to do", "waiting for the dry run", "waiting"))
        self.assertEqual([i["plugin"] for i in by["regenerate"]["items"]], ["Generated.esp"])
        self.assertEqual([(d["mod"], d["why"][:6]) for d in by["disable"]["items"]],
                         [("Bramble", "ticked"), ("Bramble Hotfix", "2 of i")])
        self.assertIn("Invented Behaviour Engine", by["tool:animations"]["title"])
        self.assertIn("compiled script", by["play"]["why"])
        self.assertFalse(s["complete"])
        # A dry run's verdicts sort the dependants.
        job = {"state": "done", "plan": {"trapped_mods": ["Bramble"]}, "result": {"files": [
            {"name": "Lantern.esp", "reading": "can be demastered", "own": 1, "entries": 1, "needs_you": 0},
            {"name": "BrambleLanternPatch.esp", "reading": "patch only", "own": 3, "entries": 0, "needs_you": 0},
            {"name": "Collection - Bramble.esp", "reading": "patch only", "own": 2, "entries": 0, "needs_you": 0},
            {"name": "Generated.esp", "reading": "needs you", "own": 1, "entries": 0, "needs_you": 1}]}}
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], job, deep)["steps"]}
        self.assertEqual(by["dry"]["state"], "done")
        self.assertEqual([i["plugin"] for i in by["switch-off"]["items"]], ["BrambleLanternPatch.esp", "Collection - Bramble.esp"])
        self.assertEqual([i["plugin"] for i in by["demaster"]["items"]], ["Lantern.esp"])

    def test_the_modlist_itself_shows_the_steps_done(self):
        b = plugin.build
        mods = self.root / "mods"
        # The owner did the work by hand: the dependants no longer list Bramble, the patches are off.
        fx.write(mods / "Lantern" / "Lantern.esp", b(("Skyrim.esm",)))
        fx.write(mods / "Tool Output" / "Generated.esp", b(("Skyrim.esm", "Quill.esp")))
        pl = self.root / "profiles" / "Default" / "plugins.txt"
        pl.write_bytes(pl.read_bytes().replace(b"*BrambleLanternPatch.esp", b"BrambleLanternPatch.esp")
                       .replace(b"*Collection - Bramble.esp", b"Collection - Bramble.esp"))
        s = steps.compile_steps(self.build(), ["Bramble"], None, {})
        by = {x["key"]: x for x in s["steps"]}
        self.assertEqual((by["dry"]["state"], by["demaster"]["state"], by["disable"]["state"]), ("not needed", "done", "to do"))
        # ...and then disabled the mod: nothing is missing, every provable step is done.
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Bramble\r\n", b"-Bramble\r\n").replace(b"+Bramble Hotfix", b"-Bramble Hotfix"))
        pl.write_bytes(pl.read_bytes().replace(b"*Bramble.esp\r\n", b""))
        lo = self.root / "profiles" / "Default" / "loadorder.txt"
        lo.write_bytes(lo.read_bytes().replace(b"Bramble.esp\r\n", b"", 1))
        s = steps.compile_steps(self.build(), ["Bramble"], None, {})
        by = {x["key"]: x for x in s["steps"]}
        self.assertEqual((by["disable"]["state"], by["health"]["state"], by["play"]["state"]), ("done", "done", "to do"))
        self.assertTrue(s["complete"])

    def test_through_the_api_the_deep_part_arrives_later(self):
        a = api.Api()
        a.open(str(self.root), wait=True)
        first = a.steps({"mods": ["Bramble"]})
        for _ in range(200):
            out = a.steps({"mods": ["Bramble"]})
            if not out["looking"]:
                break
            time.sleep(0.02)
        self.assertTrue(first["steps"])
        self.assertEqual(out["contents"]["animations"], 1)
        self.assertIn("mentions", [x["key"] for x in out["steps"]])
        self.assertEqual(a.steps({"mods": []})["steps"], [])


if __name__ == "__main__":
    unittest.main()
