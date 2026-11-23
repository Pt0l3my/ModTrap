"""ModTrap's console window (MT63): hidden where it is ModTrap's own, shown by a setting, and left alone otherwise."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modtrap import __main__ as main_mod, api, console, logbook, selfupdate

ROOT = Path(__file__).resolve().parents[1]


class TheConsoleWindow(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def test_off_windows_there_is_no_window_to_hide(self):
        with mock.patch.object(console.sys, "platform", "linux"):
            self.assertEqual((console.own([console.SWITCH]), console.show(console.HIDE)), (False, False))

    def test_the_launcher_says_the_console_is_modtraps_own(self):
        with mock.patch.object(console.sys, "platform", "win32"):
            self.assertTrue(console.own(["--allow-changes", "--own-console"]))
        src = (ROOT / "tools" / "exe" / "launcher.c").read_text(encoding="utf-8")
        self.assertIn('*rest ? L"" : L" --own-console"', src)             # only a plain start: with words, the window is the asker's
        self.assertIn("si.wShowWindow = (WORD)(*rest ? SW_SHOWNORMAL : SW_HIDE);", src)
        self.assertIn("CREATE_NEW_CONSOLE", src)                         # hidden, but there: what ModTrap starts writes to it
        self.assertIn("--own-console", main_mod.main.__code__.co_consts)

    def test_the_setting_shows_and_hides_it_at_once_and_only_a_console_of_its_own(self):
        a = api.Api()
        self.assertFalse(a.settings()["console_window"])
        with mock.patch.object(console, "show") as show:
            a.post("/api/settings", {"name": "console_window", "value": True})
            show.assert_not_called()                                    # started from a command prompt: that window is the owner's
            a.own_console = True
            a.post("/api/settings", {"name": "console_window", "value": False})
            a.post("/api/settings", {"name": "console_window", "value": True})
            self.assertEqual([c.args for c in show.call_args_list], [(console.HIDE,), (console.MINIMISED,)])

    def test_modtrap_starts_itself_again_in_a_hidden_console_of_its_own(self):
        import inspect
        src = inspect.getsource(selfupdate.restart)
        self.assertIn("si.wShowWindow = console.HIDE", src)
        self.assertIn("args.append(console.SWITCH)", src)
        with mock.patch.object(selfupdate.subprocess, "Popen") as popen:   # elsewhere: as before, and no switch
            selfupdate.restart(Path(self.tmp.name), ["--allow-changes", "--port", "8737"])
        self.assertEqual(popen.call_args.args[0][1:], ["-m", "modtrap", "--allow-changes", "--port", "8737", "--no-browser"])

    def test_a_start_that_fails_is_shown_and_waits(self):
        with mock.patch.object(console, "show") as show, mock.patch("builtins.input", side_effect=EOFError):
            console.stay()
        show.assert_called_once_with(console.NORMAL)


if __name__ == "__main__":
    unittest.main()
