import json
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
        for rel in ("meshes/actors/character/animations/BrambleAnim/wave.hkx",
                    "meshes/actors/character/animations/BrambleAnim/FNIS_BrambleAnim_List.txt",
                    "meshes/actors/character/behaviors/FNIS_BrambleAnim_Behavior.hkx", "meshes/bramble/leaf.nif",
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
                         {"animations": 3, "meshes": 1, "textures": 1, "scripts": 1,
                          "settings for a script extender plugin": 1, "other files": 1})
        self.assertEqual(steps.tools_for(self.build().instance, "animations"), ["Invented Behaviour Engine"])

    def test_a_behaviour_tool_is_asked_for_what_it_reads_not_for_any_animation_file(self):
        """TL01§12, WHY§69: a behaviour tool reads animation lists and patch folders. A mod with plain animation
        files only gives it nothing to read; its output is searched for the names of the mod's animation folders."""
        mods = self.root / "mods"
        (mods / "Bramble" / "meshes/actors/character/animations/BrambleAnim/FNIS_BrambleAnim_List.txt").unlink()
        m = self.build()
        deep = steps.look_deeper(m, ["Bramble"])
        self.assertEqual((deep["animation"]["lists"], deep["animation"]["plain"], deep["animation"]["folders"]),
                         ([], 1, ["brambleanim"]))
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep)["steps"]}
        self.assertNotIn("tool:Pandora Behaviour Engine", by)
        cleared = [i["text"] for i in by["tools-clear"]["items"] if i["text"].startswith("Pandora")]
        self.assertEqual(len(cleared), 1)
        self.assertIn("plain files: it has no animation list (FNIS_…_List.txt) and no behaviour patch folder", cleared[0])
        # A patch folder is something the tool reads; so is a list for a creature.
        fx.write(mods / "Bramble" / "Nemesis_Engine" / "mod" / "brmb" / "info.ini", b"invented")
        deep = steps.look_deeper(self.build(), ["Bramble"])
        self.assertEqual(deep["animation"]["nemesis_engine"], ["brmb"])
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep)["steps"]}
        self.assertIn("the mod carries 1 animation list(s) or behaviour patch folder(s)", by["tool:Pandora Behaviour Engine"]["why"])

    def test_pandora_passes_over_a_list_that_has_no_graph_file(self):
        """TL01§12, WHY§72: Pandora takes an animation list in only where FNIS_<folder>_Behavior.hkx is in the
        behaviour folder too, in the mod or in any enabled mod."""
        (self.root / "mods" / "Bramble" / "meshes/actors/character/behaviors/FNIS_BrambleAnim_Behavior.hkx").unlink()
        m = self.build()
        deep = steps.look_deeper(m, ["Bramble"])
        self.assertEqual((len(deep["animation"]["lists_with_graph"]), len(deep["animation"]["lists_without_graph"])), (0, 1))
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep)["steps"]}
        self.assertNotIn("tool:Pandora Behaviour Engine", by)
        cleared = [i["text"] for i in by["tools-clear"]["items"] if i["text"].startswith("Pandora")]
        self.assertIn("have no graph file with them", cleared[0])
        # With the graph file in another enabled mod, the list is read.
        fx.write(self.root / "mods" / "Quill" / "meshes/actors/character/behaviors/FNIS_BrambleAnim_Behavior.hkx", b"invented")
        m = self.build()
        deep = steps.look_deeper(m, ["Bramble"])
        self.assertEqual(len(deep["animation"]["lists_with_graph"]), 1)
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep)["steps"]}
        self.assertIn("the mod carries 1 animation list(s) or behaviour patch folder(s)", by["tool:Pandora Behaviour Engine"]["why"])

    def test_a_behaviour_tools_output_that_names_the_mods_animation_folder(self):
        mods = self.root / "mods"
        (mods / "Bramble" / "meshes/actors/character/animations/BrambleAnim/FNIS_BrambleAnim_List.txt").unlink()
        fx.write(mods / "Engine Output" / "meshes/actors/character/characters/defaultmale.hkx",
                 b"\x00packed\x00Animations\\BrambleAnim\\wave.hkx\x00more")
        fx.write(mods / "Engine Output" / "meshes/actors/character/behaviors/0_master.hkx", b"\x00nothing of it\x00")
        p = self.root / "profiles" / "Default" / "modlist.txt"
        p.write_bytes(p.read_bytes().replace(b"+Tool Output", b"+Engine Output\r\n+Tool Output"))
        st = self.root / "profiles" / "Default" / "settings.ini"
        st.write_bytes((st.read_bytes() if st.is_file() else b"") + b"[custom_overwrites]\r\nInvented%20Behaviour%20Engine=Engine Output\r\n")
        m = self.build()
        self.assertEqual(m.instance.output_mods.get("Invented Behaviour Engine"), "Engine Output")
        deep = steps.look_deeper(m, ["Bramble"])
        got = deep["animation"]["searched"]
        self.assertEqual([(x["mod"], x["files"], x["hit_count"]) for x in got], [("Engine Output", 2, 1)])
        self.assertEqual(got[0]["hits"][0]["file"], "meshes/actors/character/characters/defaultmale.hkx")
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep)["steps"]}
        why = by["tool:Pandora Behaviour Engine"]["why"]
        self.assertIn("1 file(s) of its output in “Engine Output” name a folder of the mod's animations", why)
        self.assertIn("What speaks against it: the mod's 2 animation file(s) are plain files", why)

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
                         ["dry", "switch-off", "demaster", "regenerate", "disable", "tool:Pandora Behaviour Engine",
                          "tools-clear", "mentions", "health", "play"])
        self.assertEqual((by["dry"]["state"], by["demaster"]["state"], by["disable"]["state"]),
                         ("to do", "waiting for the dry run", "waiting"))
        self.assertEqual([i["plugin"] for i in by["regenerate"]["items"]], ["Generated.esp"])
        self.assertEqual([(d["mod"], d["why"][:6]) for d in by["disable"]["items"]],
                         [("Bramble", "ticked"), ("Bramble Hotfix", "2 of i")])
        engine = by["tool:Pandora Behaviour Engine"]                    # named by what the tool is, with its start button
        self.assertEqual([i["tool"] for i in engine["items"] if "tool" in i], ["Invented Behaviour Engine"])
        self.assertIn("the mod carries 1 animation list(s) or behaviour patch folder(s), which this tool reads", engine["why"])
        self.assertIn("meshes/actors/character/animations/bramblanim/fnis_bramblanim_list.txt".replace("bramblanim", "brambleanim"),
                      [ln for i in engine["items"] if "details" in i for ln in i["details"]["lines"]])
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
        self.assertEqual([i["plugin"] for i in by["regenerate"]["items"]], ["Generated.esp"])   # needs you: the tool makes it again
        self.assertEqual({by[k]["who"] for k in ("switch-off", "demaster", "disable")}, {"you"})
        self.assertEqual(by["switch-off"]["action"], "")
        # Started with the switch, these are ModTrap's steps, with the button; and a tool's output that the dry run
        # found demasterable is demastered with the rest, as "Demaster Selected" does (WHY§57).
        job["result"]["files"][3]["reading"] = "can be demastered"
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], job, deep, auto=True)["steps"]}
        self.assertEqual({by[k]["who"] for k in ("switch-off", "demaster", "disable")}, {"ModTrap"})
        self.assertEqual((by["switch-off"]["action"], by["demaster"]["action"], by["disable"]["action"]), ("demaster", "demaster", ""))
        self.assertEqual([i["plugin"] for i in by["demaster"]["items"]], ["Lantern.esp", "Generated.esp"])
        self.assertNotIn("regenerate", by)
        self.assertIn("Demaster Selected", by["switch-off"]["why"])
        # While a demaster is in hand its steps say so, and offer no second start (WHY§61).
        going = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], job, deep, auto=True, going=True)["steps"]}
        self.assertEqual([(going[k]["state"], going[k]["action"]) for k in ("switch-off", "demaster", "disable")],
                         [("going", ""), ("going", ""), ("going", "")])
        # Every step says truly who does it (WHY§58): ModTrap, the owner, or ModTrap starting a tool the owner runs.
        self.assertEqual({k: v["who"] for k, v in by.items() if not k.startswith("tool:")},
                         {"dry": "ModTrap", "switch-off": "ModTrap", "demaster": "ModTrap", "disable": "ModTrap",
                          "tools-clear": "ModTrap", "mentions": "you", "health": "ModTrap", "play": "you"})

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
        self.assertEqual(out["contents"]["animations"], 3)
        self.assertIn("mentions", [x["key"] for x in out["steps"]])
        self.assertEqual(a.steps({"mods": []})["steps"], [])


