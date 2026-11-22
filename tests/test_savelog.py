""""Save this session" (WHY§48): what is collected, how it is cleaned, and the download."""

from __future__ import annotations

import http.client
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from modtrap import api, logbook, savelog, server

from . import _fixtures as fx
from .test_sevenz import read_back

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


class Cleaning(unittest.TestCase):
    def setUp(self) -> None:
        self.c = savelog.Cleaner({"<modlist>": "C:\\Modlists\\Example List", "<game>": "C:\\Games\\Invented Game"},
                                 home="C:\\Accounts\\Tester", user="Tester")

    def test_known_folders_become_placeholders_whatever_the_slash_or_case(self) -> None:
        self.assertEqual(self.c.text("out=C:\\Modlists\\Example List\\profiles\\Default\\x.tsv"),
                         "out=<modlist>\\profiles\\Default\\x.tsv")
        self.assertEqual(self.c.text("c:/modlists/example list/mods/A"), "<modlist>/mods/A")
        self.assertEqual(self.c.text("C:\\\\Modlists\\\\Example List\\\\mods"), "<modlist>\\\\mods")      # as JSON writes it
        self.assertEqual(self.c.text("C:\\Accounts\\Tester\\AppData\\Local\\ModTrap"), "<home>\\AppData\\Local\\ModTrap")

    def test_any_other_absolute_path_keeps_only_its_last_part(self) -> None:
        self.assertEqual(self.c.text("C:\\Tools\\SSEEdit 4\\SSEEdit64.exe started"), "<path>/SSEEdit64.exe started")
        self.assertEqual(self.c.text("\\\\nas\\share\\mods\\thing.7z"), "<path>/thing.7z")
        self.assertEqual(self.c.text("C:\\Other\\tester\\Desktop\\x.txt"), "<path>/x.txt")
        self.assertEqual(self.c.text("bare C:\\"), "bare <path>")
        self.assertEqual(self.c.text("/mnt/games/tester/mods/x.esp"), "<path>/x.esp")

    def test_the_user_name_is_replaced_only_as_part_of_a_path(self) -> None:
        self.assertEqual(self.c.text("Tester said user tester is fine"), "Tester said user tester is fine")
        self.assertEqual(self.c.text("<mods>/Tester/file.txt"), "<mods>/<user>/file.txt")
        user = savelog.Cleaner({}, home="C:\\Accounts\\User", user="User")
        self.assertEqual(user.text("the user ticked a mod; user: yes"), "the user ticked a mod; user: yes")

    def test_what_is_not_a_path_is_left_alone(self) -> None:
        for t in ("see https://example.org/a/b", "at 12:30:05 / done", "Skyrim.esm, Quill.esp", "a/b and c\\d", "ratio 3:1/2"):
            self.assertEqual(self.c.text(t), t)

    def test_json_stays_json_and_keys_are_cleaned_too(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_text(json.dumps({"folder": "C:\\Modlists\\Example List\\mods", "C:\\Accounts\\Tester\\k": [1, None, {"p": "C:\\x\\y.esp"}],
                                     "odd": "\ud83d"}), encoding="utf-8")
            out = b"".join(savelog.clean_blocks(p, self.c))
            got = json.loads(out.decode("utf-8"))
            self.assertEqual(got["folder"], "<modlist>\\mods")
            self.assertEqual(got["<home>\\k"], [1, None, {"p": "<path>/y.esp"}])
            self.assertIn(b"\\ud83d", out)                          # a lone surrogate does not fail the save
            self.assertNotIn(b"Tester", out)

    def test_a_json_that_does_not_parse_is_cleaned_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_bytes(b'{"folder": "C:\\\\Modlists\\\\Example List\\\\mods", torn')
            self.assertEqual(b"".join(savelog.clean_blocks(p, self.c)), b'{"folder": "<modlist>\\\\mods", torn')

    def test_jsonl_is_cleaned_line_by_line_and_a_torn_last_line_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.jsonl"
            p.write_bytes(b'{"mod": "A", "path": "C:\\\\Accounts\\\\Tester\\\\a"}\n{"mod": "B"}\n{"path": "C:\\\\Accounts\\\\Tester\\\\b", "to')
            lines = b"".join(savelog.clean_blocks(p, self.c)).decode().split("\n")
            self.assertEqual(json.loads(lines[0]), {"mod": "A", "path": "<home>\\a"})
            self.assertEqual(json.loads(lines[1]), {"mod": "B"})
            self.assertEqual(lines[2], '{"path": "<home>\\\\b", "to')

    def test_a_large_text_is_cleaned_in_blocks_cut_at_line_ends(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "big.log"
            line = "reading C:\\Modlists\\Example List\\mods\\Some Mod\\plugin.esp now\r\n"
            p.write_bytes((line * 6000).encode())                  # several blocks; the path falls on block ends
            blocks = list(savelog.clean_blocks(p, self.c))
            self.assertGreater(len(blocks), 3)
            out = b"".join(blocks).decode()
            self.assertEqual(out, "reading <modlist>\\mods\\Some Mod\\plugin.esp now\r\n" * 6000)

    def test_a_file_still_growing_is_taken_as_it_was_when_opened(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "grow.log"
            p.write_bytes(b"first\n" * 20000)
            it = savelog.clean_blocks(p, self.c)
            head = next(it)
            with open(p, "ab") as f:
                f.write(b"later\n" * 50000)
            out = head + b"".join(it)
            self.assertEqual(out, b"first\n" * 20000)

    def test_a_text_that_cannot_be_cleaned_is_left_out_not_passed_through(self) -> None:
        self.c._masks = [(None, "<x>")]                             # a cleaner that breaks
        self.assertEqual(self.c.text("C:\\Accounts\\Tester\\secret"), savelog.LEFT_OUT)


class Saving(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")
        self.api = api.Api()
        self.api.poll = 0.03
        self.api.running = lambda image: None
        self.api.launcher = lambda cmd, cwd: subprocess.Popen([sys.executable, FAKE, *cmd[1:]], cwd=cwd)
        self.app = server.App(self.api)
        self.httpd = server.Server(0, self.app)
        self.port = self.httpd.port
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.api.open(str(self.root), wait=True)

    def tearDown(self) -> None:
        self.api.saver.join(20)
        self.api.saver.close()
        self.httpd.shutdown()
        self.httpd.server_close()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def get(self, path: str, token: bool = True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": "127.0.0.1:%d" % self.port}
        if token:
            headers[server.TOKEN_HEADER] = self.app.token
        conn.request("GET", path, headers=headers)
        r = conn.getresponse()
        body = r.read()
        conn.close()
        return r, body

    def packed(self) -> dict:
        self.api.post("/api/save/start", {})
        self.api.saver.join(30)
        return self.api.state()["save"]

    def download(self) -> dict[str, bytes]:
        r, body = self.get(server.SAVE_PATH)
        self.assertEqual(r.status, 200)
        self.assertIn("attachment", r.getheader("Content-Disposition"))
        p = Path(self.tmp.name) / "got.7z"
        p.write_bytes(body)
        return read_back(p)

    def test_the_session_is_packed_cleaned_and_downloaded_once(self) -> None:
        self.api.post("/api/dryrun/start", {"mods": ["Bramble"]})
        self.api.job.join(20)
        s = self.packed()
        self.assertEqual(s["state"], "ready", s)
        self.assertTrue(s["name"].startswith("ModTrap-Example-List-") and s["name"].endswith(".7z"))
        self.assertEqual(s["done"], s["total"])
        files = self.download()
        names = set(files)
        self.assertTrue({"about.json", "log.txt", "session/session.json", "profile/modlist.txt", "profile/plugins.txt",
                         "profile/loadorder.txt", "modtrap/settings.json"} <= names, names)
        job = self.api.job.id
        for part in ("job.json", "manifest.json", "report.tsv", "progress.txt", "plugins.txt", "result.json",
                     "script/modtrap-job.txt"):
            self.assertIn("jobs/%s/%s" % (job, part), names)
        # Nothing of a mod's content, and nothing that is not a text record.
        self.assertFalse([n for n in names if n.lower().endswith((".esp", ".esm", ".esl", ".pas", ".7z"))])
        self.assertFalse([n for n in names if "/safe/" in n and not n.endswith("manifest.json")])
        # No folder of the owner's is left in any file.
        home = str(Path(self.tmp.name))
        for name, data in files.items():
            self.assertNotIn(home.encode(), data, name)
            self.assertNotIn(home.replace("/", "\\\\").encode(), data, name)
        self.assertIn(b"out=<modtrap>/sessions/", files["jobs/%s/script/modtrap-job.txt" % job])
        about = json.loads(files["about.json"])
        # A summary that holds a quoted path inside a text (a tool's own arguments) is cleaned value by value: cleaned
        # as plain text, the backslash of the escaped quote was taken for part of the path and the file broke.
        cleaner = savelog.Cleaner([], user="")
        text = json.dumps({"xedit": {"own_arguments": '-D:"C:\\Invented\\Data" -pseudoesl'}})
        back = json.loads(savelog._clean_text_item("about.json", text, cleaner))
        self.assertEqual(back["xedit"]["own_arguments"], '-D:"<path>/Data" -pseudoesl')
        self.assertEqual((about["name"], about["modlist"]["mods"], about["session"]["name"]), ("ModTrap", 7, "Example List"))
        self.assertEqual(json.loads(files["session/session.json"])["folder"], "<modlist>")
        self.assertIn(b"+Bramble", files["profile/modlist.txt"])
        # Handed out once, then gone from the disk.
        self.assertEqual(self.get(server.SAVE_PATH)[0].status, 404)
        self.assertEqual(list(Path(tempfile.gettempdir()).glob("modtrap-save-*.7z")), [])

    def test_the_download_needs_this_pages_token(self) -> None:
        self.packed()
        self.assertEqual(self.get(server.SAVE_PATH, token=False)[0].status, 403)
        self.assertEqual(self.get(server.SAVE_PATH)[0].status, 200)

    def test_a_second_press_while_packing_is_ignored_and_a_stale_archive_goes(self) -> None:
        gate = threading.Event()
        started = self.api.saver.start(lambda: (gate.wait(5), ([("a.txt", "x")], savelog.Cleaner({}), "a.7z"))[1])
        self.assertTrue(started)
        self.assertFalse(self.api.saver.start(lambda: ([], savelog.Cleaner({}), "b.7z")))
        gate.set()
        self.api.saver.join(10)
        first = self.api.saver._path
        self.assertTrue(first.is_file())
        self.packed()                                               # pressed again without downloading
        self.assertFalse(first.exists())

    def test_nothing_to_save_is_said_and_no_archive_is_left(self) -> None:
        self.api.saver.start(lambda: ([("empty.txt", "")], savelog.Cleaner({}), "x.7z"))
        self.api.saver.join(10)
        s = self.api.saver.public()
        self.assertEqual(s["state"], "nothing")
        self.assertIsNone(self.api.saver.take())

    def test_a_file_that_cannot_be_opened_is_passed_over(self) -> None:
        gone = Path(self.tmp.name) / "gone.log"
        self.api.saver.start(lambda: ([("gone.log", gone), ("here.txt", "kept")], savelog.Cleaner({}), "x.7z"))
        self.api.saver.join(10)
        path, _name = self.api.saver.take()
        self.assertEqual(read_back(path), {"here.txt": b"kept"})
        path.unlink()


if __name__ == "__main__":
    unittest.main()
