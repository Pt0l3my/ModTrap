"""Dropping a mod's archive on ModTrap (MT21, DESIGN§16.1): taken in, unpacked in ModTrap's own folder, analysed
there; the modlist is not touched."""

from __future__ import annotations

import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path

from modtrap import api, logbook, plugin, server
from modtrap.server import Bad

from ._fixtures import write
from .test_adding import SKY, invented
from .test_unpack import zipped

NEW_MOD = {"Heather 2.1/Heather.esp": plugin.build((SKY, "Quill.esp")),
           "Heather 2.1/textures/shared/a.dds": b"newer", "Heather 2.1/readme.txt": b"words"}


FOMOD_XML = """<config><moduleName>Heather</moduleName>
<requiredInstallFiles><file source="Core\\Heather.esp" destination="Heather.esp"/></requiredInstallFiles>
<installSteps order="Explicit"><installStep name="Colour"><optionalFileGroups>
<group name="Pick a colour" type="SelectExactlyOne"><plugins order="Explicit">
<plugin name="Purple"><description>Purple.</description><files><folder source="Purple" destination=""/></files>
<typeDescriptor><type name="Recommended"/></typeDescriptor></plugin>
<plugin name="White"><description>White.</description><files><folder source="White" destination=""/></files>
<typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
</plugins></group></optionalFileGroups></installStep></installSteps></config>"""


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


