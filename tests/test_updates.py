"""The update check (MT37, WHY§101): where a mod came from, read on this PC; what Nexus and GitHub say, by stand-ins."""

import io
import json
import os
import re
import tempfile
import time
import types
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

    def ask(self, url, query, headers):
        """Nexus's public service: `public(query)` answers, where a test gives one; else it is not there."""
        self.asked.append((url, dict(headers)))
        self.questions = getattr(self, "questions", []) + [query]
        public = getattr(self, "public", None)
        return public(query) if public is not None else (404, {}, None)

    def download(self, url, dest, progress=None, stopped=None):
        """A file fetched: what `files` holds for the address, written as the real one writes it."""
        self.asked.append((url, {}))
        data = getattr(self, "files", {}).get(url)
        if data is None:
            raise updates.Refused("the file's host answered with an error (404)")
        Path(dest).write_bytes(data)
        if progress is not None:
            progress(len(data), len(data))
        return len(data)


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
        self.assertEqual((got["host"], got["repo"], got["tag"]), ("github", "invented-owner/reed", "v1"))    # a release's page names its tag too
        self.assertEqual(sources.parse_link("https://github.com/invented-owner/reed")["tag"], "")
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


class TheBrowsersMark(Sources):
    """WHY§109: a browser on Windows leaves a mark on a file it downloads, naming the address. Where no record names
    a mod's source and its archive still lies in MO2's downloads folder, that mark does."""

    MARK = "[ZoneTransfer]\r\nZoneId=3\r\nReferrerUrl=%s\r\nHostUrl=%s\r\n"

    def test_the_mark_names_the_file_and_the_page_and_a_github_address_counts_first(self):
        m = sources.web_mark(Path("x"), lambda p: self.MARK % ("https://github.com/invented-owner/reed/releases/tag/v1.2",
                                                               "https://objects.githubusercontent.com/invented/asset?token=1"))
        self.assertEqual(m, {"page": "https://github.com/invented-owner/reed/releases/tag/v1.2",
                             "url": "https://objects.githubusercontent.com/invented/asset?token=1"})
        self.assertEqual(sources.source_of_mark(m), "https://github.com/invented-owner/reed/releases/tag/v1.2")
        m = sources.web_mark(Path("x"), lambda p: self.MARK % ("https://example.invalid/mods/reed", "https://github.com/invented-owner/reed/releases/download/v3/Reed.zip"))
        self.assertEqual(sources.source_of_mark(m), "https://github.com/invented-owner/reed/releases/download/v3/Reed.zip")
        m = sources.web_mark(Path("x"), lambda p: self.MARK % ("https://example.invalid/mods/reed", "https://cdn.example.invalid/reed.zip"))
        self.assertEqual(sources.source_of_mark(m), "https://example.invalid/mods/reed")       # the page before the file's own address
        for text in ("", "[ZoneTransfer]\r\nZoneId=3\r\n", "HostUrl=about:internet\r\n", "HostUrl=javascript:alert(1)\r\n", "HostUrl=https://a b/c\r\n"):
            self.assertEqual(sources.source_of_mark(sources.web_mark(Path("x"), lambda p, t=text: t)), "", text)
        self.assertEqual(sources.web_mark(self.root / "no such file"), {})                  # no mark, on any system

    def test_a_mod_with_no_record_of_its_source_gets_it_from_its_archives_mark(self):
        fx.write(self.mods / "Old Lantern" / "meta.ini", meta(installationFile="Old Lantern v1.zip"))
        fx.write(self.root / "downloads" / "Old Lantern v1.zip", b"an archive")
        marks = {"Old Lantern v1.zip": self.MARK % ("https://github.com/invented-owner/old-lantern/releases/tag/v1", "https://objects.githubusercontent.com/x"),
                 "Quill-4321-1-2-1700000000.7z": self.MARK % ("https://example.invalid/elsewhere", "https://example.invalid/q.7z")}
        reader = lambda p: marks.get(Path(p).name, "")
        r = {x["mod"]: x for x in sources.gather(instance.load(self.root), mark_reader=reader)}
        old = r["Old Lantern"]
        self.assertEqual((old["host"], old["repo"], old["tag"], old["by"]),
                         ("github", "invented-owner/old-lantern", "v1", ["the mark your browser left on the downloaded archive"]))
        self.assertEqual((r["Quill"]["host"], r["Quill"]["mod_id"]), ("nexus", 4321))        # a record of its own comes before any mark
        self.assertEqual(r["Tool Output"]["host"], "")                                       # no archive named: nothing to read

    def test_a_mod_modtrap_adds_carries_its_source_in_its_own_record(self):
        text = sources.own_record("Quill-4321-1-4.7z", {"game": "SkyrimSE", "mod_id": 4321, "file_id": 113, "version": "1.4"})
        folder = Path(self.tmp.name) / "new mod"
        fx.write(folder / "meta.ini", text)
        got = sources.mod_meta(folder)
        self.assertEqual((got["mod_id"], got["game"], got["version"], got["files"], got["archive"]), (4321, "SkyrimSE", "1.4", [(4321, 113)], "Quill-4321-1-4.7z"))
        fx.write(folder / "meta.ini", sources.own_record("Reed.zip", {"url": "https://github.com/invented-owner/reed/releases/download/v3/Reed.zip", "version": 'v3"\r\n[x]'}))
        got = sources.mod_meta(folder)
        self.assertEqual((got["url"], got["mod_id"], got["version"]), ("https://github.com/invented-owner/reed/releases/download/v3/Reed.zip", 0, "v3[x]"))
        self.assertEqual(sources.own_record("a.zip"), "[General]\r\ninstallationFile=a.zip\r\n")
        self.assertNotIn("url=", sources.own_record("a.zip", {"url": "javascript:alert(1)"}))


