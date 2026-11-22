"""Starting one of the modlist's tools through MO2 (DESIGN§16.8 step 5), with a stand-in for the tool."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from modtrap import api, instance, logbook, toolrun
from modtrap.server import Bad

from ._fixtures import write
from .test_adding import invented

FAKE = str(Path(__file__).with_name("fake_tool.py"))
EXES = ("[customExecutables]\r\nsize=2\r\n1\\title=xEdit\r\n1\\binary=C:/Tools/SSEEdit64.exe\r\n1\\arguments=\r\n"
        "1\\workingDirectory=C:/Tools\r\n2\\title=Invented Patcher\r\n2\\binary=C:/Tools/Patcher.exe\r\n"
        "2\\arguments=\r\n2\\workingDirectory=C:/Tools\r\n")
PANDORA = ("3\\title=Pandora Behaviour Engine+\r\n3\\binary=C:/Tools/Pandora Behaviour Engine+.exe\r\n"
           "3\\arguments=--tesv:\\\"C:/Games/Invented\\\" -o:\\\"C:/Lists/Invented/mods/Tool Output\\\"\r\n3\\workingDirectory=C:/Tools\r\n")


class Tools(unittest.TestCase):
    def setUp(self) -> None:
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = invented(Path(self.tmp.name) / "list")
        ini = (self.root / "ModOrganizer.ini").read_bytes().decode()
        (self.root / "ModOrganizer.ini").write_bytes((ini.split("[customExecutables]")[0] + EXES.replace("size=2", "size=3") + PANDORA).encode())
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
        os.environ.pop("FAKE_TOOL_UNTIL", None)
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
        self.assertEqual((t["profile"], t["hint"]), ("Default", ""))             # which MO2 profile it was given; no hint known

    def test_what_is_known_about_a_tool_that_wrote_nothing_is_said(self) -> None:
        """TL01§16: the patcher framework that closes without output most often could not build its patchers
        inside MO2. That is data, said as a hint, only when it wrote nothing."""
        ini = self.root / "ModOrganizer.ini"
        ini.write_bytes(ini.read_bytes().replace(b"title=Invented Patcher", b"title=Synthesis").replace(b"Patcher.exe", b"Synthesis.exe"))
        self.api.open(str(self.root), wait=True)
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        self.assertEqual(t["changed_count"], 0)
        self.assertIn("build them outside MO2", t["hint"])
        self.assertIn("Synthesis's own and has nothing to do with MO2's profiles", t["hint"])

    def test_a_tool_with_switches_of_its_own_runs_and_closes_by_itself(self) -> None:
        """WHY§84: the switches are added to the arguments MO2 has for the tool (MO2's -a replaces those), unless the
        owner's setting says no or the arguments carry them already."""
        self.api.post("/api/tool/start", {"title": "Pandora Behaviour Engine+"})
        t = self.ended()
        own = '--tesv:"C:/Games/Invented" -o:"C:/Lists/Invented/mods/Tool Output"'
        self.assertEqual(self.commands[0][1:], ["-p", "Default", "run", "-e", "-a", own + " --auto_run --auto_close",
                                                "Pandora Behaviour Engine+"])
        self.assertTrue(t["by_itself"])
        self.assertIn("to do its work and close by itself", "\n".join(x["text"] for x in logbook.lines_after(0)[0]))
        self.api.post("/api/settings", {"name": "tools_self", "value": False})
        self.api.post("/api/tool/start", {"title": "Pandora Behaviour Engine+"})
        self.assertFalse(self.ended()["by_itself"])
        self.assertEqual(self.commands[1][1:], ["-p", "Default", "run", "-e", "Pandora Behaviour Engine+"])
        self.assertEqual(toolrun.self_run_arguments("Pandora", "C:/Tools/Pandora.exe", "-ar -o:\"C:/x\""),
                         ('-ar -o:"C:/x" --auto_close', ["--auto_close"]))
        self.assertEqual(toolrun.self_run_arguments("Pandora", "C:/Tools/Pandora.exe", "--auto_close -ar"), ("", []))
        self.assertEqual(toolrun.self_run_arguments("Invented Patcher", "C:/Tools/Patcher.exe", ""), ("", []))

    def test_a_mo2_that_stops_at_a_message_after_the_tool_does_not_hold_the_run_up(self) -> None:
        """WHY§84, MO01§9: the tool has closed, MO2 shows “Failed to run” from one of its own plugins and stays. ModTrap
        closes that message, as a dry run does, and the run ends."""
        gone = Path(self.tmp.name) / "message closed"
        os.environ["FAKE_TOOL_UNTIL"] = str(gone)
        os.environ["FAKE_TOOL_WRITES"] = str(self.root / "mods" / "Tool Output" / "Generated.esp")
        calls = {"n": 0, "dismissed": 0}

        def running(image):
            calls["n"] += 1
            return 1 < calls["n"] <= 5                # not there before the start, then seen, then gone

        def dismiss(image):
            calls["dismissed"] += 1
            self.assertEqual(image, "ModOrganizer.exe")
            gone.write_bytes(b"")
            return True

        job = toolrun.ToolJob(instance.load(self.root), "Invented Patcher", [], launcher=self.launch, running=running,
                              poll=0.03, dismiss=dismiss, grace=0.1)
        job.start()
        job.join(10)
        self.assertEqual((job.state, job.changed), ("done", ["Tool Output/Generated.esp"]))
        self.assertGreaterEqual(calls["dismissed"], 1)
        self.assertIn("which ModTrap closed", "\n".join(x["text"] for x in logbook.lines_after(0)[0]))

    def test_a_mo2_that_waits_for_something_else_is_waited_for(self) -> None:
        """No message to close: ModTrap does not decide that the run is over while MO2 still stands."""
        os.environ["FAKE_TOOL_SECONDS"] = "0.8"
        calls = {"n": 0}

        def running(image):
            calls["n"] += 1
            return 1 < calls["n"] <= 3

        job = toolrun.ToolJob(instance.load(self.root), "Invented Patcher", [], launcher=self.launch, running=running,
                              poll=0.03, dismiss=lambda image: False, grace=0.05)
        job.start()
        time.sleep(0.4)
        self.assertEqual(job.state, "running")
        job.join(10)
        self.assertEqual(job.state, "done")

    def test_a_tools_own_log_is_read_after_its_run_and_kept_with_the_session(self) -> None:
        """WHY§88: where a tool keeps a log of its own, ModTrap reads the one written during the run it started,
        says which of the signs it knows show in it (data in tools.json), and keeps a copy for the session file."""
        tool_dir = Path(self.tmp.name) / "Tools" / "Framework"
        (tool_dir / "logs").mkdir(parents=True)
        (tool_dir / "logs" / "an older run.log").write_text("error NU1202: Package Mutagen.Invented 9.9 is not compatible with net1.0\n", encoding="utf-8")
        os.utime(tool_dir / "logs" / "an older run.log", (time.time() - 3600, time.time() - 3600))
        ini = self.root / "ModOrganizer.ini"
        ini.write_bytes(ini.read_bytes().replace(b"title=Invented Patcher", b"title=Synthesis")
                        .replace(b"C:/Tools/Patcher.exe", (tool_dir / "Synthesis.exe").as_posix().encode()))
        self.api.open(str(self.root), wait=True)
        lines = ["2026-01-01 10:00:00.000 +00:00 [INF] ============== Opening Synthesis v1.2.3 ==============",
                 "2026-01-01 10:00:01.000 +00:00 [INF] Swapped profile Invented to (Mutagen ==> Manual: 0.10.0 Newest:  ==> Manual)(Synthesis ==> Manual: 1.2.3 Newest:  ==> Manual)",
                 "2026-01-01 10:00:02.000 +00:00 [INF] Swapping to net8.0",
                 "2026-01-01 10:00:09.000 +00:00 [INF] Swapped profile Invented to (Mutagen ==> Manual: 0.11.0 Newest: 0.11.0 ==> Manual)(Synthesis ==> Manual: 1.3.0 Newest: 1.3.0 ==> Manual)",
                 "Invented.csproj : error NU1202: Package Mutagen.Invented 0.11.0 is not compatible with net8.0 (.NETCoreApp,Version=v8.0). Package Mutagen.Invented 0.11.0 supports:",
                 "Invented.csproj : error NU1202: Package Mutagen.Invented.Synthesis 1.3.0 is not compatible with net8.0 (.NETCoreApp,Version=v8.0).",
                 "2026-01-01 10:00:12.000 +00:00 [WRN] Encountered blocking overall error: \"Invented group\" has a blocking error"]
        real = self.launch

        def launch(cmd, cwd):                              # the tool writes its log while it runs
            (tool_dir / "logs" / "this run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
            return real(cmd, cwd)

        self.api.launcher = launch
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        own = t["own_log"]
        self.assertEqual((own["file"], own["kept"]), ("this run.log", True))
        said = [f["text"] for f in own["findings"]]
        self.assertIn("This is Synthesis 1.2.3.", said)
        self.assertTrue(any("were changed while it was open: Mutagen 0.10.0 with Synthesis 1.2.3, then Mutagen 0.11.0 with Synthesis 1.3.0" in x for x in said))
        self.assertTrue(any(x.startswith("2 line(s) of a library that does not fit, the last: Mutagen.Invented.Synthesis 1.3.0 cannot be used by a patcher built for net8.0") for x in said))
        self.assertEqual([f["level"] for f in own["findings"]], ["note", "note", "note", "error", "error"])
        kept = self.api.store.dir(self.api.session.id) / "tool-logs" / "Synthesis" / "this run.log"
        self.assertTrue(kept.is_file())
        self.assertFalse((kept.parent / "an older run.log").exists())             # not of this run: neither read nor kept
        self.assertIn("ModTrap read it", "\n".join(x["text"] for x in logbook.lines_after(0)[0]))
        # The session file holds it.
        from modtrap import savelog
        names = [n for n, _f in savelog.collect(self.api.store.dir(self.api.session.id), None, Path(self.tmp.name) / "home", {})]
        self.assertIn("tool-logs/Synthesis/this run.log", names)
        # A tool whose log ModTrap does not know has none read.
        self.assertIsNone(toolrun.toollog.after_run("Invented Patcher", "C:/Tools/Patcher.exe", 0, None))

    def _framework(self, versions=("0.11.0", "1.3.0"), how="Manual", log_lines=None) -> Path:
        """An invented patcher framework beside the list: its settings file with one profile, and its last log."""
        import json
        tool_dir = Path(self.tmp.name) / "Tools" / "Framework"
        (tool_dir / "logs").mkdir(parents=True, exist_ok=True)
        settings = {"Profiles": [{"$type": "Invented.Profile", "Nickname": "Invented", "ID": "abc", "MutagenVersioning": how,
                                  "MutagenManualVersion": versions[0], "SynthesisVersioning": how,
                                  "SynthesisManualVersion": versions[1], "Groups": [{"Name": "Invented group", "On": True, "Patchers": []}]},
                                 {"Nickname": "Another", "MutagenVersioning": "Match", "MutagenManualVersion": None,
                                  "SynthesisVersioning": "Match", "SynthesisManualVersion": None, "Groups": []}],
                    "SelectedProfile": "abc", "Kept": 1.5}
        (tool_dir / "PipelineSettings.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(settings, indent=2).replace("\n", "\r\n").encode())
        lines = log_lines if log_lines is not None else [
            "2026-01-01 10:00:00.000 +00:00 [INF] ============== Opening Synthesis v1.2.3 ==============",
            "2026-01-01 10:00:00.001 +00:00 [INF] Mutagen version: 0.10.0",
            "2026-01-01 10:00:00.002 +00:00 [INF] Synthesis version: 1.2.3",
            "2026-01-01 10:00:02.000 +00:00 [INF] Swapping to net8.0",
            "Invented.csproj : error NU1202: Package Mutagen.Bethesda.Invented 0.11.0 is not compatible with net8.0 (.NETCoreApp,Version=v8.0).",
            "Invented.csproj : error NU1202: Package Mutagen.Bethesda.Synthesis 1.3.0 is not compatible with net8.0 (.NETCoreApp,Version=v8.0)."]
        (tool_dir / "logs" / "the last run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        ini = self.root / "ModOrganizer.ini"
        ini.write_bytes(ini.read_bytes().replace(b"title=Invented Patcher", b"title=Synthesis")
                        .replace(b"C:/Tools/Patcher.exe", (tool_dir / "Synthesis.exe").as_posix().encode()))
        self.api.open(str(self.root), wait=True)
        return tool_dir

    def test_library_versions_the_frameworks_log_shows_as_not_fitting_are_set_right_before_it_starts(self) -> None:
        """MT27, WHY§89: the profile is still set to the versions the program's last log names as not fitting, and
        the same log states the versions the program was built with. ModTrap sets those, keeps the file as it was,
        records it, and starts the tool. Only that profile's four fields change."""
        import json
        from modtrap import toolfit
        tool_dir = self._framework()
        f = tool_dir / "PipelineSettings.json"
        before = f.read_bytes()
        self.assertEqual(toolfit.check(tool_dir), [{"profile": "Invented", "was": {"mutagen": "0.11.0", "synthesis": "1.3.0"},
                                                     "now": {"mutagen": "0.10.0", "synthesis": "1.2.3"}, "target": "net8.0",
                                                     "log": "the last run.log"}])
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        self.assertEqual(len(t["before"]), 1)
        self.assertIn("Mutagen 0.10.0, Synthesis 1.2.3", t["before"][0])
        now = f.read_bytes()
        self.assertTrue(now.startswith(b"\xef\xbb\xbf") and b"\r\n" in now)                # written as the file was
        was, new = json.loads(before.decode("utf-8-sig")), json.loads(now.decode("utf-8-sig"))
        self.assertEqual((new["Profiles"][0]["MutagenManualVersion"], new["Profiles"][0]["SynthesisManualVersion"],
                          new["Profiles"][0]["MutagenVersioning"]), ("0.10.0", "1.2.3", "Manual"))
        was["Profiles"][0].update(MutagenManualVersion="0.10.0", SynthesisManualVersion="1.2.3")
        self.assertEqual(new, was)                                                          # nothing else changed
        kept = list((self.api.store.dir(self.api.session.id) / "tool-settings").iterdir())
        self.assertEqual([k.read_bytes() for k in kept], [before])                           # the file as it was, kept
        events = self.api.get("/api/history", {})[1]["events"]
        self.assertEqual([e["kind"] for e in events[:2]], ["tool ran", "tool settings changed"])     # newest first
        ev = events[1]
        self.assertEqual((ev["was"], ev["now"]), ("Mutagen 0.11.0, Synthesis 1.3.0", "Mutagen 0.10.0, Synthesis 1.2.3"))
        # The profile now says what the log shows as fitting: a second start changes nothing.
        self.assertEqual(toolfit.check(tool_dir), [])
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        self.assertEqual(self.ended()["before"], [])
        self.assertEqual(f.read_bytes(), now)

    def test_library_versions_are_left_alone_without_the_proof_or_when_the_setting_is_off(self) -> None:
        from modtrap import toolfit
        # The log's errors name other versions than the profile is set to (set right by hand since): nothing to do.
        tool_dir = self._framework(versions=("0.10.5", "1.2.9"))
        self.assertEqual(toolfit.check(tool_dir), [])
        # No build error of that kind in the log: nothing to do, whatever the versions.
        tool_dir = self._framework(log_lines=["x [INF] Mutagen version: 0.10.0", "x [INF] Synthesis version: 1.2.3"])
        self.assertEqual(toolfit.check(tool_dir), [])
        # The log does not state the program's own versions: ModTrap does not know what to set, and sets nothing.
        tool_dir = self._framework(log_lines=["a.csproj : error NU1202: Package Mutagen.Bethesda.Synthesis 1.3.0 is not compatible with net8.0 (x)."])
        self.assertEqual(toolfit.check(tool_dir), [])
        # "Latest" with such errors in the log is set right too; a number for "Manual" stays a number.
        tool_dir = self._framework(how=1)
        self.assertEqual([(x["was"], x["now"]) for x in toolfit.check(tool_dir)],
                         [({"mutagen": "latest", "synthesis": "latest"}, {"mutagen": "0.10.0", "synthesis": "1.2.3"})])
        # The setting off: said, not set.
        before = (tool_dir / "PipelineSettings.json").read_bytes()
        self.api.post("/api/settings", {"name": "tool_versions", "value": False})
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        self.assertIn("Left as it is", t["before"][0])
        self.assertEqual((tool_dir / "PipelineSettings.json").read_bytes(), before)
        self.api.post("/api/settings", {"name": "tool_versions", "value": True})
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        self.ended()
        import json
        self.assertEqual(json.loads((tool_dir / "PipelineSettings.json").read_bytes().decode("utf-8-sig"))["Profiles"][0]["MutagenVersioning"], 3)

    def _outside(self, tool_dir: Path, records: list[Path], builds: bool, touch_settings: bool = False):
        """The framework opened by itself, outside MO2: it writes a log that names each patcher's build record,
        builds (the records appear) or fails, and stays open until its window is asked to close."""
        closed = Path(self.tmp.name) / "window closed"
        opened: list[list[str]] = []

        def launch(cmd, cwd):
            opened.append(cmd)
            lines = ["x [INF] Mutagen version: 0.10.0", "x [INF] Synthesis version: 1.2.3"]
            for r in records:
                lines += ["x [INF] Compiling RunnerRepoInfo { Project = TargetProject { SolutionPath = C:\\T\\Invented.sln }",
                          ", MetaPath = %s, CommitDate = 01/01/2026 }" % r]
                if builds:
                    r.parent.mkdir(parents=True, exist_ok=True)
                    r.write_bytes(b"built")
                else:
                    lines.append('x [WRN] error MSB6006: "csc.exe" exited with code -1073741819.')
            (tool_dir / "logs" / "opened outside.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
            if touch_settings:
                f = tool_dir / "PipelineSettings.json"
                f.write_bytes(f.read_bytes().replace(b'"Kept": 1.5', b'"Kept": 2.5'))
            return subprocess.Popen([sys.executable, FAKE], cwd=cwd, env=dict(os.environ, FAKE_TOOL_UNTIL=str(closed)))

        def ask_close(program):
            closed.write_bytes(b"")
            return True

        self.api.direct_launcher, self.api.ask_close = launch, ask_close
        self.api.prebuild_times = {"quiet": (0.1, 0.3, 1.0), "close_wait": 8.0}
        return opened

    def _last_log_names_unbuilt(self, tool_dir: Path) -> list[Path]:
        records = [Path(self.tmp.name) / "Temp" / "Framework" / name / "Build.meta" for name in ("one", "two")]
        lines = ["x [INF] Mutagen version: 0.10.0", "x [INF] Synthesis version: 1.2.3"]
        for r in records:
            lines += ["x [INF] Compiling RunnerRepoInfo { Project = TargetProject { SolutionPath = C:\\T\\Invented.sln }",
                      ", MetaPath = %s, CommitDate = 01/01/2026 }" % r, 'x [WRN] error MSB6006: "csc.exe" exited with code -1073741819.']
        (tool_dir / "logs" / "the last run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return records

    def test_patchers_that_are_not_built_are_built_outside_mo2_before_the_start(self) -> None:
        """MT28, WHY§90: the framework's last log names patcher builds whose record is not there. ModTrap opens the
        program by itself, waits for its log and the records to show every patcher built, closes it, and only then
        starts it through MO2. Its settings file is as before, even if the program wrote to it meanwhile."""
        from modtrap import toolfit
        tool_dir = self._framework(versions=("0.10.0", "1.2.3"))
        records = self._last_log_names_unbuilt(tool_dir)
        self.assertEqual(toolfit.unbuilt(tool_dir), {"log": "the last run.log", "named": 2, "missing": 2})
        settings = (tool_dir / "PipelineSettings.json").read_bytes()
        opened = self._outside(tool_dir, records, builds=True, touch_settings=True)
        got = self.api.post("/api/tool/start", {"title": "Synthesis"})[1]
        self.assertIn(got["state"], ("starting", "preparing"))
        with self.assertRaises(Bad):
            self.api.post("/api/dryrun/start", {"mods": ["Quill"]})                  # busy while it builds
        t = self.ended()
        self.assertEqual(t["state"], "done")
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0][0].endswith("Synthesis.exe") and len(opened[0]) == 1)       # by itself: no MO2, no arguments
        self.assertEqual(self.commands[0][1:], ["-p", "Default", "run", "-e", "Synthesis"])    # then through MO2
        self.assertTrue(all(r.is_file() for r in records))
        self.assertIn("opened it by itself, outside MO2, where it built them (2 of 2", t["before"][0])
        self.assertEqual((tool_dir / "PipelineSettings.json").read_bytes(), settings)          # put back as it was
        self.assertIsNone(toolfit.unbuilt(tool_dir))
        # Built now: the next start opens nothing outside MO2.
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        self.ended()
        self.assertEqual(len(opened), 1)

    def test_a_build_that_fails_outside_mo2_too_ends_there(self) -> None:
        tool_dir = self._framework(versions=("0.10.0", "1.2.3"))
        records = self._last_log_names_unbuilt(tool_dir)
        opened = self._outside(tool_dir, records, builds=False)
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        self.assertEqual((t["state"], len(opened), self.commands), ("failed", 1, []))          # no start through MO2
        self.assertIn("could not build its patchers outside MO2 either", t["message"])
        self.assertIn("the compiler crashing", t["message"])

    def test_the_owner_can_keep_the_framework_inside_mo2(self) -> None:
        tool_dir = self._framework(versions=("0.10.0", "1.2.3"))
        records = self._last_log_names_unbuilt(tool_dir)
        opened = self._outside(tool_dir, records, builds=True)
        self.api.post("/api/settings", {"name": "tool_prebuild", "value": False})
        self.api.post("/api/tool/start", {"title": "Synthesis"})
        t = self.ended()
        self.assertEqual((t["state"], opened, t["before"]), ("done", [], []))

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