class Intake(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        self.api = api.Api()
        self.api.open(str(self.root), wait=True)
        self.before = snapshot(self.root)

    def tearDown(self) -> None:
        for _ in range(300):                                  # an unpacking still going would write into the folder
            if not any(r["state"] in ("copying", "unpacking") for r in self.api._staged.values()):
                break
            time.sleep(0.02)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def drop(self, name: str, data: bytes) -> dict:
        return self.api.upload(name, len(data), io.BytesIO(data))

    def settled(self, mods: list[str], ids: list[str]) -> dict:
        for _ in range(300):
            got = self.api.post("/api/add", {"mods": mods, "staged": ids})[1]
            if not got["looking"] and not got["unpacking"]:
                return got
            time.sleep(0.02)
        self.fail("it never settled")

    def test_a_name_is_taken_only_by_a_mod_of_the_modlist_or_one_still_to_be_installed(self) -> None:
        """MT79: a mod installed through ModTrap and since taken out of the modlist left its record in ModTrap's
        work folder; the record held the name, and the mod installed again was called "(2)"."""
        first = self.drop("Heather-4711-2-1-1700000000.zip", zipped(NEW_MOD))
        self.settled([], [first["id"]])
        self.assertEqual(first["name"], "Heather 2.1")
        twin = self.drop("Heather-4711-2-1-1700000000.zip", zipped(NEW_MOD))       # while the first still waits: two cannot have one name
        self.assertEqual(twin["name"], "Heather 2.1 (2)")
        self.settled([], [twin["id"]])
        self.api.post("/api/add/forget", {"id": twin["id"]})
        self.api._staged[first["id"]]["state"] = "installed"                        # it went into MO2, and was taken out of MO2 again since
        again = self.drop("Heather-4711-2-1-1700000000.zip", zipped(NEW_MOD))
        self.assertEqual(again["name"], "Heather 2.1")                              # no mod of that name anywhere: the name is free
        self.settled([], [again["id"]])
        self.assertEqual(self.api.post("/api/add/name", {"id": again["id"], "name": "Heather"})[1]["name"], "Heather")
        failed = self.drop("Heather-4711-2-1-1700000001.zip", b"PK\x03\x04 not a whole zip")
        for _ in range(200):
            if self.api._staged[failed["id"]]["state"] == "failed":
                break
            time.sleep(0.02)
        other = self.drop("Heather-4711-2-1-1700000002.zip", zipped(NEW_MOD))       # a record that failed holds no name either
        self.assertEqual(other["name"], "Heather 2.1")
        self.settled([], [other["id"]])

    def test_the_bulk_installer_asks_how_any_number_of_archives_stand(self) -> None:
        """MT78: no limit of twenty, and no analysis."""
        ids = []
        for i in range(25):
            rec = self.drop("Sprig %d-%d-1-0-17000000%02d.zip" % (i, 7000 + i, i), zipped({"Sprig%d.esp" % i: plugin.build((SKY,))}))
            ids.append(rec["id"])
        for _ in range(400):
            got = self.api.post("/api/add/status", {"staged": ids + ["0000000000"]})[1]
            if all(r["state"] == "ready" for r in got["staged"]):
                break
            time.sleep(0.02)
        self.assertEqual((len(got["staged"]), got["gone"]), (25, ["0000000000"]))
        self.assertEqual((got["staged"][3]["name"], got["staged"][3]["title"], got["staged"][3]["version"], got["staged"][3]["state"]), ("Sprig 3 1.0", "Sprig 3", "1.0", "ready"))
        with self.assertRaises(Bad):
            self.api.post("/api/add/status", {"staged": "all"})
        with self.assertRaises(Bad):
            self.api.post("/api/add", {"mods": [], "staged": ids})          # the Installer tool's own analysis keeps its limit

    def test_a_dropped_archive_is_unpacked_and_analysed_where_it_lies(self) -> None:
        rec = self.drop("Heather-4711-2-1-1700000000.zip", zipped(NEW_MOD))
        self.assertEqual((rec["name"], rec["state"]), ("Heather 2.1", "unpacking"))
        got = self.settled([], [rec["id"]])
        self.assertEqual([(s["name"], s["state"], s["files"]) for s in got["staged"]], [("Heather 2.1", "ready", 3)])
        x = got["mods"][0]
        self.assertTrue(x["staged"])
        self.assertEqual([p["name"] for p in x["plugins"]], ["Heather.esp"])
        self.assertEqual(x["plugins"][0]["proposed"]["before"], "Generated.esp")
        self.assertEqual([(c["mod"], c["files"]) for c in x["wins"]], [("Quill", 1)])
        self.assertEqual([s["key"] for s in got["steps"]][:3], ["install", "needs", "enable"])
        self.assertEqual(got["steps"][2]["state"], "waiting")
        self.assertEqual(snapshot(self.root), self.before)            # the modlist's folder: not one file changed

    def test_it_is_analysed_together_with_mods_mo2_has(self) -> None:
        rec = self.drop("Heather.zip", zipped(NEW_MOD))
        got = self.settled(["Thistle"], [rec["id"]])
        self.assertEqual([x["name"] for x in got["mods"]], ["Thistle", "Heather"])
        heather = got["mods"][1]
        self.assertIn("Thistle", [c["mod"] for c in heather["wins"] + heather["loses"]])

    def test_an_installers_questions_are_asked_and_the_answers_build_the_mod(self) -> None:
        files = {"Wrap/fomod/ModuleConfig.xml": FOMOD_XML.encode(), "Wrap/Core/Heather.esp": plugin.build((SKY, "Quill.esp")),
                 "Wrap/Purple/textures/shared/a.dds": b"purple", "Wrap/White/textures/shared/a.dds": b"white"}
        rec = self.drop("Heather Installer.zip", zipped(files))
        got = self.settled([], [rec["id"]])
        self.assertEqual((got["staged"][0]["state"], got["staged"][0]["installer"]), ("installer", True))
        self.assertEqual(got["mods"], [])                               # nothing to analyse until it is answered
        v = self.api.post("/api/add/installer", {"id": rec["id"], "picks": {}})[1]
        self.assertEqual([[o["name"] for o in g["options"] if o["chosen"]] for g in v["steps"][0]["groups"]], [["Purple"]])
        done = self.api.post("/api/add/choose", {"id": rec["id"], "picks": {"0.0": [1]}})[1]
        self.assertEqual((done["state"], done["files"]), ("ready", 2))
        got = self.settled([], [rec["id"]])
        x = got["mods"][0]
        self.assertEqual([p["name"] for p in x["plugins"]], ["Heather.esp"])
        root = Path(self.api._staged[rec["id"]]["root"])
        self.assertEqual((root / "textures" / "shared" / "a.dds").read_bytes(), b"white")
        # answering again builds it afresh and the old build goes
        self.api.post("/api/add/choose", {"id": rec["id"], "picks": {"0.0": [0]}})
        self.assertFalse(root.exists())
        self.assertEqual((Path(self.api._staged[rec["id"]]["root"]) / "textures" / "shared" / "a.dds").read_bytes(), b"purple")
        self.assertEqual(snapshot(self.root), self.before)

    def test_an_option_says_whether_what_it_goes_with_is_in_the_load_order(self) -> None:
        """MT81: a patch for a mod of the modlist is marked as such, by the installer's own condition and by the
        masters of the plugin the option installs."""
        xml = """<config><moduleName>Patches</moduleName>
<requiredInstallFiles><file source="Core\\Base.esp" destination="Base.esp"/></requiredInstallFiles>
<installSteps order="Explicit"><installStep name="Patches"><optionalFileGroups><group name="For your mods" type="SelectAny"><plugins order="Explicit">
<plugin name="For Quill"><description/><files><file source="P\\ForQuill.esp" destination="ForQuill.esp"/></files><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
<plugin name="For Absent"><description/><files><folder source="Absent" destination=""/></files><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
<plugin name="By condition"><description/><files><folder source="Tex" destination=""/></files><typeDescriptor><dependencyType><defaultType name="Optional"/>
<patterns><pattern><dependencies operator="And"><fileDependency file="Quill.esp" state="Active"/><fileDependency file="Nowhere.esp" state="Active"/></dependencies>
<type name="Recommended"/></pattern></patterns></dependencyType></typeDescriptor></plugin>
<plugin name="Plain"><description/><files><folder source="Tex" destination=""/></files><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
<plugin name="For the base"><description/><files><file source="P\\ForBase.esp" destination="ForBase.esp"/></files><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
</plugins></group></optionalFileGroups></installStep></installSteps></config>"""
        files = {"fomod/ModuleConfig.xml": xml.encode(), "Core/Base.esp": plugin.build((SKY,)), "P/ForQuill.esp": plugin.build((SKY, "Quill.esp", "Base.esp")),
                 "Absent/ForAbsent.esp": plugin.build((SKY, "Absent.esm")), "Tex/textures/a.dds": b"x", "P/ForBase.esp": plugin.build((SKY, "Base.esp"))}
        rec = self.drop("Patches.zip", zipped(files))
        self.settled([], [rec["id"]])
        v = self.api.post("/api/add/installer", {"id": rec["id"], "picks": {}})[1]
        marks = {o["name"]: o.get("goes_with") for o in v["steps"][0]["groups"][0]["options"]}
        self.assertEqual(marks["For Quill"], {"there": True, "have": ["Quill.esp"], "lack": []})          # the game's own and the installer's own say nothing
        self.assertEqual(marks["For Absent"], {"there": False, "have": [], "lack": [{"name": "Absent.esm", "state": "missing"}]})
        self.assertEqual(marks["By condition"], {"there": False, "have": ["Quill.esp"], "lack": [{"name": "Nowhere.esp", "state": "missing"}]})
        self.assertEqual((marks["Plain"], marks["For the base"]), (None, None))
        self.assertEqual(snapshot(self.root), self.before)

    def test_the_unpacked_copies_of_older_installs_are_removed_and_the_newest_kept(self) -> None:
        """MT81: an install leaves ModTrap's unpacked copy behind, for an Uninstall to put the mod back on the list;
        fifty of those are kept."""
        base = self.api._incoming()
        made = []
        for i in range(api.STAGED_KEPT + 3):
            d = base / ("%010x" % (0xabc000 + i))
            d.mkdir(parents=True)
            (d / "files").mkdir()
            rec = {"id": d.name, "dir": str(d), "archive": "Mod %d.zip" % i, "name": "Mod %d" % i, "state": "installed", "root": str(d / "files")}
            self.api._staged[d.name] = rec
            self.api._save_staged(rec)
            os.utime(d / "staged.json", (1_700_000_000 + i, 1_700_000_000 + i))
            made.append(d)
        waiting = self.drop("Thistle2.zip", zipped({"Thistle2.esp": plugin.build((SKY,))}))
        self.settled([], [waiting["id"]])
        self.assertEqual(self.api._prune_staged(), 3)
        self.assertEqual([d.exists() for d in made[:4]], [False, False, False, True])            # the oldest three went, by when they were installed
        self.assertEqual(sum(1 for r in self.api._staged.values() if r["state"] == "installed"), api.STAGED_KEPT)
        self.assertIn(waiting["id"], self.api._staged)                                           # what still waits is never removed
        self.assertEqual(self.api._prune_staged(), 0)
        self.assertEqual(snapshot(self.root), self.before)

    def test_folders_to_choose_from_are_asked_too(self) -> None:
        rec = self.drop("Parts.zip", zipped({"00 Core/Parts.esp": plugin.build(()), "01 Extra/meshes/a.nif": b"x"}))
        self.settled([], [rec["id"]])
        v = self.api.post("/api/add/installer", {"id": rec["id"], "picks": {}})[1]
        self.assertEqual([o["name"] for o in v["steps"][0]["groups"][0]["options"]], ["00 Core", "01 Extra"])
        with self.assertRaises(Bad):
            self.api.post("/api/add/choose", {"id": rec["id"], "picks": {"0.0": []}})        # nothing chosen
        done = self.api.post("/api/add/choose", {"id": rec["id"], "picks": {"0.0": [0, 1]}})[1]
        self.assertEqual(done["files"], 2)

    def test_an_installer_modtrap_cannot_read_is_handed_to_mo2(self) -> None:
        rec = self.drop("Odd.zip", zipped({"fomod/ModuleConfig.xml": b"<notconfig/>", "Core/Odd.esp": plugin.build(())}))
        got = self.settled([], [rec["id"]])
        self.assertEqual((got["staged"][0]["state"], got["staged"][0]["installer"]), ("installer", False))
        self.assertIn("Install it in MO2", got["staged"][0]["note"])
        with self.assertRaises(Bad):
            self.api.post("/api/add/installer", {"id": rec["id"], "picks": {}})

    def test_what_is_not_an_archive_is_said_and_nothing_is_kept_of_a_refusal(self) -> None:
        rec = self.drop("Words.zip", b"not an archive at all")
        got = self.settled([], [rec["id"]])
        self.assertEqual(got["staged"][0]["state"], "failed")
        bad = self.drop("Climber.zip", zipped({"../../climbed.txt": b"x"}))
        got = self.settled([], [bad["id"]])
        self.assertEqual(got["staged"][0]["state"], "failed")
        self.assertFalse(any(p.name == "climbed.txt" for p in Path(self.tmp.name).rglob("*")))

    def test_a_name_already_in_mo2_gets_a_number(self) -> None:
        rec = self.drop("Quill.zip", zipped({"Quill.esp": plugin.build(())}))
        self.assertEqual(rec["name"], "Quill (2)")

    def test_names_that_are_not_file_names_are_refused(self) -> None:
        for name in ("", "..", "a" * 300, 'bad"name.zip', "nul\x00.zip"):
            with self.assertRaises(Bad, msg=name):
                self.drop(name, b"x")
        with self.assertRaises(Bad):
            self.api.upload("Short.zip", 50, io.BytesIO(b"only ten b"))          # it did not arrive whole
        self.assertEqual(self.api._staged, {})

    def test_an_archive_in_mo2s_downloads_is_read_there_without_a_copy(self) -> None:
        data = zipped(NEW_MOD)
        write(self.root / "downloads" / "Heather.zip", data)
        rec = self.api.post("/api/add/take", {"name": "Heather.zip", "size": len(data)})[1]
        got = self.settled([], [rec["id"]])
        self.assertEqual(got["staged"][0]["state"], "ready")
        self.assertFalse((Path(self.api._staged[rec["id"]]["dir"]) / "archive").exists())
        with self.assertRaises(Bad):
            self.api.post("/api/add/take", {"name": "Heather.zip", "size": len(data) + 1})
        with self.assertRaises(Bad):
            self.api.post("/api/add/take", {"name": "../ModOrganizer.ini"})

    def test_taking_it_off_the_list_removes_modtraps_copy_only(self) -> None:
        rec = self.drop("Heather.zip", zipped(NEW_MOD))
        self.settled([], [rec["id"]])
        d = Path(self.api._staged[rec["id"]]["dir"])
        self.assertTrue(d.is_dir())
        self.api.post("/api/add/forget", {"id": rec["id"]})
        self.assertFalse(d.exists())
        self.assertEqual(self.settled([], [rec["id"]])["gone"], [rec["id"]])
        self.assertEqual(snapshot(self.root), self.before)

    def test_what_was_taken_in_is_there_again_after_a_restart(self) -> None:
        rec = self.drop("Heather.zip", zipped(NEW_MOD))
        self.settled([], [rec["id"]])
        again = api.Api()
        self.assertTrue(again.restore())
        for _ in range(200):
            if again.status == "ready":
                break
            time.sleep(0.02)
        got = None
        for _ in range(300):
            got = again.post("/api/add", {"mods": [], "staged": [rec["id"]]})[1]
            if not got["looking"]:
                break
            time.sleep(0.02)
        self.assertEqual([x["name"] for x in got["mods"]], ["Heather"])


class UploadOverHttp(unittest.TestCase):
    """The file's bytes go through the server's own guards, straight to disk."""

    def setUp(self) -> None:
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        self.api = api.Api()
        self.app = server.App(self.api)
        self.httpd = server.Server(0, self.app)
        self.port = self.httpd.port
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.api.open(str(self.root), wait=True)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def send(self, name: str, data: bytes, *, token: bool = True, origin: bool = True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Host": "127.0.0.1:%d" % self.port, "Content-Type": "application/octet-stream"}
        if token:
            headers[server.TOKEN_HEADER] = self.app.token
        if origin:
            headers["Origin"] = "http://127.0.0.1:%d" % self.port
        conn.request("POST", server.UPLOAD_PATH + "?name=" + urllib.parse.quote(name), body=data, headers=headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, json.loads(raw or b"{}")

    def test_an_upload_arrives_and_is_unpacked(self) -> None:
        status, rec = self.send("Heather 2.1.zip", zipped(NEW_MOD))
        self.assertEqual((status, rec["name"]), (200, "Heather 2.1"))
        for _ in range(300):
            if self.api._staged[rec["id"]]["state"] == "ready":
                break
            time.sleep(0.02)
        self.assertEqual(self.api._staged[rec["id"]]["files"], 3)

    def test_the_guards_hold_for_uploads_too(self) -> None:
        data = zipped(NEW_MOD)
        self.assertEqual(self.send("Heather.zip", data, token=False)[0], 403)
        self.assertEqual(self.send("Heather.zip", data, origin=False)[0], 403)
        self.assertEqual(self.send("..", data)[0], 400)
        self.assertEqual(self.api._staged, {})


if __name__ == "__main__":
    unittest.main()