class TheListAsTheModlist(Sources):
    """WHY§104: each row carries what the Updates tab needs to lay the mods out as the modlist does."""

    def test_a_row_has_the_mods_priority_and_what_the_owner_wrote_of_it_in_mo2(self):
        fx.write(self.mods / "Quill" / "meta.ini", meta(comments="keep an eye on this one",
                                                         notes='"<html><head><style>p { x: y; }</style></head><body><p>A longer note,</p><p>in two &amp; more lines.</p></body></html>"',
                                                         gameName="SkyrimSE", modid=4321, version="1.2", installationFile="a.7z", files=[(4321, 111)]))
        inst = instance.load(self.root)
        r = {x["mod"]: x for x in sources.gather(inst)}
        self.assertEqual((r["Quill"]["comments"], r["Quill"]["notes"]), ("keep an eye on this one", "A longer note, in two & more lines."))
        self.assertEqual(r["Quill"]["priority"], next(m.priority for m in inst.mods if m.name == "Quill"))
        self.assertEqual((r["Bramble"]["comments"], r["Bramble"]["notes"]), ("", ""))

    def test_the_update_button_leads_to_the_newer_file_itself(self):
        row = Verdicts.row(self)
        files = [(111, "a.7z", "1.2", 4, 100), (113, "b.7z", "1.4", 1, 300)]
        v = updates.nexus_verdict(row, {"asked": 1, "files": [list(f) for f in files], "chain": [[111, 113, "a.7z", "b.7z"]]})
        self.assertEqual(v["file_id"], 113)
        self.assertEqual(updates.get_of(row, v), "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
        unsure = updates.nexus_verdict(dict(row, files=[], archive="renamed.7z"), {"asked": 1, "files": [list(files[1])], "chain": []})
        self.assertEqual((unsure["state"], updates.get_of(row, unsure)), ("maybe", "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files"))
        self.assertEqual(updates.get_of(row, {"state": "current"}), "")
        gh = dict(row, host="github", repo="invented-owner/lantern", tag="v2.0")
        self.assertEqual(updates.get_of(gh, {"state": "update"}), "https://github.com/invented-owner/lantern/releases/latest")

    def test_single_mods_are_asked_about_now_whatever_is_kept(self):
        a = api.Api()
        now = int(time.time())
        a.updating.net = FakeNet({"/mods/updated?period=1m": (200, {}, []),
                                  "/mods/4321/files": (200, {}, files_answer([(111, "a.7z", "1.2", 1, 100)]))})
        a.open(str(self.root), wait=True)
        a.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})

        def wait():
            for _ in range(300):
                if a.get("/api/updates", {})[1]["scan"]["state"] != "going":
                    return
                time.sleep(0.02)

        wait()                                                                    # the scan begun at launch, if any
        a.post("/api/updates/scan", {})
        wait()
        first = len([u for u, _h in a.updating.net.asked if "/mods/4321/files" in u])
        a.post("/api/updates/scan", {})                                           # nothing newer: not asked again
        wait()
        self.assertEqual(len([u for u, _h in a.updating.net.asked if "/mods/4321/files" in u]), first)
        last = a.get("/api/updates", {})[1]["last"]["when"]
        a.post("/api/updates/scan", {"mods": ["Quill"]})                          # by name: asked now
        wait()
        self.assertEqual(len([u for u, _h in a.updating.net.asked if "/mods/4321/files" in u]), first + 1)
        self.assertEqual([u for u, _h in a.updating.net.asked[-2:] if "/mods/777/" in u], [])   # and only that mod
        self.assertEqual(a.get("/api/updates", {})[1]["last"]["when"], last)      # it is not "the last scan"
        row = next(r for r in a.get("/api/updates", {})[1]["rows"] if r["mod"] == "Quill")
        self.assertEqual((row["state"], row["get"], isinstance(row["priority"], int)), ("current", "", True))
        with self.assertRaises(api.Bad):
            a.post("/api/updates/scan", {"mods": []})


