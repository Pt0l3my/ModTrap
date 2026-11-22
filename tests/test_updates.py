"""The update check (MT37, WHY§101): where a mod came from, read on this PC; what Nexus and GitHub say, by stand-ins."""

import io
import json
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from modtrap import api, instance, logbook, model, secret, sources, updates, updating
from tests import _fixtures as fx

DAY = 86400


def meta(**general) -> str:
    files = general.pop("files", [])
    out = "[General]\r\n" + "".join("%s=%s\r\n" % kv for kv in general.items())
    if files:
        out += "\r\n[installedFiles]\r\n" + "".join("%d\\modid=%d\r\n%d\\fileid=%d\r\n" % (i, m, i, f) for i, (m, f) in enumerate(files, 1))
        out += "size=%d\r\n" % len(files)
    return out


class FakeNet:
    """A stand-in for the two services: answers by address, and keeps what it was asked and with which headers."""

    def __init__(self, answers):
        self.answers, self.asked, self.agent = answers, [], "ModTrap/test"

    def get(self, url, headers):
        self.asked.append((url, dict(headers)))
        for part, answer in self.answers.items():
            if part in url:
                status, h, body = answer(url) if callable(answer) else answer
                return status, dict(h), body
        return 404, {}, None


def files_answer(files, chain=()):
    return {"files": [{"file_id": i, "file_name": n, "version": v, "category_id": c, "uploaded_timestamp": t} for i, n, v, c, t in files],
            "file_updates": [{"old_file_id": a, "new_file_id": b, "old_file_name": an, "new_file_name": bn} for a, b, an, bn in chain]}


