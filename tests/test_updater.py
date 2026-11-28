"""The Updater (MT50): one press takes a mod to its newer version, and no file is downloaded twice."""

import os
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, changes, downloads, history, instance, listjob, logbook, model, updating
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
        self.assertEqual(run["summary"], "“Quill” is updated to 1.4: “Quill 1.4” is enabled right after it, and the older version is disabled, not deleted.")
        inst = instance.load(self.root)
        old, new = inst.mod("Quill"), inst.mod("Quill 1.4")
        self.assertEqual((old.enabled, new.enabled, new.priority), (False, True, old.priority + 1))
        self.assertTrue((self.root / "mods" / "Quill" / "Quill.esp").is_file())                    # the older version is only disabled
        # The download is in ModTrap's own folder now, moved there, with where it came from.
        self.assertFalse(saved.exists())
        rows = self.api.get("/api/downloads", {})[1]["rows"]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["file"], r["size"], r["there"], r["where"]), ("Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip", len(self.data), True, "ModTrap's downloads folder"))
        self.assertEqual((r["host"], r["mod_id"], r["file_id"], r["version"], r["for_mod"], r["installed_as"]), ("nexus", 4321, 113, "1.4", "Quill", "Quill 1.4"))
        self.assertEqual(r["page"], "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
        self.assertTrue((downloads.folder() / r["file"]).is_file())
        # Installed mods: the newer version, with the install it came by.
        listed = self.api.get("/api/installed", {})[1]
        self.assertEqual(listed["total"], len(listed["rows"]))                       # MT81: the newest two hundred are listed, and their count said
        inst_rows = listed["rows"]
        self.assertEqual([(x["mod"], x["updates"], x["job"], x["enabled"], x["archive"]) for x in inst_rows],
                         [("Quill 1.4", "Quill", run["job"], True, "Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip")])
        # The Updates list: the older version as such, the newer one up to date.
        st = self.api.get("/api/updates", {})[1]
        self.assertEqual({x["mod"]: x["state"] for x in st["rows"] if x["mod"].startswith("Quill")}, {"Quill": "replaced", "Quill 1.4": "current"})
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
        self.assertTrue(instance.load(self.root).mod("Quill 1.4").enabled)
        del asked

    def settle(self):
        for _ in range(600):
            if not self.api.unsettled() and self.api.status == "ready":
                return
            time.sleep(0.02)

    def test_with_the_owners_setting_the_older_version_is_removed_after_the_update_and_comes_back(self):
        """MT82: installed, enabled, checked; then the older one is uninstalled, by the uninstall of MT66."""
        self.api.post("/api/settings", {"name": "update_removes_old", "value": True})
        fx.write(self.browser / "Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip", self.data)
        before = {p.relative_to(self.root / "mods" / "Quill").as_posix(): p.read_bytes() for p in (self.root / "mods" / "Quill").rglob("*") if p.is_file()}
        order = [n for n, _a in instance.load(self.root).load_order]
        got = self.api.post("/api/updater/start", {"mod": "Quill"})[1]
        run = self.ended(got["run"])
        self.assertEqual(run["state"], "done", run["summary"])
        self.assertEqual(run["summary"], "“Quill” is updated to 1.4: “Quill 1.4” is enabled in its place, and the older version is taken out of the modlist "
                                         "(kept by ModTrap; “Uninstall” puts it back).")
        self.assertIn("“Quill”, the older version: taken out of the modlist too (your setting). Its folder is kept by ModTrap, and “Uninstall” puts it back",
                      [t["text"] for st in run["stages"] for t in st["tasks"]])
        self.settle()
        inst = instance.load(self.root)
        self.assertIsNone(inst.mod("Quill"))
        self.assertTrue(inst.mod("Quill 1.4").enabled)
        self.assertFalse((self.root / "mods" / "Quill").exists())
        kept = list((self.root / listjob.REMOVED).glob("*/Quill"))
        self.assertEqual(len(kept), 1)                                                              # moved aside whole: nothing is deleted
        self.assertEqual({p.relative_to(kept[0]).as_posix(): p.read_bytes() for p in kept[0].rglob("*") if p.is_file()}, before)
        self.assertEqual(([n for n, _a in inst.load_order], model.build(inst).issues), (order, []))  # the plugin is the newer version's now, at its place
        kinds = [(e["kind"], e.get("mod")) for e in history.History(self.api.store.dir(self.api.session.id)).all()]
        self.assertIn(("mod uninstalled", "Quill"), kinds)
        # Taking the update out again puts the older version back first, then takes the newer one out: all as it was.
        self.api.post("/api/updater/revert", {"run": got["run"]})
        self.settle()
        inst = instance.load(self.root)
        self.assertTrue(inst.mod("Quill").enabled)
        self.assertIsNone(inst.mod("Quill 1.4"))
        self.assertEqual({p.relative_to(self.root / "mods" / "Quill").as_posix(): p.read_bytes() for p in (self.root / "mods" / "Quill").rglob("*") if p.is_file()}, before)
        self.assertEqual(([n for n, _a in inst.load_order], model.build(inst).issues), (order, []))
        self.assertEqual(list((self.root / listjob.REMOVED).glob("*/Quill")), [])

    def test_an_older_version_another_profile_has_enabled_is_left_where_it_is(self):
        self.api.post("/api/settings", {"name": "update_removes_old", "value": True})
        here = self.root / "profiles" / instance.load(self.root).profile
        other = self.root / "profiles" / "Another"
        other.mkdir()
        for name in ("modlist.txt", "plugins.txt", "loadorder.txt"):
            (other / name).write_bytes((here / name).read_bytes())
        self.api.open(str(self.root), wait=True)
        self.settle()
        fx.write(self.browser / "Quill 4321 1.4 2026-11-21T00-00Z Zx9InventedQ.zip", self.data)
        run = self.ended(self.api.post("/api/updater/start", {"mod": "Quill"})[1]["run"])
        self.assertEqual(run["state"], "done", run["summary"])
        self.assertIn("the older version is disabled, not deleted", run["summary"])
        self.assertIn("“Quill”, the older version, stays in the modlist, disabled: the profile “Another” has it enabled", [t["text"] for st in run["stages"] for t in st["tasks"]])
        self.settle()
        inst = instance.load(self.root)
        self.assertEqual((inst.mod("Quill").enabled, inst.mod("Quill 1.4").enabled), (False, True))
        self.assertTrue((self.root / "mods" / "Quill" / "Quill.esp").is_file())

    def test_an_archive_from_nexus_is_named_by_the_version_its_page_states(self):
        """WHY§151: the version in a download's name is not always the file's; the code at its end names the file."""
        rec = self.api._new_staged("Quill AE V1.4 4321 1.5 2026-11-21T00-00Z Zx9InventedQ.zip", "upload")
        self.assertEqual((rec["name"], rec["version"], rec["meta"].get("file_id"), rec["meta"].get("version")), ("Quill AE V1.4", "1.4", 113, "1.4"))
        # Nothing kept knows the page: it is asked, once, and the answer is kept.
        self.api.updating.store["nexus"].clear()
        asked = len(self.net.questions)
        rec = self.api._new_staged("Quill AE V1.4 4321 1.5 2026-11-21T00-00Z Zx9InventedQ.zip", "upload")
        self.assertEqual((rec["version"], rec["meta"].get("file_id")), ("1.4", 113))
        once = len(self.net.questions)
        self.assertGreater(once, asked)
        self.api._new_staged("Quill AE V1.4 4321 1.5 2026-11-21T00-00Z Zx9InventedQ.zip", "upload")
        self.assertEqual(len(self.net.questions), once)                              # kept: not asked a second time
        # A code the page does not have, or a page that does not answer: the name's own version stands.
        rec = self.api._new_staged("Quill AE V1.4 4321 1.5 2026-11-21T00-00Z NotOfThisPage.zip", "upload")
        self.assertEqual((rec["version"], rec["meta"].get("file_id")), ("1.5", None))
        self.api.updating.store["nexus"].clear()
        self.net.public = lambda query: (0, {"why": "no answer"}, None)
        rec = self.api._new_staged("Quill AE V1.4 4321 1.5 2026-11-21T00-00Z Zx9InventedQ.zip", "upload")
        self.assertEqual((rec["name"].startswith("Quill AE V1.4 1.5"), rec["version"]), (True, "1.5"))

    INSTALLER = """<config><moduleName>Quill</moduleName>
<requiredInstallFiles><file source="Core\\Quill.esp" destination="Quill.esp"/></requiredInstallFiles>
<installSteps order="Explicit"><installStep name="Colour"><optionalFileGroups><group name="Pick a colour" type="SelectExactlyOne"><plugins order="Explicit">
<plugin name="Purple"><description/><files><folder source="Purple" destination=""/></files><typeDescriptor><type name="Recommended"/></typeDescriptor></plugin>
<plugin name="White"><description/><files><folder source="White" destination=""/></files><typeDescriptor><type name="Optional"/></typeDescriptor></plugin>
</plugins></group></optionalFileGroups></installStep></installSteps></config>"""

    def asking(self, name: str = "Quill-2.0.zip") -> tuple[dict, dict]:
        """An update whose archive has an installer, started and waiting for its answers."""
        esp = (self.root / "mods" / "Quill" / "Quill.esp").read_bytes()
        path = fx.write(Path(self.tmp.name) / "given" / name, a_zip({"fomod/ModuleConfig.xml": self.INSTALLER.encode(), "Core/Quill.esp": esp,
                                                                    "Purple/textures/quill/c.dds": b"purple", "White/textures/quill/c.dds": b"white"}))
        pub = self.api.stage_where_it_lies(path, name, "Quill", "2.0", {"version": "2.0"})
        got = self.api.post("/api/updater/start", {"mod": "Quill", "staged": pub["id"]})[1]
        for _ in range(600):
            run = next(r for r in self.api.get("/api/updater", {})[1]["runs"] if r["id"] == got["run"])
            if run["asks"] or run["state"] not in ("going", "yours"):
                break
            time.sleep(0.02)
        return pub, run

    def test_an_installers_questions_are_answered_on_the_updater_tool_and_the_update_goes_on(self):
        """MT83: the run waits for the answers; it is not handed to Install mods and left there."""
        pub, run = self.asking()
        self.assertEqual((run["state"], run["asks"], run["handed"], run["staged"]), ("yours", True, False, pub["id"]))
        self.assertEqual(self.stages(run)[2:4], [("unpack", "yours"), ("check", "waiting")])
        self.assertTrue(self.api.get("/api/updater", {})[1]["going"])                          # the page keeps asking how it stands
        self.assertFalse(self.api._busy())                                                     # and nothing else of ModTrap waits with it
        v = self.api.post("/api/add/installer", {"id": pub["id"], "picks": {}})[1]
        self.assertEqual([o["name"] for o in v["steps"][0]["groups"][0]["options"]], ["Purple", "White"])
        self.api.post("/api/add/choose", {"id": pub["id"], "picks": {"0.0": [1]}})
        run = self.ended(run["id"])
        self.assertEqual((run["state"], run["asks"], [s for s in self.stages(run) if s[1] != "done"]), ("done", False, [("find", "skipped"), ("download", "skipped")]), run["summary"])
        self.assertIn("its installer's questions are answered: the mod is built from the answers (2 file(s))", [t["text"] for t in run["stages"][2]["tasks"]])
        self.settle()
        inst = instance.load(self.root)
        new = inst.mod(run["new"])
        self.assertEqual((inst.mod("Quill").enabled, new.enabled), (False, True))
        self.assertEqual((new.folder / "textures" / "quill" / "c.dds").read_bytes(), b"white")
        self.assertTrue(run["job"])

    def test_stopped_while_it_waits_for_answers_nothing_is_changed(self):
        pub, run = self.asking()
        before = (self.root / "profiles" / instance.load(self.root).profile / "modlist.txt").read_bytes()
        self.api.post("/api/updater/stop", {"run": run["id"]})
        run = self.ended(run["id"])
        self.assertEqual((run["state"], run["asks"]), ("stopped", False))
        self.assertEqual((self.root / "profiles" / instance.load(self.root).profile / "modlist.txt").read_bytes(), before)

    def test_an_update_finished_on_install_mods_is_taken_in_by_its_run(self):
        """MT83, the owner's report: the questions answered and "Update mod" pressed on Install mods; the run
        stood at "waits for you" for good."""
        pub, run = self.asking()
        rec = self.api._staged[pub["id"]]
        self.api.post("/api/add/choose", {"id": pub["id"], "picks": {"0.0": [0]}})
        run = self.ended(run["id"])
        self.assertEqual(run["state"], "done")
        # The same, for a run that was handed over: it is looked at again whenever the page asks.
        self.api.updater.runs[run["id"]].update(state="yours", handed=True, job="", summary="Waits for you.")
        self.api.updater._stage(self.api.updater.runs[run["id"]], "install")["state"] = "waiting"
        self.assertEqual(rec["state"], "installed")
        again = next(r for r in self.api.get("/api/updater", {})[1]["runs"] if r["id"] == run["id"])
        self.assertEqual((again["state"], again["handed"], again["job"], [s for s in self.stages(again) if s[1] not in ("done", "skipped")]), ("done", False, run["job"], []))
        self.assertIn("was installed from Install mods", again["summary"])
        self.assertIn("installed from Install mods: “%s” is in the modlist" % rec["name"], [t["text"] for st in again["stages"] for t in st["tasks"]])

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
        self.assertEqual(self.api.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})[1], {"key": True, "premium": True})   # said at once
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
        self.assertEqual((r["how"], r["where"], r["installed_as"]), ("fetched by ModTrap from Nexus, with your key", "ModTrap's downloads folder", "Quill 1.4"))

    def test_a_second_press_while_the_first_is_being_begun_starts_nothing_more(self):
        """WHY§118: the owner pressed twice while the first press was still looking for the file, and got two updates."""
        self.api.updater._starting.add("Quill")
        self.assertEqual(self.api.post("/api/updater/start", {"mod": "Quill"})[1], {"run": "", "open": "", "again": True})
        self.assertEqual(self.api.get("/api/updater", {})[1]["runs"], [])
        self.api.updater._starting.discard("Quill")

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

    def test_a_separator_is_added_below_a_mod_and_registered_in_mo2(self):
        """MT55: a folder "<name>_separator" in MO2's mods folder and its line in the profile's list, right below the
        mod named; through the add job, so that it can be taken out again."""
        before = instance.load(self.root)
        quill = before.mod("Quill").priority
        got = self.api.post("/api/separator/add", {"name": "  My   Things ", "below": "Quill"})[1]
        self.assertEqual((got["name"], got["priority"]), ("My Things_separator", quill + 1))
        inst = instance.load(self.root)
        sep = inst.mod("My Things_separator")
        self.assertEqual((sep.kind, sep.priority, inst.mod("Quill").priority), ("separator", quill + 1, quill))
        self.assertTrue((self.root / "mods" / "My Things_separator").is_dir())
        self.assertIn(b"My Things_separator\r\n", (self.root / "profiles" / "Default" / "modlist.txt").read_bytes())
        self.assertEqual([n for n, _a in inst.load_order], [n for n, _a in before.load_order])            # the load order is untouched
        for _ in range(400):
            if not self.api.unsettled():
                break
            time.sleep(0.02)
        self.assertIn("My Things_separator", [x["mod"] for x in self.api.get("/api/installed", {})[1]["rows"]])
        for bad in ({"name": "", "below": "Quill"}, {"name": "a/b", "below": "Quill"}, {"name": "My Things", "below": "Quill"}, {"name": "Other", "below": "No Such Mod"}):
            with self.assertRaises(api.Bad):
                self.api.post("/api/separator/add", bad)
        self.api.post("/api/add/revert", {"job": got["job"]})
        self.assertIsNone(instance.load(self.root).mod("My Things_separator"))
        self.assertFalse((self.root / "mods" / "My Things_separator").exists())

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
