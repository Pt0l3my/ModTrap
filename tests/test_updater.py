"""The Updater (MT50): one press takes a mod to its newer version, and no file is downloaded twice."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, downloads, instance, logbook, updating
from tests import _fixtures as fx
from tests.test_updates import FakeNet, a_zip, files_answer, meta, public_service


class TheUpdater(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        mods = self.root / "mods"
        fx.write(mods / "Quill" / "meta.ini", meta(gameName="SkyrimSE", modid=4321, version="1.2", installationFile="Quill-4321-1-2.7z", files=[(4321, 111)]))
        self.data = a_zip({"Quill.esp": (mods / "Quill" / "Quill.esp").read_bytes(), "textures/quill/new.dds": b"newer"})
        self.cdn = "https://cf-files.nexus-cdn.com/1704/4321/Quill-4321-1-4.zip?token=x"
        self.net = FakeNet({"/mods/4321/files/113/download_link": (200, {}, [{"name": "CDN", "short_name": "CDN", "URI": self.cdn}])})
        self.net.files = {self.cdn: self.data}
        self.net.public = public_service({4321: {"updated": "2026-11-21T00:00:00Z", "files": [
            (111, "Quill-4321-1-2.7z", "1.2", 4, 1700000000, 42, "Quill", 1000, "Aa1OlderCode"),
            (113, "ab/cd/ef/0123456789abcdef", "1.4", 1, 1795219200, 42, "Quill", len(self.data), "Zx9InventedQ")]}})
        self.browser = Path(self.tmp.name) / "Browser Downloads"
        self.browser.mkdir()
        self.kept = updating.LOOK_EVERY
        updating.LOOK_EVERY = 0.05
        self.api = api.Api()
        self.api.updating.net = self.net
        self.api.running = lambda image: False
        self.api.open(str(self.root), wait=True)
        self.api.changes = changes.Changes(self.api, require_probe=False)
        self.api.post("/api/updates/folder", {"path": str(self.browser)})
        for _ in range(400):                              # the scan begun at launch
            st = self.api.get("/api/updates", {})[1]
            if st["scan"]["state"] != "going" and st["last"]:
                break
            time.sleep(0.02)

    def tearDown(self):
        updating.LOOK_EVERY = self.kept
        for r in self.api.updater.runs.values():
            r["_stop"] = True
        time.sleep(0.15)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def ended(self, run_id, seconds=30):
        end = time.time() + seconds
        while time.time() < end:
            run = next(r for r in self.api.get("/api/updater", {})[1]["runs"] if r["id"] == run_id)
            if run["state"] not in ("going",) and not (run["state"] == "yours" and not run["handed"] and run["waits_page"]):
                if run["state"] != "yours" or run["handed"]:
                    return run
            time.sleep(0.05)
        self.fail("the update did not end: %s" % [(s["key"], s["state"], [t["text"] for t in s["tasks"]]) for s in run["stages"]])

    def stages(self, run):
        return [(s["key"], s["state"]) for s in run["stages"]]

    def test_one_press_and_the_owners_press_on_the_site_take_the_mod_to_its_newer_version(self):
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertEqual(got["open"], "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
        run = self.api.get("/api/updater", {})[1]["runs"][0]
        self.assertEqual((run["mod"], run["version"], run["waits_page"]), ("Quill", "1.4", True))
        self.assertEqual(self.stages(run)[:2], [("find", "done"), ("download", "yours")])
        # The owner presses the site's download button: the browser saves the file, under a name of the site's own.
        saved = fx.write(self.browser / "Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip", self.data)
        run = self.ended(got["run"])
        self.assertEqual((run["state"], self.stages(run)), ("done", [(k, "done") for k, _t in __import__("modtrap.updater", fromlist=["STAGES"]).STAGES]))
        self.assertEqual(run["summary"], "“Quill” is updated to 1.4: “Quill (1.4)” is enabled right after it, and the older version is disabled, not deleted.")
        inst = instance.load(self.root)
        old, new = inst.mod("Quill"), inst.mod("Quill (1.4)")
        self.assertEqual((old.enabled, new.enabled, new.priority), (False, True, old.priority + 1))
        self.assertTrue((self.root / "mods" / "Quill" / "Quill.esp").is_file())                    # the older version is only disabled
        # The download is in ModTrap's own folder now, moved there, with where it came from.
        self.assertFalse(saved.exists())
        rows = self.api.get("/api/downloads", {})[1]["rows"]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["file"], r["size"], r["there"], r["where"]), ("Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip", len(self.data), True, "ModTrap's downloads folder"))
        self.assertEqual((r["host"], r["mod_id"], r["file_id"], r["version"], r["for_mod"], r["installed_as"]), ("nexus", 4321, 113, "1.4", "Quill", "Quill (1.4)"))
        self.assertEqual(r["page"], "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
        self.assertTrue((downloads.folder() / r["file"]).is_file())
        # The Updates list: the older version as such, the newer one up to date.
        st = self.api.get("/api/updates", {})[1]
        self.assertEqual({x["mod"]: x["state"] for x in st["rows"] if x["mod"].startswith("Quill")}, {"Quill": "replaced", "Quill (1.4)": "current"})
        # Taken out again and pressed once more: the file is here, no page is opened, nothing is downloaded.
        self.api.post("/api/add/revert", {"job": run["job"]})
        for _ in range(400):
            if not self.api.unsettled():
                break
            time.sleep(0.02)
        asked = len(self.net.asked) if hasattr(self.net, "asked") else 0
        again = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertEqual(again["open"], "")
        run2 = self.ended(again["run"])
        self.assertEqual((run2["state"], self.stages(run2)[:2]), ("done", [("find", "done"), ("download", "skipped")]))
        self.assertIn("it is on this PC already, in ModTrap's downloads folder: it is not downloaded again", [t["text"] for t in run2["stages"][0]["tasks"]])
        self.assertEqual(len(self.api.get("/api/downloads", {})[1]["rows"]), 1)                     # kept once
        self.assertTrue(instance.load(self.root).mod("Quill (1.4)").enabled)
        del asked

    def test_a_file_downloaded_before_is_used_and_no_page_is_opened(self):
        # In the browser's folder from an earlier day, under whatever name: known by its size, to the byte.
        fx.write(self.browser / "something saved last week", self.data)
        fx.write(self.browser / "not it.zip", a_zip({"readme.txt": b"another file"}))
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertEqual(got["open"], "")
        run = self.ended(got["run"])
        self.assertEqual(run["state"], "done", run["summary"])
        self.assertEqual(self.stages(run)[1], ("download", "skipped"))
        r = self.api.get("/api/downloads", {})[1]["rows"][0]
        self.assertEqual((r["file"], r["where"]), ("something saved last week.zip", "ModTrap's downloads folder"))
        self.assertTrue((self.browser / "not it.zip").is_file())

    def test_a_file_in_mo2s_downloads_folder_is_used_from_there_and_stays(self):
        dl = self.root / "downloads"
        fx.write(dl / "renamed by mo2.zip", self.data)
        fx.write(dl / "renamed by mo2.zip.meta", meta(gameName="SkyrimSE", modID=4321, fileID=113, version="1.4"))
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertEqual(got["open"], "")
        run = self.ended(got["run"])
        self.assertEqual(run["state"], "done", run["summary"])
        self.assertTrue((dl / "renamed by mo2.zip").is_file())                                      # MO2's file stays where it is
        r = self.api.get("/api/downloads", {})[1]["rows"][0]
        self.assertEqual((r["file"], r["where"], r["there"]), ("renamed by mo2.zip", "MO2's downloads folder", True))
        self.assertEqual(list(downloads.folder().glob("*.zip")), [])

    def test_with_the_key_of_a_paying_account_modtrap_fetches_the_file_itself(self):
        self.net.answers["users/validate"] = (200, {}, {"user_id": 1, "is_premium": True})
        self.net.answers["/mods/updated?period=1m"] = (200, {}, [])
        self.net.answers["/mods/4321/files"] = (200, {}, files_answer([(111, "Quill-4321-1-2.7z", "1.2", 4, 100), (113, "Quill-4321-1-4.zip", "1.4", 1, int(time.time()))],
                                                                       [(111, 113, "Quill-4321-1-2.7z", "Quill-4321-1-4.zip")]))
        self.api.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})
        self.api.post("/api/updates/scan", {})
        for _ in range(400):
            st = self.api.get("/api/updates", {})[1]
            if st["scan"]["state"] != "going" and st["premium"]:
                break
            time.sleep(0.02)
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertEqual(got["open"], "")                                                            # no page at all
        run = self.ended(got["run"])
        self.assertEqual((run["state"], self.stages(run)[1]), ("done", ("download", "done")), run["summary"])
        r = self.api.get("/api/downloads", {})[1]["rows"][0]
        self.assertEqual((r["how"], r["where"], r["installed_as"]), ("fetched by ModTrap from Nexus, with your key", "ModTrap's downloads folder", "Quill (1.4)"))

    def test_stopping_and_what_cannot_be_updated(self):
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        self.assertTrue(self.api.post("/api/updater/start", {"mod": "Quill"})[1]["again"])           # one run for a mod
        self.assertEqual(self.api.post("/api/updater/reopen", {"run": got["run"]})[1]["open"], got["open"])
        self.api.post("/api/updater/stop", {"run": got["run"]})
        run = self.ended(got["run"])
        self.assertEqual((run["state"], run["summary"]), ("stopped", "Stopped. Nothing of the modlist was changed."))
        self.assertTrue(instance.load(self.root).mod("Quill").enabled)
        self.assertEqual(self.api.post("/api/updater/clear", {})[1], {"cleared": 1})
        with self.assertRaises(api.Bad):
            self.api.post("/api/updater/start", {"mod": "No Such Mod"})
        self.api.changes = None
        with self.assertRaises(api.Bad):
            self.api.post("/api/updater/start", {"mod": "Quill"})

    def test_modtraps_downloads_folder_can_be_named(self):
        other = Path(self.tmp.name) / "My ModTrap downloads"
        self.assertEqual(self.api.post("/api/downloads/folder", {"path": str(other)})[1]["folder"], str(other))
        self.assertTrue(other.is_dir())
        st = self.api.get("/api/downloads", {})[1]
        self.assertEqual((st["folder"], st["own"], st["rows"]), (str(other), False, []))
        self.api.post("/api/downloads/folder", {"path": ""})
        self.assertTrue(self.api.get("/api/downloads", {})[1]["own"])
        with self.assertRaises(api.Bad):
            self.api.post("/api/downloads/folder", {"path": "not a full path"})


if __name__ == "__main__":
    unittest.main()
