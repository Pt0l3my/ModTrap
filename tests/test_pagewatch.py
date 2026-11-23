"""ModTrap closes with its page and can be started from a page brought back (MT64)."""

import http.client
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from modtrap import api, logbook, pagewatch, server, startlink

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def go(self, seconds, watch=None, step=5.0):
        """Time passes, with the watcher looking as often as it does while ModTrap runs."""
        end = self.now + seconds
        while self.now < end:
            self.now = min(end, self.now + step)
            if watch is not None and self.now < end:
                watch.due()


class IsThePageStillOpen(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.w = pagewatch.Watch(self.clock)

    def test_nothing_closes_before_a_page_was_ever_open(self):
        self.clock.go(3600, self.w)
        self.assertEqual(self.w.due(), "")

    def test_a_page_that_says_goodbye_is_believed_after_a_few_seconds_and_a_reload_is_back_before(self):
        self.w.seen("page-one-mark")
        self.assertTrue(self.w.said("page-one-mark", "bye"))
        self.clock.go(3, self.w)
        self.assertEqual(self.w.due(), "")
        self.w.seen("page-two-mark")                               # the page loaded anew
        self.clock.go(60, self.w)
        self.assertEqual(self.w.due(), "")
        self.w.said("page-two-mark", "bye")
        self.clock.go(pagewatch.GRACE + 1, self.w)
        self.assertEqual(self.w.due(), "its page was closed")

    def test_two_tabs_one_closed(self):
        self.w.seen("page-one-mark")
        self.w.seen("page-two-mark")
        self.w.said("page-one-mark", "bye")
        for _ in range(20):
            self.clock.go(10, self.w)
            self.w.seen("page-two-mark")
        self.assertEqual((self.w.due(), self.w.pages()), ("", 1))

    def test_a_browser_ended_without_a_word_is_noticed_after_minutes(self):
        self.w.seen("page-one-mark")
        self.clock.go(pagewatch.SILENCE - 10, self.w)
        self.assertEqual(self.w.due(), "")
        self.clock.go(20, self.w)
        self.assertEqual(self.w.due(), "no page has asked anything for 4 minutes")

    def test_a_page_put_to_sleep_is_not_gone_and_a_pc_that_slept_ends_nothing(self):
        self.w.seen("page-one-mark")
        self.w.said("page-one-mark", "asleep")
        self.clock.go(7200, self.w)
        self.assertEqual(self.w.due(), "")
        self.w.seen("page-one-mark")                               # awake again: counted as any page
        self.clock.now += 8 * 3600                                 # the PC slept: no look in between
        self.assertEqual(self.w.due(), "")
        self.clock.go(pagewatch.SILENCE + 10, self.w)
        self.assertNotEqual(self.w.due(), "")

    def test_only_a_pages_own_mark_counts(self):
        self.w.seen("x")
        self.w.seen("../../etc")
        self.assertFalse(self.w.ever)
        self.assertFalse(self.w.said("page-one-mark", "anything"))


class FakeRegistry:
    """The few calls of winreg that are used, over a dict."""
    HKEY_CURRENT_USER, REG_SZ = "HKCU", 1

    def __init__(self):
        self.keys: dict[str, dict[str, str]] = {}

    class _Key:
        def __init__(self, values):
            self.values = values

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def OpenKey(self, root, path):
        if path not in self.keys:
            raise OSError("no such key")
        return self._Key(self.keys[path])

    def CreateKey(self, root, path):
        return self._Key(self.keys.setdefault(path, {}))

    def QueryValueEx(self, key, name):
        if name not in key.values:
            raise OSError("no such value")
        return key.values[name], self.REG_SZ

    def SetValueEx(self, key, name, _reserved, _kind, value):
        key.values[name] = value

    def DeleteKey(self, root, path):
        if any(k.startswith(path + "\\") for k in self.keys):
            raise OSError("it has keys under it")
        self.keys.pop(path, None)


class TheLinkThatStartsModTrap(unittest.TestCase):
    def test_the_entry_names_the_program_and_hands_on_nothing_of_the_link(self):
        reg, exe = FakeRegistry(), Path("C:/Tools/ModTrap/ModTrap.exe")
        self.assertTrue(startlink.enter(exe, reg))
        self.assertFalse(startlink.enter(exe, reg))                          # there already: nothing written
        cmd = startlink.entered(reg)
        self.assertEqual(cmd, '"%s" --from-page' % exe)
        self.assertNotIn("%", cmd)                                           # no "%1": the link's own words never reach the command line
        self.assertEqual(reg.keys[startlink.KEY], {"": "URL:ModTrap", "URL Protocol": ""})
        self.assertFalse(startlink.remove(Path("C:/Elsewhere/ModTrap.exe"), reg))       # another ModTrap's entry is left alone
        self.assertTrue(startlink.remove(exe, reg))
        self.assertEqual((startlink.entered(reg), reg.keys), ("", {}))
        self.assertFalse(startlink.enter(Path('C:/Odd "name"/ModTrap.exe'), reg))

    def test_off_windows_nothing_is_entered(self):
        with mock.patch.object(startlink.sys, "platform", "linux"):
            self.assertEqual((startlink.enter(Path("/x/ModTrap.exe")), startlink.entered(), startlink.remove()), (False, "", False))

    def test_the_launcher_takes_the_pages_start_as_a_plain_one(self):
        src = (ROOT / "tools" / "exe" / "launcher.c").read_text(encoding="utf-8")
        self.assertIn('plain = !*rest || wcscmp(rest, L"--from-page") == 0;', src)
        self.assertIn("si.wShowWindow = (WORD)(plain ? SW_HIDE : SW_SHOWNORMAL);", src)


class ThePagesLastWord(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.api = api.Api()
        self.app = server.App(self.api)
        self.httpd = server.Server(0, self.app)
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.host = "127.0.0.1:%d" % self.httpd.port

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def ask(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection(self.host, timeout=10)
        c.request(method, path, body=body, headers=dict({"Host": self.host}, **(headers or {})))
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, r.getheader("Content-Type", ""), data

    def test_the_worker_and_the_page_it_keeps_are_served_and_hold_nothing_of_modtraps_own(self):
        status, kind, worker = self.ask("GET", "/sw.js")
        self.assertEqual((status, kind), (200, "text/javascript; charset=utf-8"))
        self.assertIn(b'if (ev.request.mode !== "navigate") return;', worker)           # every other request goes to ModTrap untouched
        self.assertNotIn(b"__VERSION__", worker)
        self.assertNotIn(self.app.token.encode(), worker)
        status, kind, offline = self.ask("GET", "/offline")
        self.assertEqual((status, kind), (200, "text/html; charset=utf-8"))
        self.assertIn(b'location.assign("modtrap:start")', offline)
        self.assertNotIn(self.app.token.encode(), offline)                              # the kept page cannot ask ModTrap anything
        self.assertNotIn(b"__NONCE__", offline)
        self.assertIn("worker-src 'self'", server.CSP)

    def test_a_request_marks_its_page_and_the_goodbye_needs_the_token_and_the_pages_origin(self):
        origin = {"Origin": "http://" + self.host}
        self.ask("GET", "/api/state", headers={"X-ModTrap-Token": self.app.token, "X-ModTrap-Page": "page-one-mark"})
        self.assertEqual((self.app.watch.ever, self.app.watch.pages()), (True, 1))
        self.assertEqual(self.ask("POST", "/bye", "page=page-one-mark&what=bye&token=wrong", origin)[0], 403)
        self.assertEqual(self.ask("POST", "/bye", "page=page-one-mark&what=bye&token=" + self.app.token, {"Origin": "http://example.invalid"})[0], 403)
        self.assertEqual(self.app.watch.pages(), 1)
        self.assertEqual(self.ask("POST", "/bye", "page=page-one-mark&what=bye&token=" + self.app.token, origin)[0], 200)
        self.assertEqual(self.app.watch.pages(), 0)

    def test_modtrap_closes_only_with_nothing_in_hand_and_the_setting_on(self):
        closed = []
        self.api.on_quit = lambda: closed.append(True)
        self.api._listscan["state"] = "going"
        self.assertEqual((self.api.in_hand(), self.api.left_alone("its page was closed")), ("a scan of the modlist", None))
        self.api._listscan["state"] = "idle"
        self.api.post("/api/settings", {"name": "quit_with_page", "value": False})
        self.assertIsNone(self.api.left_alone("its page was closed"))
        self.api.post("/api/settings", {"name": "quit_with_page", "value": True})
        after = self.api.left_alone("its page was closed")
        self.assertIsNotNone(after)
        after()
        self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
