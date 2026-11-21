"""Starting one of the modlist's tools through MO2 (DESIGN§16.8 step 5), with a stand-in for the tool."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, logbook
from modtrap.server import Bad

from ._fixtures import write
from .test_adding import invented

FAKE = str(Path(__file__).with_name("fake_tool.py"))
EXES = ("[customExecutables]\r\nsize=2\r\n1\\title=xEdit\r\n1\\binary=C:/Tools/SSEEdit64.exe\r\n1\\arguments=\r\n"
        "1\\workingDirectory=C:/Tools\r\n2\\title=Invented Patcher\r\n2\\binary=C:/Tools/Patcher.exe\r\n"
        "2\\arguments=\r\n2\\workingDirectory=C:/Tools\r\n")


class Tools(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        ini = (self.root / "ModOrganizer.ini").read_bytes().decode()
        (self.root / "ModOrganizer.ini").write_bytes((ini.split("[customExecutables]")[0] + EXES).encode())
        write(self.root / "ModOrganizer.exe", b"not a real program")
        self.commands: list[list[str]] = []
        self.api = api.Api()
        self.api.poll = 0.03
        self.api.running = lambda image: None
        self.api.launcher = self.launch
        self.api.open(str(self.root), wait=True)

    def tearDown(self) -> None:
        if self.api.tooljob is not None:
            self.api.tooljob.join(10)
        for _ in range(300):
            if self.api.status == "ready":
                break
            time.sleep(0.02)
        os.environ.pop("FAKE_TOOL_WRITES", None)
        os.environ.pop("FAKE_TOOL_SECONDS", None)
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def launch(self, cmd, cwd):
        self.commands.append(cmd)
        return subprocess.Popen([sys.executable, FAKE], cwd=cwd)

    def ended(self) -> dict:
        self.api.tooljob.join(10)
        return self.api.state()["tool"]

    def test_the_tool_is_started_the_way_mo2_runs_it_and_its_output_is_seen(self) -> None:
        os.environ["FAKE_TOOL_WRITES"] = str(self.root / "mods" / "Tool Output" / "Generated.esp")
        got = self.api.post("/api/tool/start", {"title": "Invented Patcher"})[1]
        self.assertIn(got["state"], ("starting", "running"))
        t = self.ended()
        self.assertEqual(self.commands[0][1:], ["-p", "Default", "run", "-e", "Invented Patcher"])
        self.assertTrue(self.commands[0][0].endswith("ModOrganizer.exe"))
        self.assertEqual((t["state"], t["changed"], t["output_mod"]), ("done", ["Tool Output/Generated.esp"], "Tool Output"))

    def test_a_tool_that_wrote_nothing_is_said_so(self) -> None:
        self.api.post("/api/tool/start", {"title": "Invented Patcher"})
        t = self.ended()
        self.assertEqual((t["state"], t["changed_count"]), ("done", 0))

    def test_only_a_tool_of_this_mo2_and_one_at_a_time(self) -> None:
        with self.assertRaises(Bad):
            self.api.post("/api/tool/start", {"title": "Not Set Up"})
        with self.assertRaises(Bad):
            self.api.post("/api/tool/start", {})
        os.environ["FAKE_TOOL_SECONDS"] = "0.6"
        self.api.post("/api/tool/start", {"title": "Invented Patcher"})
        with self.assertRaises(Bad):
            self.api.post("/api/tool/start", {"title": "xEdit"})
        with self.assertRaises(Bad):
            self.api.post("/api/dryrun/start", {"mods": ["Quill"]})

    def test_waiting_can_be_stopped(self) -> None:
        os.environ["FAKE_TOOL_SECONDS"] = "1.5"
        self.api.post("/api/tool/start", {"title": "Invented Patcher"})
        self.api.post("/api/tool/stop", {})
        self.assertEqual(self.ended()["state"], "stopped")

    def test_the_add_steps_name_the_tool_to_start(self) -> None:
        for _ in range(300):
            got = self.api.post("/api/add", {"mods": ["Thistle"]})[1]
            if not got["looking"]:
                break
            time.sleep(0.02)
        st = next(s for s in got["steps"] if s["key"] == "tool:Invented Patcher")
        self.assertEqual([i.get("start") for i in st["items"]], ["Invented Patcher"])


if __name__ == "__main__":
    unittest.main()
