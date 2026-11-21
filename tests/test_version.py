"""The version and the take-over between two starts (WHY§68)."""

from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from modtrap import handover, server, version
from modtrap.server import Bad


class TheVersion(unittest.TestCase):
    def test_the_version_was_raised_after_the_last_change(self) -> None:
        """Every change to ModTrap's files gets a version of its own: run `python3 tools/bump.py` before a commit."""
        number, mark = version.recorded()
        self.assertRegex(number, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(mark, version.code_mark(), "ModTrap's files changed without a new version: run tools/bump.py")

    def test_the_mark_is_of_contents_not_of_dates_or_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "xedit").mkdir()
            (root / "a.py").write_bytes(b"one\ntwo\n")
            (root / "xedit" / "Script.pas").write_bytes(b"begin\nend.\n")
            (root / version.RECORD).write_text(json.dumps({"version": "1.2.3", "mark": "x"}), encoding="utf-8")
            first = version.code_mark(root)
            os.utime(root / "a.py", (1, 1))                                  # unpacked again: other dates
            (root / "xedit" / "Script.pas").write_bytes(b"begin\r\nend.\r\n")   # checked out with other line endings
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "a.cpython-313.py").write_bytes(b"made by Python")
            (root / "notes.txt").write_bytes(b"not a file of the program")
            (root / version.RECORD).write_text(json.dumps({"version": "1.2.4", "mark": "y"}), encoding="utf-8")
            self.assertEqual(version.code_mark(root), first)
            self.assertEqual(version.recorded(root), ("1.2.4", "y"))
            (root / "xedit" / "Script.pas").write_bytes(b"begin\n  Say;\nend.\n")   # a newer script
            self.assertNotEqual(version.code_mark(root), first)
            (root / "xedit" / "Script.pas").write_bytes(b"begin\nend.\n")
            (root / "left_behind.py").write_bytes(b"a file of an older version, still in the folder")
            self.assertNotEqual(version.code_mark(root), first)
            (root / version.RECORD).write_bytes(b"not json")
            self.assertEqual(version.recorded(root), ("unknown", ""))

    def test_the_next_version(self) -> None:
        self.assertEqual((version.raised("0.3.9"), version.raised("0.3.10")), ("0.3.10", "0.3.11"))


class StandIn:
    """An API that only knows how to be asked to close."""

    def __init__(self) -> None:
        self.busy, self.asked, self.httpd = False, 0, None

    def handover(self):
        self.asked += 1
        if self.busy:
            raise Bad("in the middle of a job")
        return {"quit": True, "version": "0.0.1"}, lambda: threading.Thread(target=self.httpd.shutdown, daemon=True).start()

    def get(self, path, query):
        return 404, {}

    def post(self, path, body):
        return 404, {}, None


class OneAtATime(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = mock.patch.dict(os.environ, {"MODTRAP_HOME": self.tmp.name})
        env.start()
        self.addCleanup(env.stop)
        self.api = StandIn()
        self.app = server.App(self.api)
        self.httpd = server.Server(0, self.app)
        self.api.httpd = self.httpd
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self) -> None:
        self.httpd.shutdown()
        self.thread.join(5)
        self.httpd.server_close()

    def ask(self, headers: dict) -> tuple[int, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.port, timeout=5)
        try:
            conn.request("POST", handover.PATH, body=b"", headers=dict({"Content-Length": "0"}, **headers))
            r = conn.getresponse()
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
        finally:
            conn.close()

    def test_nothing_running_nothing_asked(self) -> None:
        self.assertEqual(handover.take_over(), ("none", "", ""))

    def test_a_new_start_makes_the_running_one_save_and_close(self) -> None:
        handover.note(self.httpd.port, self.app.handover)
        self.assertEqual(handover.running()["version"], version.VERSION)
        closing = threading.Thread(target=lambda: (self.thread.join(5), self.httpd.server_close()), daemon=True)
        closing.start()
        self.assertEqual(handover.take_over()[0], "quit")
        self.assertEqual(self.api.asked, 1)
        closing.join(5)
        handover.clear("another start's key")                     # only its own note is a start's to remove
        self.assertIsNotNone(handover.running())
        handover.clear(self.app.handover)
        self.assertIsNone(handover.running())

    def test_one_in_the_middle_of_a_job_is_left_alone(self) -> None:
        self.api.busy = True
        handover.note(self.httpd.port, self.app.handover)
        what, was, where = handover.take_over()
        self.assertEqual((what, was, where), ("busy", version.VERSION, "http://127.0.0.1:%d/" % self.httpd.port))
        self.assertIsNotNone(handover.running())                  # it still runs: its note stays

    def test_only_the_key_of_this_start_opens_it_and_never_a_page(self) -> None:
        key = {server.HANDOVER_HEADER: self.app.handover}
        self.assertEqual(self.ask({server.HANDOVER_HEADER: "a guess"})[0], 403)
        self.assertEqual(self.ask({})[0], 403)
        self.assertEqual(self.ask({server.TOKEN_HEADER: self.app.token})[0], 403)        # the page's token is not it
        self.assertEqual(self.ask(dict(key, Origin="http://127.0.0.1:%d" % self.httpd.port))[0], 403)   # a browser
        self.assertEqual(self.ask(dict(key, Host="example.invalid"))[0], 403)
        self.assertEqual(self.api.asked, 0)
        self.api.busy = True
        self.assertEqual(self.ask(key), (409, {"error": "in the middle of a job"}))

    def test_a_note_nobody_answers_for_is_cleared(self) -> None:
        handover.note(self.httpd.port, "the key of a start that was ended")
        self.assertEqual(handover.take_over()[0], "none")         # refused there: not ours to close
        self.assertIsNone(handover.running())
        self.assertEqual(self.api.asked, 0)


if __name__ == "__main__":
    unittest.main()