if __name__ == "__main__":
    unittest.main()


class ToolEvidence(unittest.TestCase):
    """WHY§63, WHY§64: a tool is to run again only where its output carries what the mod changed, or files made
    from the mod's; holding the same record is not enough. Each tool gets one verdict. Invented plugins with real
    records: a few global variables, told apart by their value."""

    def setUp(self):
        from modtrap import probe
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")

        def pf(masters, *globs):
            recs = [probe.glob(form, "MT_%X" % (form & 0xFFFFFF), value) for form, value in globs]
            return probe.plugin_file(list(masters), [probe.group(b"GLOB", recs)], len(recs), 0x900, "invented")

        core = ("Core.esp",)
        A, B, C, D = 0x00000A00, 0x00000B00, 0x00000C00, 0x00000D00          # Core's own; 00 is Core in the others
        self.root = fx.make_instance(Path(self.tmp.name) / "List", [
            ("+", "PG Output", {"PGPatcher.esp": pf(core, (D, 1.0))}),
            ("+", "Patcher Output", {
                # carries the mod's change to A (the mod's value, 7), and Core's own B
                "Synthesis.esp": pf(core, (A, 7.0), (B, 1.0)),
                # holds A, but with a value of its own: not the mod's change
                "Synthesis Gameplay.esp": pf(core, (A, 3.0)),
                # holds B, which the mod holds too but does not change; and C with the patch's change (9)
                "Bashed Patch, 0.esp": pf(core, (B, 1.0), (C, 9.0))}),
            # a patch made for the mod: it changes C
            ("+", "Inn Patches", {"Inn - Bramble Patch.esp": pf(core + ("Bramble.esp",), (C, 9.0))}),
            # the mod: it changes A, holds B unchanged, and has a record of its own
            ("+", "Bramble", {"Bramble.esp": pf(core, (A, 7.0), (B, 1.0), (0x01000800, 5.0))}),
            ("+", "Core", {"Core.esp": pf((), (A, 1.0), (B, 1.0), (C, 1.0), (D, 1.0))}),
        ], load_order=["Core.esp", "Bramble.esp", "Inn - Bramble Patch.esp", "Synthesis.esp", "Synthesis Gameplay.esp",
                       "Bashed Patch, 0.esp", "PGPatcher.esp"],
            profile_settings="[custom_overwrites]\r\nParallaxGen=PG Output\r\n")
        mods = self.root / "mods"
        fx.write(mods / "Bramble" / "meshes" / "bramble" / "leaf.nif", b"invented")
        fx.write(mods / "PG Output" / "meshes" / "bramble" / "leaf.nif", b"made from it")
        fx.write(mods / "PG Output" / "meshes" / "quill" / "nib.nif", b"made from another mod")

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_reader_finds_records_and_their_fields(self):
        path = self.root / "mods" / "Bramble" / "Bramble.esp"
        ids, cut = plugin.record_ids(path)
        self.assertEqual((ids, cut), ({("core.esp", 0xA00), ("core.esp", 0xB00), ("bramble.esp", 0x800)}, False))
        with plugin.Records(path) as r:
            self.assertEqual([t for t, _ in r.fields(("core.esp", 0xA00))], ["EDID", "FNAM", "FLTV"])
            self.assertEqual((r.kind_of(("core.esp", 0xA00)), r.fields(("core.esp", 0x999))), ("GLOB", None))

    def test_a_tool_runs_again_only_where_its_output_carries_the_mods_changes(self):
        m = model.build(instance.load(self.root))
        # Without a dry run that told what the mod changes, no tool is judged by records: it is said to wait.
        deep = steps.look_deeper(m, ["Bramble"])
        self.assertEqual({o["plugin"]: o["judged"] for o in deep["outputs"]},
                         {"Synthesis.esp": False, "Synthesis Gameplay.esp": False, "Bashed Patch, 0.esp": False})
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        self.assertEqual(sorted(k for k in by if k.startswith("tool")),
                         ["tool:ParallaxGen (PGPatcher)", "tools-wait"])        # judged by files; and the two that wait
        self.assertEqual((by["tools-wait"]["state"], sorted(i["text"].split(":")[0] for i in by["tools-wait"]["items"])),
                         ("waiting for the dry run", ["Synthesis", "Wrye Bash"]))
        # What xEdit tells in the dry run (XE01§18): the mod changes A in its value; its patch changes C. B, which
        # the mod only holds, is not among them.
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}],
                "Inn - Bramble Patch.esp": [{"form": "02000C00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        deep = steps.look_deeper(m, ["Bramble"], told)
        got = {o["plugin"]: (o["tool"], o["shared"], o["carried"]) for o in deep["outputs"]}
        self.assertEqual(got, {"Synthesis.esp": ("Synthesis", 1, 1),            # A, with the mod's value
                               "Synthesis Gameplay.esp": ("Synthesis", 1, 0),   # A, with another value
                               "Bashed Patch, 0.esp": ("Wrye Bash", 1, 1)})     # C, with the patch's value; B does not count
        detail = next(o for o in deep["outputs"] if o["plugin"] == "Synthesis.esp")["details"]
        self.assertEqual({k: v for k, v in detail[0].items() if k != "values"},
                         {"kind": "GLOB", "owner": "core.esp", "id": "000A00", "by": ["Bramble.esp"],
                          "carried": ["FLTV"], "changed": ["FLTV"]})
        self.assertEqual([(o["tool"], o["mod"], o["files"], o["shared"], o["examples"]) for o in deep["output_files"]],
                         [("ParallaxGen (PGPatcher)", "PG Output", 3, 1, ["meshes/bramble/leaf.nif"])])
        st = steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]
        by = {x["key"]: x for x in st}
        # One verdict for each tool: none is both to run and cleared.
        cleared = {i["text"].split(":")[0] for i in by.get("tools-clear", {"items": []})["items"]}
        running = {k[5:] for k in by if k.startswith("tool:")}
        self.assertEqual((running, cleared), ({"Synthesis", "Wrye Bash", "ParallaxGen (PGPatcher)"}, set()))
        syn = by["tool:Synthesis"]
        self.assertIn("Synthesis runs its patchers", syn["why"])                # what the tool is for
        self.assertIn("Synthesis.esp holds, in 1 record(s), a value it has from the mod", syn["why"])
        # A patcher's plugin that holds a record the mod has a stake in, without the mod's bytes, is not cleared:
        # the patcher writes records in its own form, so other bytes do not show another value (WHY§73).
        self.assertIn("Synthesis Gameplay.esp holds 1 record(s) in which the mod has a stake. A patcher builds its "
                      "copy of a record from the version that wins", syn["why"])
        self.assertEqual(syn["title"], "Run Synthesis again")                   # proof in one plugin: no "to be sure"
        folds = [i["details"] for i in syn["items"] if "details" in i]
        self.assertEqual(len(folds), 2)
        self.assertIn("GLOB 000A00 of core.esp · Bramble.esp has a stake in FLTV · this plugin holds the same FLTV",
                      folds[0]["lines"])
        self.assertIn("this plugin holds none of it", folds[1]["lines"][-1])
        # What the plugin is comes first (WHY§74): its records by kind, and the mod's stakes among those kinds.
        self.assertEqual(folds[0]["lines"][:2], ["Its 2 record(s) by kind: GLOB 2",
                                                 "The mod has a stake in records of kinds this plugin works on: GLOB 2 (this plugin holds 1 of them)"])
        self.assertIn("holds 1 file(s) at the path of a file of the mod", by["tool:ParallaxGen (PGPatcher)"]["why"])

    def test_a_patcher_is_cleared_only_where_it_can_be_ruled_out(self):
        """WHY§73: with no proof either way, a patcher that holds a record the mod has a stake in is to run again,
        to be sure; a tool built on xEdit, whose bytes can be compared, is cleared by the same finding."""
        m = model.build(instance.load(self.root))
        # The mod's stake is in A only, with a value (7) no tool's plugin holds: take the proof out of Synthesis.esp.
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        deep = steps.look_deeper(m, ["Bramble"], told)
        for o in deep["outputs"]:
            if o["plugin"] == "Synthesis.esp":
                o["carried"] = 0
                for d in o["details"]:
                    d["carried"] = []
        outputs = [dict(o) for o in deep["outputs"]]
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        syn = by["tool:Synthesis"]
        self.assertEqual(syn["title"], "Run Synthesis again, to be sure")
        self.assertIn("ModTrap cannot rule it out", syn["why"])
        self.assertIn("when in doubt, run it", syn["why"])
        cleared = [i["text"] for i in by["tools-clear"]["items"]]
        self.assertTrue(any(t.startswith("Wrye Bash: Bashed Patch, 0.esp holds no record in which the mod has a stake") for t in cleared))
        self.assertIn("This is evidence, not proof", by["tools-clear"]["why"])
        # The same finding in the plugin of a tool built on xEdit clears it: its records are written as the mod's are.
        deep["outputs"] = [dict(o, tool="DynDOLOD") for o in outputs if o["plugin"] != "Bashed Patch, 0.esp"]
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        self.assertNotIn("tool:DynDOLOD", by)
        self.assertTrue(any(i["text"].startswith("DynDOLOD: Synthesis.esp holds 1 record(s) in which the mod has a stake, but none of the mod's values")
                            for i in by["tools-clear"]["items"]))

    def test_the_patcher_frameworks_own_settings_say_who_made_a_plugin_and_what_was_left_out(self):
        """TL01§14, WHY§74: the framework keeps, beside its program, which patchers make each output plugin and
        which plugins each output leaves out. A plugin made with the mod's plugin left out holds nothing of it."""
        from modtrap import toolmade
        home = Path(self.tmp.name) / "Patcher Framework"
        fx.write(home / "PipelineSettings.json", json.dumps({"Version": 2, "Profiles": [{"Nickname": "Invented", "Groups": [
            {"On": True, "Name": "Synthesis", "BlacklistedMods": [], "Patchers": [
                {"$type": "invented", "On": True, "Nickname": "Lantern Lighter", "RemoteRepoPath": "https://example.invalid/a/lantern-lighter"},
                {"$type": "invented", "On": False, "Nickname": "", "RemoteRepoPath": "https://example.invalid/a/quill-sharpener"}]},
            {"On": True, "Name": "Synthesis Gameplay", "BlacklistedMods": ["Bramble.esp", "Other.esp"], "Patchers": [
                {"$type": "invented", "On": True, "Nickname": "Inn Keeper"}]}]}]}))
        fx.write(home / "Data" / "Invented" / "Lantern Lighter" / "settings.json", '{"Skip": ["bramble.ESP"]}')
        fx.write(home / "Data" / "Invented" / "Inn Keeper" / "settings.json", '{"Skip": ["Quill.esp"]}')
        ini = self.root / "ModOrganizer.ini"
        text = ini.read_bytes().decode("utf-8")
        text = text.replace("size=1\r\n", "size=2\r\n2\\title=Synthesis\r\n2\\binary=%s\r\n2\\arguments=\r\n2\\workingDirectory=\r\n"
                            % (home / "Synthesis.exe").as_posix(), 1)
        ini.write_bytes(text.encode("utf-8"))
        m = model.build(instance.load(self.root))
        self.assertEqual(toolmade.tool_folders(m.instance, "Synthesis"), [home])
        groups = toolmade.synthesis_groups([home])
        self.assertEqual([(g["group"], [(p["name"], p["on"]) for p in g["patchers"]], g["left_out"]) for g in groups],
                         [("Synthesis", [("Lantern Lighter", True), ("quill-sharpener", False)], []),
                          ("Synthesis Gameplay", [("Inn Keeper", True)], ["Bramble.esp", "Other.esp"])])
        self.assertEqual(toolmade.group_of("Synthesis Gameplay.esp", groups)["group"], "Synthesis Gameplay")
        self.assertEqual(toolmade.group_of("Synthesis Gameplay_2.esp", groups)["group"], "Synthesis Gameplay")
        self.assertIsNone(toolmade.group_of("Bashed Patch, 0.esp", groups))
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        deep = steps.look_deeper(m, ["Bramble"], told)
        rows = {o["plugin"]: o for o in deep["outputs"]}
        self.assertEqual(rows["Synthesis Gameplay.esp"]["left_out"], ["Bramble.esp"])
        self.assertEqual(deep["tool_settings"], [{"tool": "Synthesis", "file": "Data/Invented/Lantern Lighter/settings.json", "names": ["Bramble.esp"]}])
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        syn = by["tool:Synthesis"]
        self.assertIn("a settings file of one of its patchers names the mod's plugin", syn["why"])
        self.assertIn("Synthesis Gameplay.esp was made with Bramble.esp left out", syn["why"])     # speaks against it
        lines = [ln for i in syn["items"] if "details" in i for ln in i["details"]["lines"]]
        self.assertIn("Made by the patchers of the group “Synthesis”, in order: Lantern Lighter, quill-sharpener (switched off) "
                      "(from Synthesis's own settings file)", lines)
        # And the whole modlist's account of what its tools made.
        got = toolmade.made(m)
        self.assertTrue(got["synthesis_settings"])
        table = {x["plugin"]: (x["tool"], x["records"], x["kinds"], x.get("made_by", {}).get("group")) for x in got["plugins"]}
        self.assertEqual(table["Synthesis.esp"], ("Synthesis", 2, [["GLOB", 2]], "Synthesis"))
        self.assertEqual(table["Bashed Patch, 0.esp"][:3], ("Wrye Bash", 2, [["GLOB", 2]]))

    def test_a_mod_whose_changes_no_output_carries_clears_every_tool(self):
        # Take Core's own D out of the picture: a mod that only holds a record unchanged, and changes nothing else.
        from modtrap import probe
        still = probe.plugin_file(["Core.esp"], [probe.group(b"GLOB", [probe.glob(0x00000B00, "MT_B00", 1.0)])], 1, 0x900, "invented")
        fx.write(self.root / "mods" / "Still" / "Still.esp", still)
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Core", b"+Still\r\n+Core"))
        for name in ("plugins.txt", "loadorder.txt"):
            f = self.root / "profiles" / "Default" / name
            f.write_bytes(f.read_bytes().replace(b"Bramble.esp", b"Still.esp\r\n" + (b"*" if name == "plugins.txt" else b"") + b"Bramble.esp", 1))
        m = model.build(instance.load(self.root))
        deep = steps.look_deeper(m, ["Still"], {"Still.esp": []})       # xEdit looked through it: it changes nothing
        self.assertEqual({o["plugin"]: (o["shared"], o["carried"]) for o in deep["outputs"]},
                         {"Synthesis.esp": (0, 0), "Synthesis Gameplay.esp": (0, 0), "Bashed Patch, 0.esp": (0, 0)})
        by = {x["key"]: x for x in steps.compile_steps(m, ["Still"], None, deep, auto=True)["steps"]}
        self.assertEqual([k for k in by if k.startswith("tool:")], [])
        clear = by["tools-clear"]
        self.assertEqual((clear["state"], sorted(i["text"].split(":")[0] for i in clear["items"])),
                         ("not needed", ["ParallaxGen (PGPatcher)", "Synthesis", "Wrye Bash"]))
        self.assertTrue(all(i["evidence"] for i in clear["items"]))


    def add_plugin(self, mod, name, data, before):
        """Puts one more mod with one plugin into the list, loading just before the plugin named."""
        fx.write(self.root / "mods" / mod / name, data)
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Core", b"+" + mod.encode() + b"\r\n+Core"))
        for fname in ("plugins.txt", "loadorder.txt"):
            f = self.root / "profiles" / "Default" / fname
            star = b"*" if fname == "plugins.txt" else b""
            f.write_bytes(f.read_bytes().replace(star + before.encode(), star + name.encode() + b"\r\n" + star + before.encode(), 1))

    def test_the_mods_value_in_a_tools_plugin_counts_only_if_the_whole_load_order_agrees(self):
        """WHY§76: the dry run's xEdit loads the mod, its dependants and their masters, not the whole load order. A
        plugin outside that set may have the last word on a record, or say the same as the mod."""
        from modtrap import probe
        A = 0x00000A00
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        pf = lambda value: probe.plugin_file(["Core.esp"], [probe.group(b"GLOB", [probe.glob(A, "MT_A00", value)])], 1, 0x900, "invented")
        # 1. A plugin that stays and loads after the mod has the last word on A: the tool did not build from the mod.
        self.add_plugin("Later", "Later.esp", pf(2.0), "Synthesis.esp")
        deep = steps.look_deeper(model.build(instance.load(self.root)), ["Bramble"], told)
        rows = {o["plugin"]: o for o in deep["outputs"]}
        self.assertEqual((rows["Synthesis.esp"]["shared"], rows["Synthesis.esp"]["carried"]), (0, 0))   # no stake after all
        self.assertIn("Later.esp, which loads after the mod and stays, has the last word", rows["Synthesis.esp"]["no_stake"][0]["why"])
        self.assertEqual(rows["Synthesis Gameplay.esp"]["shared"], 0)                # for every tool's plugin alike
        (self.root / "mods" / "Later" / "Later.esp").unlink()

    def test_the_next_in_line_saying_the_same_as_the_mod_is_no_trace_of_the_mod(self):
        from modtrap import probe
        A = 0x00000A00
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        same = probe.plugin_file(["Core.esp"], [probe.group(b"GLOB", [probe.glob(A, "MT_A00", 7.0)])], 1, 0x900, "invented")
        self.add_plugin("Earlier", "Earlier.esp", same, "Bramble.esp")          # says 7 too, and loads before the mod
        m = model.build(instance.load(self.root))
        deep = steps.look_deeper(m, ["Bramble"], told)
        rows = {o["plugin"]: o for o in deep["outputs"]}
        self.assertEqual((rows["Synthesis.esp"]["shared"], rows["Synthesis.esp"]["carried"]), (0, 0))
        self.assertIn("the plugin next in line, Earlier.esp, says the same there as the mod", rows["Synthesis.esp"]["no_stake"][0]["why"])
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        self.assertNotIn("tool:Synthesis", by)                                        # nothing of the mod in it: cleared
        syn = next(i for i in by["tools-clear"]["items"] if i["text"].startswith("Synthesis"))
        lines = [ln for d in syn["evidence"] for ln in d["lines"]]
        self.assertTrue(any("no stake of the mod's after all: the plugin next in line, Earlier.esp" in ln for ln in lines))

    def test_unused_bytes_of_a_cells_place_on_the_grid_do_not_count(self):
        """TL01§15: the last three bytes of XCLC are unused and hold what happened to be in memory; an older plugin
        has no flags at all."""
        new, other, old = b"\x09\x00\x00\x00\xfc\xff\xff\xff\x00\x11\x22\x33", b"\x09\x00\x00\x00\xfc\xff\xff\xff\x00\xaa\xbb\xcc", b"\x09\x00\x00\x00\xfc\xff\xff\xff"
        self.assertEqual(plugin.canonical("XCLC", new), plugin.canonical("XCLC", other))
        self.assertEqual(plugin.canonical("XCLC", new), plugin.canonical("XCLC", old))
        self.assertNotEqual(plugin.canonical("XCLC", new), plugin.canonical("XCLC", new[:8] + b"\x01" + new[9:]))   # a flag counts
        self.assertEqual(plugin.canonical("FLTV", new), new)                          # any other field: as it is

    def test_a_field_that_differs_only_in_what_does_not_count_is_no_stake_anywhere(self):
        """WHY§78: xEdit names a field whose bytes differ in nothing that counts (unused bytes). ModTrap's own
        comparison then finds no difference from the mod's master, and must not count the field for all that: the
        tool's plugin holding the same bytes as the mod is no trace of the mod."""
        from unittest import mock
        m = model.build(instance.load(self.root))
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        with mock.patch.object(plugin, "canonical", lambda t, b: b"" if t == "FLTV" else b):    # as if all of it were unused
            deep = steps.look_deeper(m, ["Bramble"], told)
        rows = {o["plugin"]: o for o in deep["outputs"]}
        self.assertEqual((rows["Synthesis.esp"]["shared"], rows["Synthesis.esp"]["carried"]), (0, 0))
        self.assertIn("says the same there as the mod", rows["Synthesis.esp"]["no_stake"][0]["why"])

    def test_the_evidence_shows_what_each_plugin_says(self):
        m = model.build(instance.load(self.root))
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        deep = steps.look_deeper(m, ["Bramble"], told)
        vals = next(o for o in deep["outputs"] if o["plugin"] == "Synthesis.esp")["details"][0]["values"]
        self.assertEqual(vals, [{"field": "FLTV", "mod": "00 00 E0 40", "tool": "00 00 E0 40", "next": "00 00 80 3F", "next_by": "Core.esp"}])
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        lines = [ln for i in by["tool:Synthesis"]["items"] if "details" in i for ln in i["details"]["lines"]]
        self.assertIn("    FLTV · the mod: 00 00 E0 40 · this plugin: 00 00 E0 40 · next in line (Core.esp): 00 00 80 3F", lines)
        self.assertEqual(steps.show_field("XCLC", b"\x09\x00\x00\x00\xfc\xff\xff\xff\x05\x11\x22\x33"), "cell (9, -4), land flags 0x05")
        self.assertEqual(steps.show_field("XCLC", b"\x09\x00\x00\x00\xfc\xff\xff\xff"), "cell (9, -4), land flags none")
        self.assertEqual(steps.show_field("FULL", b"x" * 40), "40 bytes")

    def test_a_tools_plugin_that_named_the_mod_is_proof(self):
        """WHY§77: ModTrap's demastered copy of a plugin a tool made, in ModTrap's own mod: the tool made it from the
        mod's own records, and makes it anew."""
        m = model.build(instance.load(self.root))
        told = {"Bramble.esp": [{"form": "02000A00", "kind": "GLOB", "owner": "Core.esp", "fields": ["FLTV"]}]}
        deep = steps.look_deeper(m, ["Bramble"], told)
        deep["outputs"] = [dict(o, mod="ModTrap - Bramble", carried=0, shared=0, details=[]) if o["plugin"] == "Synthesis Gameplay.esp"
                           else dict(o, carried=0, shared=0, details=[]) for o in deep["outputs"] if o["tool"] == "Synthesis"]
        by = {x["key"]: x for x in steps.compile_steps(m, ["Bramble"], None, deep, auto=True)["steps"]}
        syn = by["tool:Synthesis"]
        self.assertEqual(syn["title"], "Run Synthesis again")
        self.assertIn("Synthesis Gameplay.esp named the mod as a master", syn["why"])
        self.assertIn("ModTrap's copy in “ModTrap - Bramble” then hides the new one", syn["why"])

    def test_only_groups_that_can_hold_a_wanted_kind_are_read(self):
        from modtrap import probe
        data = probe.plugin_file([], [probe.group(b"GLOB", [probe.glob(0x800, "MT_One", 1.0)]),
                                      probe.group(b"MATT", [probe.matt(0x801, "MT_Two", "Two")])], 2, 0x900, "invented")
        f = fx.write(self.root / "mods" / "Core" / "Two Kinds.esp", data) or self.root / "mods" / "Core" / "Two Kinds.esp"
        with plugin.Records(self.root / "mods" / "Core" / "Two Kinds.esp") as r:
            self.assertEqual(sorted(v[3] for v in r.index.values()), ["GLOB", "MATT"])
        with plugin.Records(self.root / "mods" / "Core" / "Two Kinds.esp", kinds=frozenset(("MATT",))) as r:
            self.assertEqual([v[3] for v in r.index.values()], ["MATT"])
        self.assertTrue(plugin._skip_group(int.from_bytes(b"CELL", "little"), 0, frozenset(("GLOB",))))
        self.assertFalse(plugin._skip_group(int.from_bytes(b"WRLD", "little"), 0, frozenset(("CELL",))))
        self.assertTrue(plugin._skip_group(0, 9, frozenset(("CELL",))))            # what is in a cell, when only cells are wanted
        self.assertFalse(plugin._skip_group(0, 9, frozenset(("REFR",))))


class PointersAcrossPlugins(unittest.TestCase):
    """WHY§65: two plugins write the same pointer differently when their master lists differ. Comparing bytes
    called a patch's untouched list "changed" and a tool's copy of it "the mod's". Invented plugins, each with the
    game's first file as its first master, as real plugins have: a form list that points at a global of Core."""

    def setUp(self):
        from modtrap import probe
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        G, H, L = 0xA00, 0xB00, 0xC00                       # Core's two globals and its list, by their ids there
        sky = "Skyrim.esm"

        def lst(masters, core_at, *points):
            """A plugin holding Core's list; `core_at` is Core's place among its masters, each point (place, id)."""
            recs = [probe.flst(core_at << 24 | L, "MT_List", [at << 24 | ident for at, ident in points])]
            return probe.plugin_file(list(masters), [probe.group(b"FLST", recs)], 1, 0x900, "invented")

        core = probe.plugin_file([sky], [                    # in Core itself, its own records are numbered 01
            probe.group(b"GLOB", [probe.glob(1 << 24 | G, "MT_G", 1.0), probe.glob(1 << 24 | H, "MT_H", 2.0)]),
            probe.group(b"FLST", [probe.flst(1 << 24 | L, "MT_List", [1 << 24 | G])])], 3, 0x900, "invented")
        other = probe.plugin_file([sky], [probe.group(b"GLOB", [probe.glob(1 << 24 | H, "MT_OtherH", 9.0)])], 1, 0x900, "invented")
        wide = (sky, "Other.esp", "Core.esp")                # here Other is 01 and Core is 02
        self.root = fx.make_instance(Path(self.tmp.name) / "List", [
            ("+", "Patcher Output", {
                # holds the list as Core has it, written in its own numbering (Core's G as 02...)
                "Synthesis.esp": lst(wide, 2, (2, G)),
                # holds the mod's real change, Core's H, written in its own numbering
                "Synthesis Gameplay.esp": lst(wide, 2, (2, H)),
                # the very bytes the mod wrote (01...), but here 01 is Other: it points at Other's record
                "Bashed Patch, 0.esp": lst(wide, 2, (1, H))}),
            # a patch for the mod that holds the list untouched, in the wide numbering
            ("+", "Inn Patches", {"Inn - Bramble Patch.esp": lst(wide + ("Bramble.esp",), 2, (2, G))}),
            # the mod: it makes the list point at Core's H (Core is 01 here)
            ("+", "Bramble", {"Bramble.esp": lst((sky, "Core.esp"), 1, (1, H))}),
            ("+", "Other", {"Other.esp": other}),
            ("+", "Core", {"Core.esp": core}),
        ], load_order=["Core.esp", "Other.esp", "Bramble.esp", "Inn - Bramble Patch.esp", "Synthesis.esp",
                       "Synthesis Gameplay.esp", "Bashed Patch, 0.esp"])

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_same_pointer_written_two_ways_is_the_same(self):
        mods = self.root / "mods"
        key = ("core.esp", 0xC00)
        with plugin.Records(mods / "Core" / "Core.esp") as core, \
                plugin.Records(mods / "Inn Patches" / "Inn - Bramble Patch.esp") as patch, \
                plugin.Records(mods / "Bramble" / "Bramble.esp") as mod, \
                plugin.Records(mods / "Patcher Output" / "Synthesis Gameplay.esp") as carries, \
                plugin.Records(mods / "Patcher Output" / "Bashed Patch, 0.esp") as lookalike:
            point = lambda r: dict(r.fields(key))["LNAM"]            # noqa: E731
            self.assertNotEqual(point(core), point(patch))           # other bytes ...
            self.assertTrue(plugin.same_field(point(core), core, point(patch), patch))       # ... the same record
            self.assertFalse(plugin.same_field(point(core), core, point(mod), mod))          # the mod's real change
            self.assertNotEqual(point(mod), point(carries))
            self.assertTrue(plugin.same_field(point(mod), mod, point(carries), carries))     # carried, in other bytes
            self.assertEqual(point(mod), point(lookalike))           # the same bytes ...
            self.assertFalse(plugin.same_field(point(mod), mod, point(lookalike), lookalike))    # ... another record
            name = lambda r: dict(r.fields(key))["EDID"]             # noqa: E731
            self.assertTrue(plugin.same_field(name(core), core, name(carries), carries))     # plain values: as written

    def test_only_a_real_change_that_is_really_carried_counts(self):
        m = model.build(instance.load(self.root))
        # As xEdit tells it: the mod changes where the list points; the patch, which holds it untouched, nothing.
        told = {"Bramble.esp": [{"form": "01000C00", "kind": "FLST", "owner": "Core.esp", "fields": ["LNAM"]}],
                "Inn - Bramble Patch.esp": []}
        deep = steps.look_deeper(m, ["Bramble"], told)
        self.assertEqual({o["plugin"]: (o["shared"], o["carried"]) for o in deep["outputs"]},
                         {"Synthesis.esp": (1, 0),                   # holds the list, without the mod's change
                          "Synthesis Gameplay.esp": (1, 1),          # carries it
                          "Bashed Patch, 0.esp": (1, 0)})            # the mod's bytes, pointing elsewhere: not it
        by = [d["by"] for o in deep["outputs"] for d in o["details"]]
        self.assertEqual(by, [["Bramble.esp"]] * 3)                  # the untouched patch changed nothing