class Sources(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        self.mods = self.root / "mods"
        fx.write(self.mods / "Quill" / "meta.ini", meta(gameName="SkyrimSE", modid=4321, version="1.2.0.0", newestVersion="1.3.0.0",
                                                         installationFile="C:/Lists/Example/downloads/Quill-4321-1-2-1700000000.7z",
                                                         repository="Nexus", url="", hasCustomURL="false", files=[(4321, 111)]))
        fx.write(self.mods / "Lantern" / "meta.ini", meta(gameName="SkyrimSE", modid=0, version="2.0", installationFile="Lantern.Release.zip",
                                                           url="https://github.com/invented-owner/lantern/releases/download/v2.0/Lantern.Release.zip", hasCustomURL="true"))
        fx.write(self.mods / "Bramble" / "meta.ini", meta(gameName="SkyrimSE", modid=-1, version="", installationFile="Bramble main.7z"))
        fx.write(self.root / "downloads" / "Bramble main.7z.meta", meta(gameName="SkyrimSE", modID=777, fileID=7001, version="0.9"))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def rows(self, wj=None, added=None):
        return {r["mod"]: r for r in sources.gather(instance.load(self.root), wj, added)}

    def test_a_mods_own_records_say_where_it_came_from(self):
        r = self.rows()
        q = r["Quill"]
        self.assertEqual((q["host"], q["game"], q["mod_id"], q["files"], q["version"], q["mo2_newest"]),
                         ("nexus", "skyrimspecialedition", 4321, [111], "1.2.0.0", "1.3.0.0"))
        self.assertEqual(q["archive"], "Quill-4321-1-2-1700000000.7z")
        self.assertEqual(q["origin"], "")                                   # no Wabbajack file: not known
        lan = r["Lantern"]
        self.assertEqual((lan["host"], lan["repo"], lan["tag"]), ("github", "invented-owner/lantern", "v2.0"))
        b = r["Bramble"]                                                     # nothing in meta.ini: the download's meta file says
        self.assertEqual((b["host"], b["mod_id"], b["files"], b["by"]), ("nexus", 777, [7001], ["the download's meta file"]))
        self.assertEqual(r["Old Lantern"]["host"], "")

    def wabbajack(self, big=False):
        archives = [{"Hash": "aaaa=", "Meta": "", "Name": "Quill-4321-1-2-1700000000.7z", "Size": 10,
                     "State": {"$type": "NexusDownloader, Wabbajack.Lib", "GameName": "SkyrimSpecialEdition", "ModID": 4321, "FileID": 112, "Version": "1.2"}},
                    {"Hash": "bbbb=", "Meta": "", "Name": "Old Lantern.zip", "Size": 10,
                     "State": {"$type": "HttpDownloader, Wabbajack.Lib", "Url": "https://example.invalid/files/Old%20Lantern.zip", "Headers": []}},
                    {"Hash": "cccc=", "Meta": "", "Name": "Data.bsa", "Size": 10, "State": {"$type": "GameFileSourceDownloader, Wabbajack.Lib", "GameFile": "Data\\\\x.bsa"}}]
        directives = [{"$type": "FromArchive", "Hash": "h1=", "Size": 3, "To": "mods\\Quill\\Quill.esp", "ArchiveHashPath": ["aaaa=", "Quill.esp"]},
                      {"$type": "FromArchive", "Hash": "h2=", "Size": 3, "To": "mods\\Old Lantern\\Lantern.esp", "ArchiveHashPath": ["bbbb=", "Lantern.esp"]},
                      {"$type": "InlineFile", "Hash": "h3=", "Size": 3, "To": "mods\\Lantern\\meta.ini", "SourceDataID": "x"},
                      {"$type": "FromArchive", "Hash": "h4=", "Size": 3, "To": "profiles\\Default\\modlist.txt", "ArchiveHashPath": ["cccc="]}]
        if big:                                                              # far more than one piece of the file
            directives += [{"$type": "FromArchive", "Hash": "h%d=" % i, "Size": i, "To": "mods\\Quill\\textures\\t%06d.dds" % i,
                            "ArchiveHashPath": ["aaaa=", "textures", "t%06d.dds" % i]} for i in range(30000)]
        doc = {"Archives": archives, "Author": "an invented author", "Description": "x" * 10, "Directives": directives, "GameType": "SkyrimSpecialEdition",
               "Image": "", "Name": "Invented List", "Readme": "", "WabbajackVersion": "4.0.0.0", "Website": "", "Version": "8.2.0", "IsNSFW": False}
        p = Path(self.tmp.name) / "Invented List.wabbajack"
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("modlist", json.dumps(doc))
            z.writestr("x", b"an inline file")
        return p

    def test_the_lists_own_file_names_its_archives_and_its_mods(self):
        wj = sources.read_wabbajack(self.wabbajack())
        self.assertEqual((wj["name"], wj["version"]), ("Invented List", "8.2.0"))
        self.assertEqual(wj["counts"]["archives"], 3)
        self.assertEqual(wj["counts"]["directives"], 4)
        self.assertEqual(sorted(wj["mods"]), ["lantern", "old lantern", "quill"])
        self.assertEqual(wj["archives"]["aaaa="]["mod_id"], 4321)
        r = self.rows(wj, {"Collection"})
        self.assertEqual(r["Quill"]["files"], [111, 112])                   # MO2's record first, the list's file added
        self.assertEqual((r["Quill"]["origin"], r["Lantern"]["origin"], r["Bramble"]["origin"]), ("list", "list", "added"))
        self.assertEqual((r["Old Lantern"]["host"], r["Old Lantern"]["origin"]), ("url", "list"))
        fx.write(self.mods / "ModTrap - Bramble" / "meta.ini", "[General]\r\n")
        p = self.root / "profiles" / "Default" / "modlist.txt"
        p.write_bytes(b"+ModTrap - Bramble\r\n" + p.read_bytes())
        self.assertEqual(self.rows(wj)["ModTrap - Bramble"]["origin"], "modtrap")

    def test_a_large_list_is_read_piece_by_piece_and_remembered(self):
        p = self.wabbajack(big=True)
        old = sources.WJ_CHUNK
        sources.WJ_CHUNK = 4096                                              # many pieces, values cut at every kind of place
        try:
            wj = sources.wabbajack(p)
        finally:
            sources.WJ_CHUNK = old
        self.assertEqual(wj["counts"]["directives"], 30004)
        self.assertEqual(wj["mods"]["quill"], ["aaaa="])
        real = sources.read_wabbajack
        sources.read_wabbajack = lambda *a, **k: self.fail("read again though remembered")
        try:
            self.assertEqual(sources.wabbajack(p)["counts"]["directives"], 30004)
        finally:
            sources.read_wabbajack = real

    def test_a_file_that_is_no_wabbajack_file_is_said_as_such(self):
        p = Path(self.tmp.name) / "not.wabbajack"
        p.write_bytes(b"nothing of the kind")
        with self.assertRaises(ValueError):
            sources.read_wabbajack(p)
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("something else", "x")
        with self.assertRaisesRegex(ValueError, "holds no list"):
            sources.read_wabbajack(p)
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("modlist", '{"Archives": [ {"Hash": "a", ')
        with self.assertRaisesRegex(ValueError, "could not be read to the end"):
            sources.read_wabbajack(p)


class GivenByHand(Sources):
    """WHY§103: a source link of the owner's own, meta files dropped on the page, a Wabbajack list sent as its bytes."""

    def test_a_link_says_what_kind_of_source_it_is(self):
        self.assertEqual(sources.parse_link("https://www.nexusmods.com/skyrimspecialedition/mods/555?tab=files&file_id=5"),
                         {"host": "nexus", "game": "skyrimspecialedition", "mod_id": 555, "file_id": 5,
                          "url": "https://www.nexusmods.com/skyrimspecialedition/mods/555?tab=files&file_id=5"})
        got = sources.parse_link("https://github.com/invented-owner/reed/releases/tag/v1")
        self.assertEqual((got["host"], got["repo"], got["tag"]), ("github", "invented-owner/reed", ""))
        self.assertEqual(sources.parse_link("https://example.invalid/mods/reed")["host"], "url")
        for bad in ("", "reed", "ftp://example.invalid/x", "https://example.invalid/a b", "javascript:alert(1)", "https://x/" + "a" * 600):
            with self.assertRaises(ValueError, msg=bad):
                sources.parse_link(bad)

    def test_the_owners_link_comes_before_every_record_and_touches_no_file_of_the_mod(self):
        before = (self.mods / "Quill" / "meta.ini").read_bytes()
        u = updating.Updating("test", FakeNet({}))
        inst_key = "the modlist"
        u.set_link(inst_key, "Quill", "https://www.nexusmods.com/skyrimspecialedition/mods/9999")
        u.set_link(inst_key, "Old Lantern", "https://example.invalid/old-lantern")
        r = {x["mod"]: x for x in sources.gather(instance.load(self.root), None, None, u._given(inst_key))}
        self.assertEqual((r["Quill"]["mod_id"], r["Quill"]["by"], r["Quill"]["given"]),
                         (9999, ["your link"], "https://www.nexusmods.com/skyrimspecialedition/mods/9999"))
        self.assertEqual((r["Old Lantern"]["host"], r["Old Lantern"]["url"]), ("url", "https://example.invalid/old-lantern"))
        self.assertEqual(updates.page_of(r["Old Lantern"]), "https://example.invalid/old-lantern")
        self.assertEqual((self.mods / "Quill" / "meta.ini").read_bytes(), before)
        self.assertEqual(u._given("another modlist")["links"], {})               # a link belongs to its modlist
        with self.assertRaises(updating.Bad):
            u.set_link(inst_key, "Quill", "not an address")
        u.set_link(inst_key, "Quill", "")
        self.assertEqual({x["mod"]: x for x in sources.gather(instance.load(self.root), None, None, u._given(inst_key))}["Quill"]["mod_id"], 4321)

    def test_dropped_meta_files_fill_in_where_the_mods_own_records_say_nothing(self):
        fx.write(self.mods / "Old Lantern" / "meta.ini", meta(installationFile="Old Lantern 1.0.zip"))
        u = updating.Updating("test", FakeNet({}))
        got = u.take_metas("the modlist", [
            {"name": "Old Lantern 1.0.zip.meta", "folder": "", "text": meta(gameName="SkyrimSE", modID=6100, fileID=61, version="1.0")},
            {"name": "Tool Output", "folder": "", "text": "x"},
            {"name": "meta.ini", "folder": "", "text": meta(gameName="SkyrimSE", modid=1)},
            {"name": "meta.ini", "folder": "Patch Collection", "text": meta(gameName="SkyrimSE", modid=6200, version="2.2", files=[(6200, 62)])},
            {"name": "meta.ini", "folder": "Quill", "text": meta(gameName="SkyrimSE", modid=1)},     # the mod's own record says more
            {"name": "empty.7z.meta", "folder": "", "text": "[General]\r\n"}, "not a file", {"name": 5}])
        self.assertEqual((got["archives"], got["mods"]), (1, 2))
        self.assertEqual(len(got["passed"]), 3)
        self.assertTrue(any("alone it does not say which mod" in t for t in got["passed"]))
        r = {x["mod"]: x for x in sources.gather(instance.load(self.root), None, None, u._given("the modlist"))}
        self.assertEqual((r["Old Lantern"]["mod_id"], r["Old Lantern"]["files"], r["Old Lantern"]["by"]), (6100, [61], ["a download's meta file you gave"]))
        self.assertEqual((r["Patch Collection"]["mod_id"], r["Patch Collection"]["files"], r["Patch Collection"]["by"]), (6200, [62], ["a meta file you gave"]))
        self.assertEqual((r["Quill"]["mod_id"], r["Quill"]["by"]), (4321, ["meta.ini"]))

    def test_a_dropped_lists_bytes_alone_are_read_and_only_the_reading_is_kept(self):
        import zlib
        p = self.wabbajack()
        with zipfile.ZipFile(p) as z:
            plain = z.read("modlist")
        packer = zlib.compressobj(6, zlib.DEFLATED, -15)
        packed = packer.compress(plain) + packer.flush()
        for method, data in ((8, packed), (0, plain)):
            u = updating.Updating("test", FakeNet({}))
            u.take_list("the modlist", "C:\\somewhere\\Invented List.wabbajack", 123456, 99 + method, method, len(data), io.BytesIO(data))
            for _ in range(300):
                if u.reading["state"] != "going":
                    break
                time.sleep(0.01)
            wj, place = u._list("the modlist")
            self.assertEqual((wj["name"], wj["counts"]["archives"], place["file"]), ("Invented List", 3, "Invented List.wabbajack"))
            self.assertEqual(sorted(x.name for x in (Path(os.environ["MODTRAP_HOME"]) / "wabbajack").iterdir() if "incoming" in x.name), [])
            # Another ModTrap finds the reading again, without the file.
            self.assertEqual(updating.Updating("test", FakeNet({}))._list("the modlist")[0]["name"], "Invented List")
        # Bytes that are not a list are said as such, and nothing is kept for them.
        u = updating.Updating("test", FakeNet({}))
        u.take_list("another modlist", "broken.wabbajack", 1, 1, 8, 5, io.BytesIO(b"\x00\x01\x02\x03\x04"))
        for _ in range(300):
            if u.reading["state"] != "going":
                break
            time.sleep(0.01)
        self.assertIn("could not be read", u.reading["error"])
        self.assertEqual(u._place("another modlist"), {})
        with self.assertRaises(updating.Bad):
            u.take_list("another modlist", "x.wabbajack", 1, 1, 8, 0, io.BytesIO(b""))

    def test_through_the_page_a_link_is_for_a_mod_of_this_modlist_only(self):
        a = api.Api()
        a.updating.net = FakeNet({})
        a.open(str(self.root), wait=True)
        self.assertEqual(a.post("/api/updates/link", {"mod": "Old Lantern", "url": "https://example.invalid/x"})[1], {"kept": True, "kind": "url"})
        row = next(r for r in a.get("/api/updates", {})[1]["rows"] if r["mod"] == "Old Lantern")
        self.assertEqual((row["given"], row["page"], row["host"]), ("https://example.invalid/x", "https://example.invalid/x", "url"))
        self.assertEqual(a.get("/api/updates", {})[1]["given"]["links"], 1)
        with self.assertRaises(api.Bad):
            a.post("/api/updates/link", {"mod": "No Such Mod", "url": "https://example.invalid/x"})
        self.assertEqual(a.post("/api/updates/metas", {"files": [{"name": "a.7z.meta", "text": meta(gameName="SkyrimSE", modID=1, fileID=2)}]})[1]["archives"], 1)
        got = a.updates_upload({"name": ["x.wabbajack"], "size": ["5"], "date": ["7"], "method": ["0"]}, 2, io.BytesIO(b"{}"))
        self.assertTrue(got["taken"])


class Verdicts(unittest.TestCase):
    def row(self, **over):
        r = {"mod": "Quill", "enabled": True, "host": "nexus", "game": "skyrimspecialedition", "mod_id": 4321, "files": [111],
             "archive": "Quill-4321-1-2.7z", "version": "1.2", "mo2_newest": "", "url": "", "repo": "", "tag": "", "by": [], "origin": ""}
        r.update(over)
        return r

    def kept(self, files, chain=()):
        return {"asked": 1_700_000_000, "files": [list(f) for f in files], "chain": [list(c) for c in chain]}

    def test_the_chain_of_replacements_is_followed_from_the_installed_file(self):
        files = [(111, "Quill-4321-1-2.7z", "1.2", 4, 100), (112, "Quill-4321-1-3.7z", "1.3", 4, 200), (113, "Quill-4321-1-4.7z", "1.4", 1, 300),
                 (120, "Quill Optional.7z", "1.0", 3, 50)]
        chain = [(111, 112, "Quill-4321-1-2.7z", "Quill-4321-1-3.7z"), (112, 113, "Quill-4321-1-3.7z", "Quill-4321-1-4.7z")]
        v = updates.nexus_verdict(self.row(), self.kept(files, chain))
        self.assertEqual((v["state"], v["newest"], v["file"]), ("update", "1.4", "Quill-4321-1-4.7z"))
        self.assertEqual(updates.nexus_verdict(self.row(files=[113]), self.kept(files, chain))["state"], "current")
        self.assertEqual(updates.nexus_verdict(self.row(files=[120]), self.kept(files, chain))["state"], "current")   # another file of the mod
        # Not by number: by the archive's name, also where the file is only in the chain (archived and hidden).
        v = updates.nexus_verdict(self.row(files=[]), self.kept(files[1:], chain))
        self.assertEqual((v["state"], v["newest"]), ("update", "1.4"))
        self.assertIn("by the archive's name", v["text"])
        # Two files installed: an update of either is an update.
        self.assertEqual(updates.nexus_verdict(self.row(files=[120, 112]), self.kept(files, chain))["state"], "update")

    def test_what_cannot_be_told_is_said_as_such_and_never_as_current(self):
        files = [(113, "Quill-4321-1-4.7z", "1.4", 1, 300)]
        v = updates.nexus_verdict(self.row(files=[], archive="renamed by hand.7z"), self.kept(files))
        self.assertEqual(v["state"], "maybe")
        self.assertIn("could not be told", v["text"])
        v = updates.nexus_verdict(self.row(files=[], archive="renamed by hand.7z", version="1.4.0"), self.kept(files))
        self.assertEqual(v["state"], "current")                               # the version is that of the main file
        # The installed file is marked old, nothing says what replaced it, and a later main file is there.
        v = updates.nexus_verdict(self.row(), self.kept([(111, "Quill-4321-1-2.7z", "1.2", 4, 100), (113, "Quill-new.7z", "2.0", 1, 300)]))
        self.assertEqual((v["state"], v["newest"]), ("maybe", "2.0"))
        self.assertEqual(updates.nexus_verdict(self.row(), None)["state"], "not asked")
        self.assertEqual(updates.nexus_verdict(self.row(), {"asked": 1, "gone": "hidden or removed"})["state"], "gone")

    def test_a_release_at_github_and_what_mo2_last_saw(self):
        row = self.row(host="github", repo="invented-owner/lantern", tag="v2.0", mod_id=0, files=[])
        store = {"nexus": {}, "github": {"invented-owner/lantern": {"asked": 1, "tag": "v2.1", "published": "2026-11-01T00:00:00Z"}}}
        self.assertEqual(updates.verdict(row, store)["state"], "update")
        store["github"]["invented-owner/lantern"]["tag"] = "v2.0"
        self.assertEqual(updates.verdict(row, store)["state"], "current")
        self.assertEqual(updates.verdict(dict(row, tag="", version="2.0"), store)["state"], "current")
        self.assertEqual(updates.verdict(dict(row, tag="", version=""), store)["state"], "maybe")
        v = updates.verdict(self.row(mo2_newest="1.3.0.0", version="1.2.0.0"), {"nexus": {}, "github": {}})
        self.assertEqual(v["state"], "not asked")
        self.assertIn("MO2's own last check saw version 1.3.0.0", v["text"])
        self.assertEqual(updates.verdict(self.row(host="", mod_id=0), {"nexus": {}, "github": {}})["state"], "none")
        self.assertTrue(updates.same_version("v1.2.0.0", "1.2"))
        self.assertFalse(updates.same_version("1.2", "1.2a"))


class Scan(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.rows = [dict(Verdicts.row(self), mod="Quill"), dict(Verdicts.row(self), mod="Reed", mod_id=5000, files=[900], enabled=False),
                     dict(Verdicts.row(self), mod="Lantern", host="github", repo="Invented-Owner/Lantern", tag="v2.0", mod_id=0, files=[])]
        self.now = 1_800_000_000
        self.limits = {"x-rl-daily-remaining": "2400", "x-rl-hourly-remaining": "90"}
        self.net = FakeNet({
            "/mods/updated?period=1m": (200, self.limits, [{"mod_id": 4321, "latest_file_update": self.now - DAY, "latest_mod_activity": self.now}]),
            "/mods/4321/files": (200, self.limits, files_answer([(111, "a.7z", "1.2", 4, 100), (113, "b.7z", "1.4", 1, self.now - DAY)], [(111, 113, "a.7z", "b.7z")])),
            "/mods/5000/files": (200, self.limits, files_answer([(900, "r.7z", "1.0", 1, 100)])),
            "/repos/invented-owner/lantern/releases/latest": (200, {"x-ratelimit-remaining": "55", "etag": 'W/"abc"'},
                                                               {"tag_name": "v2.1", "published_at": "2026-11-20T10:00:00Z"})})

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_a_scan_asks_what_needs_asking_and_keeps_the_answers(self):
        store = updates.load()
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, store, now=self.now)
        self.assertEqual((out["nexus"]["mods"], out["nexus"]["asked"], out["nexus"]["left"], out["nexus"]["day_left"]), (2, 2, 0, 2400))
        self.assertEqual((out["github"]["repos"], out["github"]["asked"]), (1, 1))
        # Only the two services, the key only to Nexus, and never in an address.
        for url, headers in self.net.asked:
            self.assertTrue(url.startswith(("https://api.nexusmods.com/v1/", "https://api.github.com/")), url)
            self.assertNotIn("INVENTEDKEY", url)
            self.assertEqual("APIKEY" in headers, "nexusmods" in url, url)
        self.assertEqual([updates.verdict(r, store)["state"] for r in self.rows], ["update", "current", "update"])
        # The answers are kept: a second ModTrap reads them without asking.
        again = updates.load()
        self.assertEqual([updates.verdict(r, again)["state"] for r in self.rows], ["update", "current", "update"])
        # A second scan the next day: the month's list shows nothing newer, so no mod is asked about again.
        self.net.asked.clear()
        self.net.answers["/mods/updated?period=1m"] = (200, self.limits, [])
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, again, now=self.now + DAY)
        self.assertEqual(out["nexus"]["asked"], 0)
        self.assertEqual([u for u, _h in self.net.asked if "/files" in u], [])
        # A mod the month's list names with a newer file than at the last asking is asked about again; so is one
        # last asked over four weeks ago.
        self.net.answers["/mods/updated?period=1m"] = (200, self.limits, [{"mod_id": 5000, "latest_file_update": self.now + 2 * DAY}])
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, again, now=self.now + 3 * DAY)
        self.assertEqual(out["nexus"]["asked"], 1)
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, again, now=self.now + 40 * DAY)
        self.assertEqual(out["nexus"]["asked"], 2)

    def test_without_a_key_nexus_is_not_asked_and_github_still_is(self):
        store = updates.load()
        out = updates.scan(self.rows, "", self.net, store, now=self.now)
        self.assertEqual((out["nexus"]["asked"], out["nexus"]["left"]), (0, 2))
        self.assertIn("no Nexus key", out["nexus"]["why_stopped"])
        self.assertEqual([u for u, _h in self.net.asked if "nexusmods" in u], [])
        self.assertEqual(out["github"]["asked"], 1)

    def test_the_accounts_allowance_is_spared_and_a_refused_key_is_said(self):
        store = updates.load()
        low = {"x-rl-daily-remaining": "250", "x-rl-hourly-remaining": "90"}
        self.net.answers["/mods/updated?period=1m"] = (200, low, [])
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, store, now=self.now)
        self.assertEqual((out["nexus"]["asked"], out["nexus"]["left"]), (0, 2))
        self.assertIn("250 question(s) left for today", out["nexus"]["why_stopped"])
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, updates.load(), now=self.now, per_scan=1)
        self.net.answers["/mods/updated?period=1m"] = (401, {}, None)
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, updates.load(), now=self.now)
        self.assertIn("did not accept the key", out["nexus"]["why_stopped"])
        # The enabled mod is asked about before the disabled one when only one fits.
        self.net.answers["/mods/updated?period=1m"] = (200, self.limits, [])
        self.net.asked.clear()
        out = updates.scan(self.rows, "INVENTEDKEY0123456789", self.net, {"format": "modtrap-updates/1", "nexus": {}, "github": {}, "last": {}},
                           now=self.now, per_scan=1)
        self.assertEqual((out["nexus"]["asked"], out["nexus"]["left"]), (1, 1))
        self.assertEqual([u.rsplit("/mods/", 1)[1] for u, _h in self.net.asked if "/files" in u], ["4321/files"])

    def test_the_real_net_goes_nowhere_but_the_two_services(self):
        net = updates.Net("test")
        for url in ("https://example.invalid/x", "http://api.nexusmods.com/v1/x", "https://api.nexusmods.com.example.invalid/x",
                    "https://api.github.com@example.invalid/x"):
            with self.assertRaises(updates.Refused, msg=url):
                net.get(url, {})


