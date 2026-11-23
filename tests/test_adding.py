"""Adding mods (MT21, DESIGN§16): what the read-only analysis tells, on an invented modlist."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import adding, api, instance, logbook, model, plugin
from modtrap.server import Bad

from ._fixtures import make_instance, write

b = plugin.build
SKY = "Skyrim.esm"


def invented(root: Path) -> Path:
    """Quill and Lantern are the list's ordinary mods; an invented patcher's output sits last, under its own
    separator. Thistle is installed but disabled: the mod to add. Three more disabled mods try the needs."""
    make_instance(root, [
        ("+", "Tool Output", {"Generated.esp": b((SKY, "Quill.esp"), kinds=("NPC_", "ARMO")), "textures/shared/a.dds": b"made"}),
        ("+", "Outputs_separator", {}),
        ("-", "Thistle", {"Thistle.esp": b((SKY, "Quill.esp"), kinds=("NPC_", "QUST")), "textures/shared/a.dds": b"new",
                          "textures/shared/b.dds": b"new", "scripts/quill.pex": b"new",
                          "meta.ini": b"[General]\r\ngameName=SkyrimSE\r\ninstallationFile=Thistle-123-1-0-1700000000.7z\r\n"}),
        ("-", "Needs Absent", {"NeedsAbsent.esp": b((SKY, "Nowhere.esp"))}),
        ("-", "Needs Dormant", {"NeedsDormant.esp": b((SKY, "Dormant.esp"))}),
        ("-", "Dormant", {"Dormant.esp": b((SKY,), version=1.71)}),
        ("-", "Beacon", {"Beacon.esm": b((SKY,), flags=plugin.FLAG_ESM)}),
        ("+", "Quill", {"Quill.esp": b((SKY,)), "textures/shared/a.dds": b"old", "scripts/quill.pex": b"old",
                        "textures/quill/only.dds": b"old"}),
        ("+", "Lantern", {"Lantern.esm": b((SKY,), flags=plugin.FLAG_ESM)}),
    ], load_order=["Lantern.esm", "Quill.esp", "Generated.esp"],
        profile_settings="[custom_overwrites]\r\nInvented%20Patcher=Tool Output\r\n")
    write(root / "downloads" / "Unpacked Later.7z", b"not an archive")
    return root


class Adding(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = invented(Path(self.tmp.name))
        self.inst = instance.load(self.root)
        self.m = model.build(self.inst)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def one(self, name: str) -> dict:
        return adding.analyse(self.m, [name])

    def step(self, rep: dict, key: str) -> dict:
        return next(s for s in rep["steps"] if s["key"] == key)

    # --- what was dropped -----------------------------------------------------------------------------------------

    def test_a_dropped_thing_is_found_by_its_name_alone(self) -> None:
        got = adding.resolve(self.inst, [
            {"name": "thistle"},                                   # the mod's folder
            {"name": "Thistle-123-1-0-1700000000.7z"},             # the archive MO2 installed it from
            {"name": "Dormant-55-2-1.zip"},                        # an archive named like a mod
            {"name": "Unpacked Later.7z"},                         # downloaded, not installed
            {"name": "Never Heard Of.rar"},
        ])
        self.assertEqual([g["mods"] for g in got], [["Thistle"], ["Thistle"], ["Dormant"], [], []])
        self.assertEqual([g["sure"] for g in got], [True, True, False, False, False])
        self.assertTrue(got[3]["downloaded"])
        self.assertIn("Downloads", got[3]["how"])
        self.assertFalse(got[4]["downloaded"])

    # --- where it goes --------------------------------------------------------------------------------------------

    def test_the_mod_goes_after_the_ordinary_mods_and_before_the_tools_output(self) -> None:
        rep = self.one("Thistle")
        self.assertEqual(rep["place"]["before"], "Outputs_separator")
        self.assertEqual([o["mod"] for o in rep["place"]["outputs"]], ["Tool Output"])
        self.assertIn("“Outputs” heading", rep["place"]["outputs"][0]["why"])
        self.assertEqual(rep["place"]["heading"], "Outputs_separator")
        self.assertEqual(rep["place"]["after"], "Needs Absent")       # disabled mods say nothing either way

    def test_a_list_that_keeps_more_after_its_outputs(self) -> None:
        """As a large curated list is laid out: an "Outputs" heading in the middle, with the tools' outputs and a
        few things of unknown making under it, and sections of options after it. The new mod goes right before the
        heading; its plugin before everything the list keeps among its outputs."""
        with tempfile.TemporaryDirectory() as d:
            root = make_instance(Path(d), [
                ("-", "Not Yet Installed_separator", {}),
                ("+", "A Shader Option", {"textures/shared/a.dds": b"option"}),
                ("-", "Shader Options_separator", {}),
                ("+", "List - Tool Output", {"Made One.esp": b((SKY, "Quill.esp"), kinds=("NPC_",)), "Made Two.esp": b((SKY,))}),
                ("+", "Randomised Loot", {"Randomised Loot.esp": b((SKY,))}),          # no tool known for it
                ("+", "List - Merge", {"List - Merge.esp": b((SKY, "Quill.esp"))}),
                ("+", "Outputs_separator", {}),
                ("+", "List - Late Loaders", {"List - Late Loaders.esp": b((SKY, "Quill.esp"))}),
                ("-", "Patches_separator", {}),
                ("-", "Thistle", {"Thistle.esp": b((SKY, "Quill.esp"), kinds=("NPC_",)), "textures/shared/a.dds": b"new"}),
                ("+", "Quill", {"Quill.esp": b((SKY,)), "textures/shared/a.dds": b"old"}),
            ], load_order=["Quill.esp", "List - Late Loaders.esp", "List - Merge.esp", "Made One.esp", "Randomised Loot.esp",
                           "Made Two.esp"],
                profile_settings="[custom_overwrites]\r\nInvented%20Patcher=List - Tool Output\r\n")
            m = model.build(instance.load(root))
            rep = adding.analyse(m, ["Thistle"])
        place = rep["place"]
        self.assertEqual((place["before"], place["after"], place["heading"]),
                         ("Outputs_separator", "List - Late Loaders", "Outputs_separator"))
        self.assertEqual(sorted(o["mod"] for o in place["outputs"]), ["List - Merge", "List - Tool Output", "Randomised Loot"])
        p = rep["mods"][0]["plugins"][0]
        self.assertEqual(p["proposed"]["before"], "List - Merge.esp")
        self.assertEqual(p["proposed"]["stay_after"], ["List - Merge.esp", "Made One.esp", "Randomised Loot.esp", "Made Two.esp"])
        x = rep["mods"][0]
        self.assertEqual([c["mod"] for c in x["wins"]], ["Quill"])
        self.assertEqual([c["mod"] for c in x["loses"]], ["A Shader Option"])          # what the list keeps after its outputs
        self.assertIn("“Outputs”", next(s for s in rep["steps"] if s["key"] == "enable")["note"])
        # Only the tool that is known is asked to run again.
        self.assertEqual([t["tool"] for t in rep["tools"]], ["Invented Patcher"])

    def test_a_few_plugins_of_unknown_making_among_the_outputs_do_not_end_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_instance(Path(d), [
                ("+", "Tool Output", {"Made One.esp": b((SKY,)), "Made Two.esp": b((SKY,))}),
                ("+", "Unknown", {"Unknown A.esp": b((SKY,)), "Unknown B.esp": b((SKY,)), "Unknown C.esp": b((SKY,)),
                                  "Unknown D.esp": b((SKY,))}),
                ("-", "Thistle", {"Thistle.esp": b((SKY,))}),
            ], load_order=["Unknown A.esp", "Unknown B.esp", "Unknown C.esp", "Made One.esp", "Unknown D.esp", "Made Two.esp"],
                profile_settings="[custom_overwrites]\r\nInvented%20Patcher=Tool Output\r\n")
            rep = adding.analyse(model.build(instance.load(root)), ["Thistle"])
        p = rep["mods"][0]["plugins"][0]["proposed"]
        self.assertEqual((p["before"], p["stay_after"]), ("Made One.esp", ["Made One.esp", "Unknown D.esp", "Made Two.esp"]))

    def test_its_plugin_goes_after_its_masters_and_before_the_generated_plugins(self) -> None:
        p = self.one("Thistle")["mods"][0]["plugins"][0]
        self.assertEqual(p["proposed"]["before"], "Generated.esp")
        self.assertEqual(p["proposed"]["stay_after"], ["Generated.esp"])
        self.assertEqual([(x["name"], x["state"]) for x in p["masters"]], [(SKY, "active"), ("Quill.esp", "active")])
        self.assertFalse(p["active"])

    def test_a_master_flagged_plugin_goes_to_the_end_of_the_masters_block(self) -> None:
        p = self.one("Beacon")["mods"][0]["plugins"][0]
        self.assertEqual(p["proposed"]["before"], "Quill.esp")
        self.assertIn("masters' block", p["proposed"]["why"])

    def test_with_no_output_it_all_goes_last(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = make_instance(Path(d), [("-", "Thistle", {"Thistle.esp": b((SKY,))}),
                                           ("+", "Quill", {"Quill.esp": b((SKY,))})], load_order=["Quill.esp"])
            rep = adding.analyse(model.build(instance.load(root)), ["Thistle"])
        self.assertEqual((rep["place"]["before"], rep["place"]["after"]), ("", "Quill"))
        self.assertEqual(rep["mods"][0]["plugins"][0]["proposed"]["before"], "")
        self.assertIn("goes last", self.step(rep, "enable")["note"])

    # --- what it needs --------------------------------------------------------------------------------------------

    def test_a_master_nobody_has_is_named(self) -> None:
        rep = self.one("Needs Absent")
        needs = self.step(rep, "needs")
        self.assertEqual(needs["state"], "to do")
        self.assertIn("Nowhere.esp", needs["items"][0]["text"])
        self.assertEqual(self.step(rep, "enable")["state"], "waiting")

    def test_a_master_in_a_disabled_mod_names_that_mod(self) -> None:
        rep = self.one("Needs Dormant")
        item = self.step(rep, "needs")["items"][0]
        self.assertEqual(item["mod"], "Dormant")
        both = adding.analyse(self.m, ["Needs Dormant", "Dormant"])
        self.assertEqual(self.step(both, "needs")["state"], "done")
        master = both["mods"][0]["plugins"][0]["masters"][1]
        self.assertEqual((master["state"], master["mod"]), ("comes along", "Dormant"))
        texts = [i["text"] for i in self.step(both, "activate")["items"]]
        self.assertLess(next(i for i, t in enumerate(texts) if t.startswith("Dormant.esp")),
                        next(i for i, t in enumerate(texts) if t.startswith("NeedsDormant.esp")))

    def test_the_newer_header_format_is_said(self) -> None:
        notes = self.one("Dormant")["mods"][0]["plugins"][0]["notes"]
        self.assertTrue(any("1.71" in n for n in notes))
        self.assertEqual(self.one("Thistle")["mods"][0]["plugins"][0]["notes"], [])

    def test_room_in_the_load_order_is_counted(self) -> None:
        rep = self.one("Thistle")
        self.assertEqual(rep["slots"]["full"], {"now": 8, "after": 9, "limit": 254})   # the game's 5, and 3 of the list
        old = adding.FULL_SLOTS
        adding.FULL_SLOTS = 8
        try:
            rep = self.one("Thistle")
        finally:
            adding.FULL_SLOTS = old
        self.assertTrue(any(i["tag"] == "no room" for i in self.step(rep, "needs")["items"]))

    # --- shared files ---------------------------------------------------------------------------------------------

    def test_shared_files_are_split_into_won_and_lost(self) -> None:
        x = self.one("Thistle")["mods"][0]
        self.assertEqual([(c["mod"], c["files"]) for c in x["wins"]], [("Quill", 2)])
        self.assertEqual(x["wins"][0]["kinds"], {"textures": 1, "scripts": 1})
        self.assertEqual(x["wins"][0]["notable"], ["scripts"])
        self.assertEqual([(c["mod"], c["files"]) for c in x["loses"]], [("Tool Output", 1)])
        self.assertTrue(x["loses"][0]["output"])

    def test_the_files_step_names_what_goes_wrong_quietly(self) -> None:
        files = self.step(self.one("Thistle"), "files")
        self.assertEqual((files["manual"], files["state"]), (False, "done"))            # told, not asked (MT53)
        texts = [i["text"] for i in files["items"]]
        self.assertTrue(texts[0].startswith("overwrites “Quill” in 2 file(s):"), texts)
        self.assertIn("scripts", [i["tag"] for i in files["items"]])
        self.assertTrue(any(t.startswith("is overwritten by “Tool Output” in 1 file(s)") and "a tool made that mod's files" in t for t in texts), texts)
        self.assertEqual(files["note"], "Placed last, before the tools' outputs, it overwrites 2 file(s) of other mods and 1 of its own are overwritten.")

    def test_only_shared_folders_are_entered(self) -> None:
        trie = adding._trie(["textures/shared/a.dds", "Thistle.esp"])
        found, cut = adding.shared_files(self.inst.mod("Quill").folder, trie, time.monotonic() + 5)
        self.assertEqual((found, cut), (["textures/shared/a.dds"], False))
        found, cut = adding.shared_files(self.inst.mod("Quill").folder, trie, time.monotonic() - 1)
        self.assertTrue(cut)

    def test_a_plugin_another_mod_also_has_is_said(self) -> None:
        write(self.root / "mods" / "Thistle" / "Quill.esp", b((SKY,)))
        m = model.build(instance.load(self.root))
        rep = adding.analyse(m, ["Thistle"])
        p = next(p for p in rep["mods"][0]["plugins"] if p["name"] == "Quill.esp")
        self.assertEqual((p["replaces"]["mod"], p["replaces"]["dependants"]), ("Quill", 1))
        self.assertIn("same plugin", [i["tag"] for i in self.step(rep, "files")["items"]])

    # --- tools, and the steps -------------------------------------------------------------------------------------

    def test_the_tool_whose_output_is_now_stale_is_named(self) -> None:
        rep = self.one("Thistle")
        self.assertEqual([(t["tool"], t["plugins"], t["records"]) for t in rep["tools"]], [("Invented Patcher", ["Generated.esp"], ["NPC_"])])
        st = self.step(rep, "tools")
        self.assertEqual((st["manual"], st["state"]), (False, "done"))                  # named, never a step to tick (MT53)
        self.assertIn("its output (Generated.esp) holds records of kinds this mod's plugin also has: NPC_", st["items"][0]["text"])

    def test_a_tool_whose_output_holds_other_kinds_of_records_has_nothing_to_do_with_the_mod(self) -> None:
        """MT53: a plugin of quests and spells does not send a patcher of characters and armour running."""
        write(self.root / "mods" / "Thistle" / "Thistle.esp", b((SKY, "Quill.esp"), kinds=("QUST", "SPEL", "MGEF")))
        rep = self.one("Thistle")
        self.assertEqual(rep["tools"], [])
        self.assertEqual(self.step(rep, "tools")["note"], "None of the modlist's tools builds from anything this mod brings.")
        # A plugin whose records cannot be read counts for the tool, to be on the safe side.
        write(self.root / "mods" / "Thistle" / "Thistle.esp", b"not a plugin at all")
        self.assertEqual([t["tool"] for t in adding.run_again(model.build(instance.load(self.root)), {}, 1, {}, {"?"})], ["Invented Patcher"])

    def test_a_mod_without_plugins_does_not_send_a_plugin_patcher_running(self) -> None:
        write(self.root / "mods" / "Paint" / "textures" / "quill" / "only.dds", b"new")
        rep = adding.analyse(model.build(instance.load(self.root)), ["Paint"])
        self.assertEqual(rep["tools"], [])
        self.assertEqual([s["key"] for s in rep["steps"]], ["needs", "enable", "files", "tools", "health"])
        self.assertEqual(self.step(rep, "files")["state"], "done")

    def test_a_place_chosen_by_hand_is_judged_there(self) -> None:
        """MT53: the owner names the entry the new mod goes before; what it overwrites, and what overwrites it, is
        told for that place."""
        m = model.build(instance.load(self.root))
        last = adding.analyse(m, ["Thistle"])
        self.assertEqual((last["place"]["chosen"], last["place"]["before"]), (False, "Outputs_separator"))
        self.assertEqual([c["mod"] for c in last["mods"][0]["wins"]], ["Quill"])                      # placed last, it wins over Quill
        rep = adding.analyse(m, ["Thistle"], before="Quill")
        place = rep["place"]
        self.assertEqual((place["chosen"], place["before"], place["priority"]), (True, "Quill", m.instance.mod("Quill").priority))
        x = rep["mods"][0]
        self.assertEqual(x["wins"], [])
        self.assertEqual(sorted(c["mod"] for c in x["loses"]), ["Quill", "Tool Output"])               # before Quill, Quill wins
        self.assertIn("The place you chose: directly before “Quill” in MO2's list.", self.step(rep, "enable")["why"])
        self.assertTrue(self.step(rep, "files")["note"].startswith("Where you put it, it overwrites 0 file(s)"))
        rep = adding.analyse(m, ["Thistle"], before=adding.LAST)
        self.assertEqual((rep["place"]["chosen"], rep["place"]["before"]), (True, ""))
        self.assertEqual(sorted(c["mod"] for c in rep["mods"][0]["wins"]), ["Quill", "Tool Output"])  # last of all, it wins over the tools' output too
        # A name that is no entry of the list leaves the place where ModTrap would put it.
        self.assertFalse(adding.analyse(m, ["Thistle"], before="No Such Mod")["place"]["chosen"])

    def test_what_a_sites_file_name_says_of_the_mod(self) -> None:
        f = adding.from_archive_name
        self.assertEqual(f("Thistle Main 4321 1.3.1 2026-11-22T06-39Z Ab1InventedX.zip"), {"stem": "Thistle Main", "mod_id": 4321, "version": "1.3.1", "code": "Ab1InventedX"})
        self.assertEqual(f("Thistle Main 4321 1.3.1 2026-11-22T06-39Z Ab1InventedX(2).zip")["stem"], "Thistle Main")
        self.assertEqual(f("Thistle-123-1-0-1700000000.7z"), {"stem": "Thistle", "mod_id": 123, "version": "1.0", "code": ""})
        self.assertEqual(f("Just A Mod (1).zip"), {"stem": "Just A Mod", "mod_id": 0, "version": "", "code": ""})
        self.assertEqual(f("Plain.rar")["stem"], "Plain")

    def test_the_kinds_of_records_a_plugin_holds_are_read_from_its_groups(self) -> None:
        path = write(self.root / "kinds.esp", b((SKY,), kinds=("NPC_", "QUST", "WRLD")))
        self.assertEqual(plugin.groups(path), frozenset({"NPC_", "QUST", "WRLD"}))
        self.assertEqual(plugin.groups(write(self.root / "none.esp", b((SKY,)))), frozenset())
        with self.assertRaises(plugin.Unreadable):
            plugin.groups(write(self.root / "bad.esp", b"not a plugin"))

    def test_the_steps_in_order(self) -> None:
        rep = self.one("Thistle")
        self.assertEqual([s["key"] for s in rep["steps"]],
                         ["needs", "enable", "activate", "files", "records", "tools", "health"])
        self.assertFalse(any(s["manual"] for s in rep["steps"]))                        # nothing is ticked by hand (MT53)
        self.assertEqual([s["state"] for s in rep["steps"][:3]], ["done", "to do", "waiting"])
        self.assertFalse(rep["complete"])

    def test_a_mod_already_in_shows_its_steps_done(self) -> None:
        rep = self.one("Quill")
        self.assertEqual([self.step(rep, k)["state"] for k in ("needs", "enable", "activate", "health")], ["done"] * 4)
        self.assertEqual(rep["slots"]["full"]["after"], rep["slots"]["full"]["now"])
        self.assertEqual([c["mod"] for c in rep["mods"][0]["loses"]], ["Tool Output"])

    def test_nothing_is_written(self) -> None:
        def snapshot() -> dict:
            return {p.relative_to(self.root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                    for p in self.root.rglob("*") if p.is_file()}
        before = snapshot()
        adding.analyse(self.m, ["Thistle", "Dormant", "Needs Absent"])
        adding.resolve(self.inst, [{"name": "Whatever.7z"}])
        self.assertEqual(snapshot(), before)


class AddingThroughThePage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = invented(Path(self.tmp.name) / "list")
        logbook.set_console(False)
        logbook.clear()
        self.old = os.environ.get("MODTRAP_HOME")
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.api = api.Api()
        self.api.open(str(self.root), wait=True)

    def tearDown(self) -> None:
        if self.old is None:
            os.environ.pop("MODTRAP_HOME", None)
        else:
            os.environ["MODTRAP_HOME"] = self.old
        self.tmp.cleanup()
        logbook.set_console(True)

    def analysed(self, mods: list[str]) -> dict:
        for _ in range(200):
            code, got, _after = self.api.post("/api/add", {"mods": mods})
            self.assertEqual(code, 200)
            if not got["looking"]:
                return got
            time.sleep(0.02)
        self.fail("the analysis did not end")

    def test_the_analysis_arrives_off_the_request(self) -> None:
        got = self.analysed(["Thistle"])
        self.assertEqual([x["name"] for x in got["mods"]], ["Thistle"])
        self.assertEqual(got["steps"][0]["key"], "needs")
        self.assertEqual(self.api.post("/api/add", {"mods": []})[1]["mods"], [])

    def test_a_drop_is_resolved_by_name(self) -> None:
        code, got, _after = self.api.post("/api/add/resolve", {"items": [{"name": "Thistle-123-1-0-1700000000.7z"},
                                                                         {"name": "Quill"}]})
        self.assertEqual([i["mods"] for i in got["items"]], [["Thistle"], ["Quill"]])

    def test_what_is_not_a_list_of_names_is_refused(self) -> None:
        for body in ({}, {"items": []}, {"items": ["Thistle"]}, {"items": [{"name": "x" * 301}]}):
            with self.assertRaises(Bad):
                self.api.post("/api/add/resolve", body)
        for body in ({}, {"mods": "Thistle"}, {"mods": [""]}, {"mods": ["x"] * 21}):
            with self.assertRaises(Bad):
                self.api.post("/api/add", body)


if __name__ == "__main__":
    unittest.main()
