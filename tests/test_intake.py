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