class TheKeyAndThePage(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "mods" / "Quill" / "meta.ini", meta(gameName="SkyrimSE", modid=4321, version="1.2", installationFile="a.7z", files=[(4321, 111)]))

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_the_key_is_kept_apart_and_never_given_back(self):
        a = api.Api()
        a.open(str(self.root), wait=True)
        mark = logbook.lines_after(0)[1]
        code, got, _after = a.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})
        self.assertEqual((code, got), (200, {"key": True}))
        self.assertEqual(secret.read("nexus"), "INVENTEDKEY0123456789abcdef")
        state = a.get("/api/updates", {})[1]
        self.assertTrue(state["key"])
        self.assertNotIn("INVENTEDKEY", json.dumps(state))
        self.assertNotIn("INVENTEDKEY", json.dumps(a.state()))
        self.assertNotIn("INVENTEDKEY", " ".join(ln["text"] for ln in logbook.lines_after(mark)[0]))
        with self.assertRaises(api.Bad):
            a.post("/api/updates/key", {"key": "too short"})
        a.post("/api/updates/key", {"key": None})
        self.assertFalse(a.get("/api/updates", {})[1]["key"])

    def test_the_page_gets_rows_and_a_scan_through_the_stand_in(self):
        a = api.Api()
        now = int(time.time())
        a.updating.net = FakeNet({"/mods/updated?period=1m": (200, {}, []),
                                  "/mods/4321/files": (200, {}, files_answer([(111, "a.7z", "1.2", 4, 100), (113, "b.7z", "1.4", 1, now)], [(111, 113, "a.7z", "b.7z")]))})
        a.open(str(self.root), wait=True)
        st = a.get("/api/updates", {})[1]
        quill = next(r for r in st["rows"] if r["mod"] == "Quill")
        self.assertEqual((quill["host"], quill["state"], quill["page"]), ("nexus", "not asked", "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files"))
        self.assertEqual(a.updating.net.asked, [])                           # no key, no GitHub mod: nothing asked at launch
        a.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})
        a.post("/api/updates/scan", {})
        for _ in range(200):
            if a.get("/api/updates", {})[1]["scan"]["state"] != "going":
                break
            time.sleep(0.02)
        st = a.get("/api/updates", {})[1]
        quill = next(r for r in st["rows"] if r["mod"] == "Quill")
        self.assertEqual((quill["state"], quill["newest"]), ("update", "1.4"))
        self.assertEqual(st["counts"]["update"], 1)
        self.assertEqual(st["last"]["nexus"]["asked"], 1)
        # A Wabbajack file is named by its path; a wrong one is refused in words.
        with self.assertRaises(api.Bad):
            a.post("/api/updates/list", {"path": str(self.root / "ModOrganizer.ini")})
        self.assertIn("updates_at_launch", a.settings())


if __name__ == "__main__":
    unittest.main()