def a_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class FetchingANewerFile(unittest.TestCase):
    """MT40, WHY§105: with a key of a paying account ModTrap fetches the file and hands it to Add mods; without, or
    for a host that gives a program nothing, the page is opened and the reason said."""

    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        mods = self.root / "mods"
        fx.write(mods / "Quill" / "meta.ini", meta(gameName="SkyrimSE", modid=4321, version="1.2", installationFile="Quill-4321-1-2.7z", files=[(4321, 111)]))
        fx.write(mods / "Lantern" / "meta.ini", meta(gameName="SkyrimSE", modid=0, version="2.0", installationFile="Lantern.Release.2.0.zip",
                                                      url="https://github.com/invented-owner/lantern/releases/download/v2.0/Lantern.Release.2.0.zip", hasCustomURL="true"))
        fx.write(mods / "Old Lantern" / "meta.ini", meta(url="https://www.loverslab.com/files/file/1234-old-lantern/", hasCustomURL="true"))
        now = int(time.time())
        self.cdn = "https://cf-files.nexus-cdn.com/1704/4321/Quill-4321-1-4.zip?token=x"
        self.net = FakeNet({
            "users/validate": (200, {}, {"user_id": 1, "is_premium": True}),
            "/mods/updated?period=1m": (200, {}, []),
            "/mods/4321/files/113/download_link": (200, {}, [{"name": "CDN", "short_name": "CDN", "URI": self.cdn}]),
            "/mods/4321/files": (200, {}, files_answer([(111, "Quill-4321-1-2.7z", "1.2", 4, 100), (113, "Quill-4321-1-4.zip", "1.4", 1, now)],
                                                       [(111, 113, "Quill-4321-1-2.7z", "Quill-4321-1-4.zip")])),
            "/repos/invented-owner/lantern/releases/latest": (200, {}, {"tag_name": "v2.1", "published_at": "2026-11-20T10:00:00Z", "assets": [
                {"name": "Lantern.Release.2.1.zip", "browser_download_url": "https://github.com/invented-owner/lantern/releases/download/v2.1/Lantern.Release.2.1.zip", "size": 10},
                {"name": "Source.txt", "browser_download_url": "https://github.com/invented-owner/lantern/releases/download/v2.1/Source.txt", "size": 1}]})})
        self.net.files = {self.cdn: a_zip({"Quill.esp": (mods / "Quill" / "Quill.esp").read_bytes(), "textures/quill/new.dds": b"newer"}),
                          "https://github.com/invented-owner/lantern/releases/download/v2.1/Lantern.Release.2.1.zip": a_zip({"Lantern.esp": (mods / "Lantern" / "Lantern.esp").read_bytes()})}
        self.api = api.Api()
        self.api.updating.net = self.net
        self.api.updating.by_itself = False                    # these tests count the looks themselves
        self.api.running = lambda image: False
        self.api.open(str(self.root), wait=True)

    def tearDown(self):
        for _ in range(400):                              # a scan begun at launch ends before its folder goes
            if self.api.updating.work["state"] != "going" and self.api.updating.reading["state"] != "going":
                break
            time.sleep(0.01)
        time.sleep(0.05)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def wait(self, test):
        for _ in range(400):
            st = self.api.get("/api/updates", {})[1]
            if test(st):
                return st
            time.sleep(0.02)
        self.fail("it did not come about")

    def scanned(self, key=True):
        self.wait(lambda st: st["scan"]["state"] != "going")                      # the scan begun at launch, if any
        if key:
            self.api.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})
        self.api.post("/api/updates/scan", {})
        return self.wait(lambda st: st["scan"]["state"] != "going" and st["last"])

    def test_without_the_switch_for_changes_nothing_is_fetched(self):
        self.scanned()
        got = self.api.post("/api/updates/get", {"mod": "Quill"})[1]
        self.assertEqual(got["open"], "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
        self.assertEqual([u for u, _h in self.net.asked if "download_link" in u or "nexus-cdn" in u], [])

    def test_what_the_button_does_by_key_account_and_host(self):
        from modtrap import changes
        self.api.changes = changes.Changes(self.api, require_probe=False)
        st = self.scanned(key=False)                       # no key: GitHub is asked, Nexus is not
        rows = {r["mod"]: r for r in st["rows"]}
        self.assertEqual((rows["Old Lantern"]["host"], rows["Old Lantern"]["state"]), ("loverslab", "none"))
        self.assertEqual((rows["Lantern"]["state"], rows["Lantern"]["fetches"]), ("update", True))
        got = self.api.post("/api/updates/get", {"mod": "Old Lantern"})[1]
        self.assertEqual(got["open"], "https://www.loverslab.com/files/file/1234-old-lantern/")
        self.assertIn("logged-in browser", got["why"])
        # A key of an account that is not a paying one: the page, and the file is not asked for.
        self.net.answers["users/validate"] = (200, {}, {"user_id": 1, "is_premium": False})
        st = self.scanned()
        self.assertFalse(next(r for r in st["rows"] if r["mod"] == "Quill")["fetches"])
        got = self.api.post("/api/updates/get", {"mod": "Quill"})[1]
        self.assertNotIn("nmm=1", got["open"])                    # the browser's own download, not a mod manager's (WHY§112)
        self.assertIn("Premium", got["why"])
        self.assertEqual([u for u, _h in self.net.asked if "download_link" in u], [])
        with self.assertRaises(api.Bad):
            self.api.post("/api/updates/get", {"mod": "No Such Mod"})

    def test_a_paying_accounts_key_fetches_the_file_and_add_mods_takes_it_as_a_newer_version(self):
        from modtrap import changes
        self.api.changes = changes.Changes(self.api, require_probe=False)
        st = self.scanned()
        self.assertTrue(st["premium"])
        self.assertTrue(next(r for r in st["rows"] if r["mod"] == "Quill")["fetches"])
        self.assertEqual(self.api.post("/api/updates/get", {"mod": "Quill"})[1], {"going": True})
        st = self.wait(lambda st: st["fetching"].get("Quill", {}).get("state") in ("done", "failed", "open"))
        f = st["fetching"]["Quill"]
        self.assertEqual((f["state"], f["name"]), ("done", "Quill 1.4"))
        # The key went to Nexus's own service only; the file's host got none.
        for url, headers in self.net.asked:
            self.assertEqual("APIKEY" in headers, url.startswith("https://api.nexusmods.com/v1/"), url)
        # Add mods has it, unpacked, as a newer version of Quill: right above it, Quill to be disabled.
        staged = f["staged"]
        for _ in range(400):
            got = self.api.post("/api/add", {"mods": [], "staged": [staged]})[1]
            if not got.get("looking") and not got.get("unpacking") and got.get("mods"):
                break
            time.sleep(0.02)
        x = got["mods"][0]
        self.assertEqual((x["name"], x["updates"], x["updates_enabled"]), ("Quill 1.4", "Quill", True))
        self.assertEqual(next(r for r in got["staged"] if r["id"] == staged)["updates"], "Quill")
        # What the new mod's own record will say: the same mod at Nexus, the file that was fetched, its version.
        self.assertEqual(self.api._staged[staged]["meta"], {"game": "SkyrimSE", "mod_id": 4321, "file_id": 113, "version": "1.4"})
        self.api.post("/api/updates/seen", {"mod": "Quill"})
        self.assertEqual(self.api.get("/api/updates", {})[1]["fetching"], {})
        # A GitHub release: the file named as the installed archive but for its version.
        self.assertEqual(self.api.post("/api/updates/get", {"mod": "Lantern"})[1], {"going": True})
        st = self.wait(lambda st: st["fetching"].get("Lantern", {}).get("state") in ("done", "failed", "open"))
        self.assertEqual((st["fetching"]["Lantern"]["state"], st["fetching"]["Lantern"]["name"]), ("done", "Lantern 2.1"))

    def test_a_download_started_in_the_browser_is_taken_from_the_watched_folders(self):
        """MT42: the page is opened, the owner presses download there, and ModTrap takes the archive from MO2's
        downloads folder (by the numbers MO2 writes beside it) or from the browser's (by the file's name)."""
        from modtrap import changes
        self.api.changes = changes.Changes(self.api, require_probe=False)
        self.net.answers["users/validate"] = (200, {}, {"user_id": 1, "is_premium": False})
        browser = Path(self.tmp.name) / "Browser Downloads"
        browser.mkdir()
        self.api.post("/api/updates/folder", {"path": str(browser)})
        self.scanned()
        got = self.api.post("/api/updates/get", {"mod": "Quill"})[1]
        self.assertTrue(got["watching"])
        st = self.api.get("/api/updates", {})[1]
        self.assertEqual(list(st["watch"]["waiting"]), ["Quill"])
        self.assertEqual(st["watch"]["folder"], str(browser))
        data = self.net.files[self.cdn]
        # An older file, an unfinished one, and one of another mod are passed by.
        fx.write(browser / "Quill-4321-1-4.zip.crdownload", data)
        fx.write(browser / "something else.zip", data)
        old = fx.write(browser / "Quill-4321-1-2.zip", data)
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        self.api.updating._looked = 0
        self.api.get("/api/updates", {})
        self.assertEqual(list(self.api.get("/api/updates", {})[1]["watch"]["waiting"]), ["Quill"])
        # The download itself, as the browser names it; taken at the second look, once its size stands.
        fx.write(browser / "Quill-4321-1-4 (1).zip", data)
        for _ in range(3):
            self.api.updating._looked = 0
            st = self.api.get("/api/updates", {})[1]
        self.assertEqual((st["fetching"]["Quill"]["state"], st["fetching"]["Quill"]["name"]), ("done", "Quill 1.4"))
        self.assertEqual(st["watch"]["waiting"], {})
        self.assertTrue((browser / "Quill-4321-1-4 (1).zip").is_file())            # the owner's file stays where it is
        # MO2's own downloads folder, by the numbers in the file MO2 keeps beside the archive.
        self.api.post("/api/updates/seen", {"mod": "Quill"})
        self.api.post("/api/updates/get", {"mod": "Quill"})
        downloads = self.root / "downloads"
        fx.write(downloads / "renamed by mo2.zip", data)
        fx.write(downloads / "renamed by mo2.zip.meta", meta(gameName="SkyrimSE", modID=4321, fileID=113, version="1.4"))
        fx.write(downloads / "another mod.zip", data)
        fx.write(downloads / "another mod.zip.meta", meta(gameName="SkyrimSE", modID=9, fileID=1))
        for _ in range(3):
            self.api.updating._looked = 0
            st = self.api.get("/api/updates", {})[1]
        self.assertEqual(st["fetching"]["Quill"]["state"], "done")
        # Waiting can be stopped, and ends by itself.
        self.api.post("/api/updates/seen", {"mod": "Quill"})
        self.api.post("/api/updates/get", {"mod": "Quill"})
        self.api.post("/api/updates/wait", {"mod": "Quill"})
        self.assertEqual(self.api.get("/api/updates", {})[1]["watch"]["waiting"], {})
        self.api.post("/api/updates/get", {"mod": "Quill"})
        self.api.updating.waiting["Quill"]["since"] -= updating.WAIT_SECONDS + 10
        self.api.updating._looked = 0
        st = self.api.get("/api/updates", {})[1]
        self.assertIn("stopped waiting", st["fetching"]["Quill"]["error"])
        with self.assertRaises(api.Bad):
            self.api.post("/api/updates/folder", {"path": str(browser / "no such folder")})

    def test_the_watch_looks_by_itself_and_knows_an_archive_by_its_first_bytes_and_its_size(self):
        """WHY§112: nobody asks while the owner is on the site's page, so ModTrap looks by itself; the download may
        come under a name that tells nothing and has no ending, and is known by its size, to the byte."""
        from modtrap import changes
        self.api.changes = changes.Changes(self.api, require_probe=False)
        self.net.answers["users/validate"] = (200, {}, {"user_id": 1, "is_premium": False})
        data = self.net.files[self.cdn]
        self.net.public = public_service({4321: {"updated": "2026-11-21T00:00:00Z", "files": [
            (111, "Quill-4321-1-2.7z", "1.2", 4, 1700000000, 42, "Quill", 1000),
            (113, "ab/cd/ef/0123456789abcdef", "1.4", 1, 1795219200, 42, "Quill", len(data))]}})
        browser = Path(self.tmp.name) / "Browser Downloads"
        browser.mkdir()
        self.api.post("/api/updates/folder", {"path": str(browser)})
        self.scanned()
        self.api.updating.by_itself = True
        self.api.updating.net.answers.pop("/mods/4321/files", None)
        updating.LOOK_EVERY, kept = 0.05, updating.LOOK_EVERY
        try:
            got = self.api.post("/api/updates/get", {"mod": "Quill"})[1]
            self.assertEqual(got["open"], "https://www.nexusmods.com/skyrimspecialedition/mods/4321?tab=files&file_id=113")
            w = self.api.updating.waiting["Quill"]
            self.assertEqual((w["size"], w["name"], w["label"], w["file_id"]), (len(data), "", "Quill", 113))     # asked afresh at the press
            fx.write(browser / "notes.txt", b"not an archive at all")
            fx.write(browser / "0123456789abcdef.part", data[:10])
            fx.write(browser / "another archive.zip", a_zip({"readme.txt": b"of another size"}))
            fx.write(browser / "0123456789abcdef", data)                                 # no ending, a name that says nothing
            end = time.time() + 10
            while time.time() < end and self.api.updating.fetching.get("Quill", {}).get("state") != "done":
                time.sleep(0.05)                                                          # nobody asks: the watch looks by itself
        finally:
            updating.LOOK_EVERY = kept
        f = self.api.updating.fetching["Quill"]
        self.assertEqual((f["state"], f["name"]), ("done", "Quill 1.4"))
        self.assertEqual(self.api.updating.waiting, {})
        self.assertEqual(sorted(p.name for p in browser.iterdir()), ["0123456789abcdef", "0123456789abcdef.part", "another archive.zip", "notes.txt"])     # all of the owner's files stay

    def test_a_site_without_a_name_to_go_by_takes_the_one_archive_that_comes(self):
        from modtrap import changes
        self.api.changes = changes.Changes(self.api, require_probe=False)
        browser = Path(self.tmp.name) / "Browser Downloads"
        browser.mkdir()
        self.api.post("/api/updates/folder", {"path": str(browser)})
        self.wait(lambda st: st["scan"]["state"] != "going")
        row = next(r for r in self.api.get("/api/updates", {})[1]["rows"] if r["mod"] == "Old Lantern")
        self.assertEqual(row["get"], "https://www.loverslab.com/files/file/1234-old-lantern/")       # the button is there for it too
        self.api.post("/api/updates/get", {"mod": "Old Lantern"})
        fx.write(browser / "Old Lantern v3.7z.zip", a_zip({"Lantern.esp": (self.root / "mods" / "Lantern" / "Lantern.esp").read_bytes()}))
        for _ in range(3):
            self.api.updating._looked = 0
            st = self.api.get("/api/updates", {})[1]
        self.assertEqual((st["fetching"]["Old Lantern"]["state"], st["fetching"]["Old Lantern"]["name"]), ("done", "Old Lantern 3.7z"))

    def test_an_archive_the_owner_downloaded_is_taken_as_a_newer_version_of_the_mod_named(self):
        data = a_zip({"Lantern.esp": (self.root / "mods" / "Lantern" / "Lantern.esp").read_bytes()})
        rec = self.api.upload("old-lantern-from-the-browser.zip", len(data), io.BytesIO(data), "Old Lantern")
        self.assertEqual((rec["updates"], rec["name"]), ("Old Lantern", "Old Lantern (new)"))
        with self.assertRaises(api.Bad):
            self.api.upload("x.zip", len(data), io.BytesIO(data), "No Such Mod")

    def test_the_real_net_fetches_a_file_only_from_where_mod_files_are_kept(self):
        net = updates.Net("test")
        for url in ("https://example.invalid/x.zip", "http://github.com/a/b/releases/download/v1/x.zip", "https://github.com/a/b/archive/x.zip",
                    "https://nexus-cdn.com.example.invalid/x.zip", "https://%s/x.zip" % "@".join(("someone", "cf-files.nexus-cdn.com")),   # a name before the host
                    "https://www.loverslab.com/files/x.zip"):
            with self.assertRaises(updates.Refused, msg=url):
                net.download(url, Path(self.tmp.name) / "x.bin")
        self.assertFalse((Path(self.tmp.name) / "x.bin").exists())

    def test_which_file_of_a_release_is_the_mods(self):
        row = {"archive": "Lantern.Release.2.0.zip"}
        files = [["Lantern.Release.2.1.zip", "u1", 1], ["Lantern.Extras.2.1.zip", "u2", 1], ["notes.txt", "u3", 1]]
        self.assertEqual(updates.github_asset(row, {"assets": files}), ("Lantern.Release.2.1.zip", "u1"))
        self.assertIsNone(updates.github_asset({"archive": "renamed.zip"}, {"assets": files}))      # two archives, neither named so
        self.assertEqual(updates.github_asset({"archive": ""}, {"assets": files[1:]}), ("Lantern.Extras.2.1.zip", "u2"))
        self.assertIsNone(updates.github_asset(row, {"assets": [["notes.txt", "u3", 1]]}))


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
        # MO2's word is passed on only where it says something: both plain numbers, and MO2's the higher. A version
        # MO2 made up from a file's date, or a lower one, is left out.
        for mine, theirs in (("d2025.1.9.0", "0.8.0.0"), ("1.3", "1.2"), ("1.2", "1.2.0.0"), ("", "2.0")):
            self.assertNotIn("MO2's own last check", updates.verdict(self.row(mo2_newest=theirs, version=mine), {"nexus": {}, "github": {}})["text"], (mine, theirs))
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
            self.assertTrue(url.startswith(("https://api.nexusmods.com/v1/", "https://api.nexusmods.com/v2/graphql", "https://api.github.com/")), url)
            self.assertNotIn("INVENTEDKEY", url)
            self.assertEqual("APIKEY" in headers, "/v1/" in url, url)             # the key goes to the service that needs it, and to no other
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
        self.assertIn("none is kept", out["nexus"]["why_stopped"])
        self.assertEqual([u for u, _h in self.net.asked if "/v1/" in u], [])            # the keyed service is not asked without a key
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


def public_service(mods: dict, game_id: int = 1704, asked: list | None = None):
    """A stand-in for Nexus's public service (TL01§29), answering the three questions ModTrap asks of it. `mods`:
    {mod number: {"updated": "2026-05-05T22:41:21Z", "status": "published", "files": [(file number, name, version,
    category number, time, group)]}}."""
    import re as _re

    def answer(query: str):
        if asked is not None:
            asked.append(query)
        if "game(domainName" in query:
            return 200, {}, {"data": {"game": {"id": game_id}}}
        if "legacyModsByDomain" in query:
            ids = [int(x) for x in _re.findall(r"modId: (\d+)", query)]
            return 200, {}, {"data": {"legacyModsByDomain": {"nodes": [
                {"modId": i, "gameId": game_id, "status": mods[i].get("status", "published"), "updatedAt": mods[i]["updated"]} for i in ids if i in mods]}}}
        if "modFiles" in query:
            out = {}
            for alias, mod_id in _re.findall(r'(m\d+): modFiles\(modId: "(\d+)"', query):
                out[alias] = [{"fileId": f[0], "name": f[6] if len(f) > 6 else f[1], "uri": f[1], "version": f[2], "categoryId": f[3], "date": f[4], "groupId": f[5], "sizeInBytes": str(f[7]) if len(f) > 7 else None, "sqid": f[8] if len(f) > 8 else None}
                              for f in mods[int(mod_id)]["files"]]
            return 200, {}, {"data": out}
        return 200, {}, {"errors": [{"message": "not a question this stand-in knows"}], "data": None}
    return answer


class WithoutAKey(unittest.TestCase):
    """MT44, WHY§108: Nexus's public service answers without a key. Which mods had a new file is asked fifty mods to
    a question; a mod's files only where the installed file is not plainly its newest."""

    T_OLD, T_NEW = 1774355307, 1778020881
    NEW = "2026-05-05T22:41:21Z"                      # T_NEW, as the service writes a mod's time

    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        row = lambda mod, mod_id, files, archive, **over: dict(Verdicts.row(self), mod=mod, mod_id=mod_id, files=files, archive=archive, **over)
        self.rows = [
            row("Quill", 4321, [735000], "Quill-4321-6-0-%d.zip" % self.T_OLD),                 # an older file of the main line
            row("Reed", 5000, [], "Reed-5000-2-0-%d.7z" % self.T_NEW),                          # its archive carries the mod's own newest time
            row("Thistle", 6000, [61], "Thistle Old Name.7z"),                                  # no time in the name; its file is current
            row("Gone", 7000, [71], "Gone-7000-1-0-%d.zip" % self.T_OLD),                       # no longer shown
            row("Patch of Quill", 4321, [736000], "Quill Patch-4321-1-0-%d.zip" % self.T_OLD)]  # a second file of the same mod, in another line
        self.mods = {
            4321: {"updated": self.NEW, "files": [(735000, "Quill-4321-6-0-%d.zip" % self.T_OLD, "6.0", 7, self.T_OLD, 42),
                                                  (749043, "Quill-4321-6-11-%d.zip" % self.T_NEW, "6.11", 1, self.T_NEW, 42),
                                                  (736000, "Quill Patch-4321-1-0-%d.zip" % self.T_OLD, "1.0", 3, self.T_OLD, 77)]},
            5000: {"updated": self.NEW, "files": [(900, "Reed-5000-2-0-%d.7z" % self.T_NEW, "2.0", 1, self.T_NEW, 5)]},
            6000: {"updated": self.NEW, "files": [(61, "Thistle-6000-1-0.7z", "1.0", 1, 100, 9), (62, "Thistle Extras.7z", "0.1", 3, self.T_NEW, 10)]}}
        self.net = FakeNet({})
        self.questions = []
        self.net.public = public_service(self.mods, asked=self.questions)

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def scan(self, store, **over):
        return updates.scan(self.rows, over.pop("key", ""), self.net, store, now=1_800_000_000 + over.pop("later", 0), pause=0, **over)

    def test_a_scan_needs_no_key_and_tells_each_mods_state(self):
        store = updates.load()
        out = self.scan(store)
        self.assertEqual((out["nexus"]["way"], out["nexus"]["why_stopped"], out["nexus"]["left"]), ("public", "", 0))
        states = {r["mod"]: updates.verdict(r, store) for r in self.rows}
        self.assertEqual({m: v["state"] for m, v in states.items()},
                         {"Quill": "update", "Reed": "current", "Thistle": "current", "Gone": "gone", "Patch of Quill": "current"})
        # The newer file is the newest current one of the installed file's own line, not any newer file of the mod.
        self.assertEqual((states["Quill"]["newest"], states["Quill"]["file_id"]), ("6.11", 749043))
        self.assertIn("nothing was uploaded after it", states["Reed"]["text"])
        # No key went anywhere, and only the public service was asked.
        for url, headers in self.net.asked:
            self.assertEqual(url, "https://api.nexusmods.com/v2/graphql")
            self.assertNotIn("APIKEY", headers)
            self.assertEqual(headers.get("Application-Name"), "ModTrap")
        # Files were asked for only where needed: not for Reed (plainly newest) nor for Gone.
        files_q = " ".join(q for q in self.questions if "modFiles" in q)
        self.assertEqual(sorted(set(re.findall(r'modId: "(\d+)"', files_q))), ["4321", "6000"])
        self.assertEqual(sum("legacyModsByDomain" in q for q in self.questions), 1)

    def test_a_second_scan_asks_for_files_only_where_something_was_uploaded_since(self):
        store = updates.load()
        self.scan(store)
        self.questions.clear()
        self.scan(store, later=86400)
        self.assertEqual([q for q in self.questions if "modFiles" in q], [])                    # nothing changed: no files asked for
        self.mods[6000]["updated"] = "2026-06-01T00:00:00Z"
        self.mods[6000]["files"].append((63, "Thistle-6000-1-1.7z", "1.1", 1, 1780272000, 9))
        self.mods[6000]["files"][0] = (61, "Thistle-6000-1-0.7z", "1.0", 4, 100, 9)
        self.questions.clear()
        self.scan(store, later=2 * 86400)
        self.assertEqual(re.findall(r'modId: "(\d+)"', " ".join(q for q in self.questions if "modFiles" in q)), ["6000"])
        v = updates.verdict(self.rows[2], store)
        self.assertEqual((v["state"], v["newest"]), ("update", "1.1"))

    def test_many_mods_go_fifty_to_a_question_and_a_few_to_a_question_for_files(self):
        rows, mods = [], {}
        for i in range(1, 121):
            rows.append(dict(Verdicts.row(self), mod="Mod %d" % i, mod_id=i, files=[i * 10], archive="renamed %d.7z" % i))
            mods[i] = {"updated": self.NEW, "files": [(i * 10, "x.7z", "1.0", 1, 100, i)]}
        qs = []
        self.net.public = public_service(mods, asked=qs)
        store = updates.load()
        out = updates.scan(rows, "", self.net, store, now=1_800_000_000, pause=0)
        self.assertEqual(sum("legacyModsByDomain" in q for q in qs), 3)                         # 50, 50, 20
        self.assertEqual(sum("modFiles" in q for q in qs), 24)                                  # 120 mods, five to a question
        self.assertEqual((out["nexus"]["asked"], out["nexus"]["left"]), (120, 0))
        self.assertEqual({updates.verdict(r, store)["state"] for r in rows}, {"current"})

    def test_where_the_public_service_is_not_there_the_key_serves_and_without_one_it_is_said(self):
        self.net.public = lambda q: (500, {}, None)
        out = self.scan(updates.load())
        self.assertEqual(out["nexus"]["way"], "key")
        self.assertIn("answered with an error (500)", out["nexus"]["why_stopped"])
        self.assertIn("none is kept", out["nexus"]["why_stopped"])
        self.net.answers = {"/mods/updated?period=1m": (200, {}, []),
                            "/files": (200, {}, files_answer([(735000, "a.zip", "6.0", 1, 100)]))}
        out = self.scan(updates.load(), key="INVENTEDKEY0123456789")
        self.assertEqual((out["nexus"]["way"], out["nexus"]["asked"] > 0), ("key", True))
        # A service that asks to wait part way stops the scan, keeps what it has, and says so.
        n = [0]
        base = public_service(self.mods)

        def tiring(q):
            n[0] += 1
            return (429, {}, None) if "modFiles" in q else base(q)
        self.net.public = tiring
        out = self.scan(updates.load())
        self.assertEqual(out["nexus"]["way"], "public")
        self.assertIn("asks ModTrap to wait", out["nexus"]["why_stopped"])
        self.assertGreater(out["nexus"]["left"], 0)

    def test_a_game_name_that_could_carry_more_than_a_name_is_not_put_into_a_question(self):
        rows = [dict(Verdicts.row(self), game='x") { id } } #', mod_id=1)]
        qs = []
        self.net.public = public_service({}, asked=qs)
        updates.scan(rows, "", self.net, updates.load(), now=1_800_000_000, pause=0)
        self.assertEqual([q for q in qs if "#" in q or "x\")" in q], [])


class TheDownloadsOwnName(unittest.TestCase):
    """WHY§110: Nexus's public service may give a storage code where a file's name is expected. The file is then
    shown by its name on the mod's page, and its download is known by the browser's mark on it, or by the mod's
    number and the upload's time in the name the site gives the download."""

    T_OLD, T_NEW = 1774355307, 1778020881

    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.browser = Path(self.tmp.name) / "Browser Downloads"
        self.browser.mkdir()
        self.up = updating.Updating(net=FakeNet({}))
        self.up.set_downloads_folder(str(self.browser))
        self.model = types.SimpleNamespace(instance=types.SimpleNamespace(downloads_dir=None))
        self.staged = []
        self.row = dict(Verdicts.row(self), mod="Quill", mod_id=4321, files=[735000], archive="Quill-4321-6-0-%d.zip" % self.T_OLD)

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def verdict(self, uri="ab/cd/ef/0123456789abcdef", page_name="Quill Main File"):
        kept = {"files": [[735000, "Quill-4321-6-0-%d.zip" % self.T_OLD, "6.0", 7, self.T_OLD, 42, "Quill Main File"],
                          [749043, uri, "6.11", 1, self.T_NEW, 42, page_name]], "chain": [], "asked": 1}
        return updates.nexus_verdict(self.row, kept)

    def looks(self, times=3):
        stage = lambda path, name, mod, version, meta: self.staged.append((name, mod, version, meta)) or {"id": "s%d" % len(self.staged), "name": mod}
        for _ in range(times):
            self.up._looked = 0
            self.up.look(self.model, stage)

    def test_a_storage_code_is_never_shown_or_waited_for_as_a_files_name(self):
        v = self.verdict()
        self.assertEqual((v["state"], v["file"], v["file_name"], v["time"], v["file_id"]), ("update", "Quill Main File", "", self.T_NEW, 749043))
        self.assertNotIn("ab/cd", v["text"])
        self.assertEqual(self.verdict(page_name="")["file"], "the mod's newer file")                 # no name on the page either
        v = self.verdict(uri="Quill-4321-6-11-%d.zip" % self.T_NEW)
        self.assertEqual(v["file_name"], "Quill-4321-6-11-%d.zip" % self.T_NEW)                     # a real name is kept as before
        self.assertEqual(updates.how_to_get(self.row, self.verdict(), {}, True, True)["name"], "Quill Main File")

    def test_the_download_is_known_by_the_mods_number_and_the_uploads_time_in_its_name(self):
        self.up._expect(self.row, self.verdict())
        data = a_zip({"readme.txt": b"x"})
        fx.write(self.browser / ("Quill-4321-6-0-%d.zip" % self.T_OLD), data)                       # the installed file, downloaded again
        fx.write(self.browser / ("Reed-5000-6-11-%d.zip" % self.T_NEW), data)                       # another mod's
        fx.write(self.browser / "Unrelated.zip", data)
        self.looks()
        self.assertEqual((self.staged, list(self.up.waiting)), ([], ["Quill"]))
        fx.write(self.browser / ("A Name Nobody Told-4321-6-11-%d (1).zip" % self.T_NEW), data)
        self.looks()
        self.assertEqual([(n, m, v) for n, m, v, _ in self.staged], [("A Name Nobody Told-4321-6-11-%d (1).zip" % self.T_NEW, "Quill", "6.11")])
        self.assertEqual(self.staged[0][3], {"mod_id": 4321, "file_id": 749043, "version": "6.11"})
        self.assertEqual((self.up.waiting, self.up.fetching["Quill"]["state"]), ({}, "done"))

    def test_the_download_is_known_by_the_browsers_mark_whatever_its_name(self):
        self.up._expect(self.row, self.verdict())
        other = dict(self.row, mod="Reed", mod_id=5000, archive="Reed-5000-1-0-%d.zip" % self.T_OLD)
        self.up._expect(other, dict(self.verdict(), file_id=901))
        mark = "[ZoneTransfer]\r\nZoneId=3\r\nReferrerUrl=https://www.nexusmods.com/skyrimspecialedition/mods/%d?tab=files&file_id=1\r\nHostUrl=https://cdn.example.invalid/x\r\n"
        marks = {"renamed.zip": mark % 4321, "elsewhere.zip": mark % 9999}
        self.up.mark_reader = lambda path: marks.get(Path(path).name, "")
        data = a_zip({"readme.txt": b"x"})
        fx.write(self.browser / "elsewhere.zip", data)                                               # from another mod's page: nobody's
        fx.write(self.browser / "renamed.zip", data)
        self.looks()
        self.assertEqual([(n, m) for n, m, _v, _ in self.staged], [("renamed.zip", "Quill")])
        self.assertEqual(list(self.up.waiting), ["Reed"])

    def test_the_download_is_known_by_the_files_own_code_in_its_name(self):
        """TL01§31: the site names a download "<name> <mod's number> <version> <date> <code>.zip"; the code is the
        file's own, and the public service gives it."""
        self.up._expect(self.row, dict(self.verdict(), size=0, time=0, code="Zx9InventedQ"))
        data = a_zip({"readme.txt": b"x"})
        fx.write(self.browser / "Quill Main File 4321 6.10 2026-11-01T10-00Z Aa1OtherCode.zip", data)      # another file of the mod
        fx.write(self.browser / "Reed 5000 1.0 2026-11-01T10-00Z Zx9InventedQ.zip", data)                   # the code, another mod's number
        self.looks()
        self.assertEqual(self.staged, [])
        fx.write(self.browser / "Quill Main File 4321 6.11 2026-11-14T12-13Z Zx9InventedQ(1).zip", data)
        self.looks()
        self.assertEqual([(n, m) for n, m, _v, _ in self.staged], [("Quill Main File 4321 6.11 2026-11-14T12-13Z Zx9InventedQ(1).zip", "Quill")])

    def test_a_download_in_progress_is_told_with_how_far_it_is(self):
        """WHY§113: what is being written is shown while it comes, by the file's own size, not the folder's listing."""
        v = dict(self.verdict(), size=1000)
        self.up._expect(self.row, v)
        fx.write(self.browser / "anything.zip.part", b"x" * 400)
        self.looks(1)
        saw = self.up.waiting["Quill"]["saw"]
        self.assertIn("a download is being written in your browser's Downloads folder", saw)
        self.assertIn("40%", saw)
        self.assertEqual(self.staged, [])
        account = {m: w.get("saw") for m, w in self.up.waiting.items()}
        self.assertEqual(list(account), ["Quill"])

    def test_one_mod_waited_for_takes_an_archive_named_as_its_file_is_on_the_page(self):
        self.up._expect(self.row, self.verdict())
        data = a_zip({"readme.txt": b"x"})
        fx.write(self.browser / "Something Else Entirely.zip", data)
        self.looks()
        self.assertEqual(self.staged, [])
        fx.write(self.browser / "Quill Main File 6.11.zip", data)
        self.looks()
        self.assertEqual([(n, m) for n, m, _v, _ in self.staged], [("Quill Main File 6.11.zip", "Quill")])


class AnOlderVersionReplaced(unittest.TestCase):
    """MT49: a mod whose newer file is installed as another, enabled mod is shown as the older version it is, with
    no update asked for; the newer one is up to date."""

    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        mods = self.root / "mods"
        fx.write(mods / "Quill" / "meta.ini", meta(gameName="SkyrimSE", modid=4321, version="1.2", installationFile="Quill-4321-1-2.7z", files=[(4321, 111)]))
        self.net = FakeNet({})
        self.net.public = public_service({4321: {"updated": "2026-11-21T00:00:00Z", "files": [
            (111, "Quill-4321-1-2.7z", "1.2", 4, 1700000000, 42, "Quill", 1000), (113, "ab/cd/ef/0123456789abcdef", "1.4", 1, 1795219200, 42, "Quill", 2000)]}})
        self.api = api.Api()
        self.api.updating.net = self.net
        self.api.running = lambda image: False
        self.api.open(str(self.root), wait=True)

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def state(self):
        end = time.time() + 10
        while time.time() < end:
            st = self.api.get("/api/updates", {})[1]
            if st["scan"]["state"] != "going" and st["last"]:
                return st
            time.sleep(0.05)
        self.fail("the scan did not end")

    def test_the_older_version_is_told_as_such_and_the_newer_is_up_to_date(self):
        st = self.state()
        row = next(r for r in st["rows"] if r["mod"] == "Quill")
        self.assertEqual((row["state"], st["counts"]["update"], st["counts"]["replaced"]), ("update", 1, 0))
        # The newer file is installed as a mod of its own, enabled; the older one is disabled.
        from modtrap import profile
        new = self.root / "mods" / "Quill 1.4"
        fx.write(new / "Quill.esp", (self.root / "mods" / "Quill" / "Quill.esp").read_bytes())
        fx.write(new / "meta.ini", sources.own_record("0123456789abcdef.zip", {"game": "SkyrimSE", "mod_id": 4321, "file_id": 113, "version": "1.4"}))
        ml = self.root / "profiles" / "Default" / "modlist.txt"
        ml.write_bytes(ml.read_bytes().replace(b"+Quill\r\n", b"+Quill 1.4\r\n-Quill\r\n", 1))
        self.assertIn(b"-Quill\r\n", ml.read_bytes())
        self.api.open(str(self.root), wait=True)
        st = self.state()
        rows = {r["mod"]: r for r in st["rows"]}
        self.assertEqual((rows["Quill"]["state"], rows["Quill"]["get"], rows["Quill"]["enabled"]), ("replaced", "", False))
        self.assertEqual(rows["Quill"]["text"], "Its newer file (1.4) is installed as “Quill 1.4”, which is enabled. This older version is disabled and kept")
        self.assertEqual((rows["Quill 1.4"]["state"], rows["Quill 1.4"]["version"]), ("current", "1.4"))
        self.assertEqual((st["counts"]["update"], st["counts"]["replaced"]), (0, 1))
        # A favourite's mark goes on to the newer version (MT53): where both carry it, only the newer one shows it.
        self.api.post("/api/updates/favourite", {"mod": "Quill", "on": True})
        self.api.post("/api/updates/favourite", {"mod": "Quill 1.4", "on": True})
        st = self.api.get("/api/updates", {})[1]
        self.assertEqual(({r["mod"]: r["fav"] for r in st["rows"] if r["mod"].startswith("Quill")}, st["counts"]["fav"]), ({"Quill": False, "Quill 1.4": True}, 1))
        self.api.post("/api/updates/favourite", {"mod": "Quill 1.4", "on": False})
        self.assertTrue(next(r for r in self.api.get("/api/updates", {})[1]["rows"] if r["mod"] == "Quill")["fav"])      # the older one alone keeps its own

    def test_the_time_of_upload_in_a_newer_file_name(self):
        self.assertEqual(updates.archive_time("Quill-4321-6-0-1774355307.zip"), 1774355307)
        self.assertEqual(updates.archive_time("Quill Main 4321 6.0 2026-11-14T12-13Z Ab1InventedX.zip"), 1794658439)      # the end of that minute
        self.assertEqual(updates.archive_time("Quill Main 4321 6.0 2026-11-14T12-13Z Ab1InventedX(1).zip"), 1794658439)
        self.assertEqual(updates.archive_time("Quill.zip"), 0)


class Favourites(Sources):
    """MT46: the owner's own mark on a mod, kept in ModTrap's folder for that modlist, shown and counted with the rows."""

    def test_a_mod_is_marked_and_unmarked_and_the_rows_tell(self):
        a = api.Api()
        a.running = lambda image: False
        a.updating.net = FakeNet({})
        a.open(str(self.root), wait=True)
        name = a.get("/api/updates", {})[1]["rows"][0]["mod"]
        self.assertEqual(a.get("/api/updates", {})[1]["counts"].get("fav", 0), 0)
        self.assertEqual(a.post("/api/updates/favourite", {"mod": name, "on": True})[1], {"favourite": True, "count": 1})
        st = a.get("/api/updates", {})[1]
        self.assertEqual(([r["mod"] for r in st["rows"] if r["fav"]], st["counts"]["fav"]), ([name], 1))
        self.assertEqual(list(sources.given_load()["favourites"].values()), [[sources.fold(name)]])
        a.post("/api/updates/favourite", {"mod": name, "on": False})
        st = a.get("/api/updates", {})[1]
        self.assertEqual(([r["mod"] for r in st["rows"] if r["fav"]], st["counts"]["fav"]), ([], 0))
        with self.assertRaises(api.Bad):
            a.post("/api/updates/favourite", {"mod": "No Such Mod", "on": True})


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
        self.assertEqual((code, got), (200, {"key": True, "premium": None}))        # the kind of account is asked at once; here Nexus gives no answer
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
        for _ in range(200):                                                      # the scan at launch: the public service, no key
            if a.get("/api/updates", {})[1]["scan"]["state"] != "going":
                break
            time.sleep(0.02)
        self.assertEqual({u for u, _h in a.updating.net.asked}, {"https://api.nexusmods.com/v2/graphql"})
        self.assertEqual([h for _u, h in a.updating.net.asked if "APIKEY" in h], [])
        a.post("/api/updates/key", {"key": "INVENTEDKEY0123456789abcdef"})
        for _ in range(200):                                                      # a scan begun at launch, if any
            if a.get("/api/updates", {})[1]["scan"]["state"] != "going":
                break
            time.sleep(0.02)
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
