"""ModTrap updating itself from a release file (MT58), on invented package folders: the file is checked before
anything is written, the version in use is copied aside first, and a version that does not start is put back."""

import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from modtrap import api, logbook, selfupdate, version

REPO = Path(version.ROOT)


def program(ver: str, extra: dict[str, bytes]) -> dict[str, bytes]:
    files = {"__init__.py": b'VERSION = "%s"\n' % ver.encode(), "__main__.py": b"print('an invented program')\n",
             "page/index.html": b"<!doctype html><title>invented</title>", **extra}
    files[version.RECORD] = json.dumps({"version": ver, "mark": selfupdate._mark_of(files)}).encode()
    return files


def release(files: dict[str, bytes], *, top: str = "ModTrap", more: dict[str, bytes] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(top + "/ModTrap.exe", b"the launcher, invented")
        z.writestr(top + "/ModTrap.cmd", b"@echo off\r\n")
        z.writestr(top + "/READ ME FIRST.txt", b"read me")
        for rel, data in files.items():
            z.writestr(top + "/app/modtrap/" + rel, data)
        for rel, data in (more or {}).items():
            z.writestr(rel, data)
    return buf.getvalue()


class ReleaseFiles(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        os.environ["MODTRAP_HOME"] = str(self.dir / "home")
        # The package in use: version 1.0.0, with a Python of its own and a file the next version no longer has.
        self.root = self.dir / "ModTrap"
        for rel, data in program("1.0.0", {"old_only.py": b"# gone in the next version\n", "shared.py": b"# as in 1.0.0\n"}).items():
            f = self.root / "app" / "modtrap" / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        (self.root / "ModTrap.exe").write_bytes(b"the older launcher")
        (self.root / "python").mkdir()
        (self.root / "python" / "python.exe").write_bytes(b"the Python in use")
        self.new = program("1.0.1", {"new_only.py": b"# new in 1.0.1\n", "shared.py": b"# as in 1.0.1\n"})

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def file(self, data: bytes, name: str = "ModTrap-1.0.1-win64.zip") -> Path:
        p = self.dir / name
        p.write_bytes(data)
        return p

    def snapshot(self) -> dict:
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in sorted(self.root.rglob("*")) if p.is_file()}

    def test_a_release_file_is_read_and_says_its_version(self):
        got = selfupdate.read(self.file(release(self.new)))
        self.assertEqual((got["version"], got["python"]), ("1.0.1", False))
        got = selfupdate.read(self.file(release(self.new, more={"ModTrap/python/python.exe": b"a newer Python"})))
        self.assertTrue(got["python"])

    def test_what_is_no_release_file_is_refused_in_words(self):
        tampered = dict(self.new, **{"shared.py": b"# changed after the version was written\n"})
        cases = {
            "not a .zip": b"not a zip at all",
            "has no ModTrap.exe": release(self.new, top="Other"),
            "outside its one folder": release(self.new, more={"elsewhere/evil.py": b"x"}),
            "outside its one folder ": release(self.new, more={"ModTrap/../evil.py": b"x"}),
            "not whole": release(tampered),
        }
        for words, data in cases.items():
            with self.assertRaises(selfupdate.Refused, msg=words) as c:
                selfupdate.read(self.file(data))
            self.assertIn(words.strip(), str(c.exception))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Some Mod/Plugin.esp", b"a mod's archive, not ModTrap")
        with self.assertRaises(selfupdate.Refused):
            selfupdate.read(self.file(buf.getvalue()))

    def test_versions_are_compared_by_their_numbers(self):
        self.assertEqual([selfupdate.newer(a, b) for a, b in (("0.3.50", "0.3.49"), ("0.3.9", "0.3.10"), ("1.0", "1.0"), ("unknown", "1.0"))], [1, -1, 0, 0])

    def test_the_update_replaces_the_program_keeps_the_older_one_and_leaves_its_python(self):
        before = self.snapshot()
        done = selfupdate.apply(self.file(release(self.new, more={"ModTrap/python/python.exe": b"a newer Python"})), self.root, try_start=lambda root: "")
        self.assertEqual((done["version"], done["was"]), ("1.0.1", "1.0.0"))
        now = self.snapshot()
        self.assertEqual(now["app/modtrap/shared.py"], b"# as in 1.0.1\n")
        self.assertIn("app/modtrap/new_only.py", now)
        self.assertNotIn("app/modtrap/old_only.py", now)                       # what the new version no longer has
        self.assertEqual(now["ModTrap.exe"], b"the launcher, invented")
        self.assertEqual(now["python/python.exe"], b"the Python in use")       # the running Python is not replaced
        self.assertEqual(version.recorded(self.root / "app" / "modtrap")[0], "1.0.1")
        self.assertEqual(version.code_mark(self.root / "app" / "modtrap"), version.recorded(self.root / "app" / "modtrap")[1])
        kept = self.dir / "home" / "updates" / done["kept"]
        self.assertEqual({p.relative_to(kept).as_posix(): p.read_bytes() for p in kept.rglob("*") if p.is_file()},
                         {k: v for k, v in before.items() if not k.startswith("python/")})

    def test_a_version_that_does_not_start_is_put_back(self):
        before = self.snapshot()
        with self.assertRaises(selfupdate.Refused) as c:
            selfupdate.apply(self.file(release(self.new)), self.root, try_start=lambda root: "SyntaxError: invented")
        self.assertIn("does not start on this PC: SyntaxError: invented", str(c.exception))
        self.assertIn("(1.0.0) is back in place", str(c.exception))
        self.assertEqual(self.snapshot(), before)

    def test_the_real_program_is_tried_before_it_takes_over(self):
        """The real check, with ModTrap's own files as the new version: it starts, so the update stands."""
        files = {p.relative_to(REPO).as_posix(): p.read_bytes() for p in REPO.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        files[version.RECORD] = json.dumps({"version": version.VERSION, "mark": selfupdate._mark_of(files)}).encode()
        done = selfupdate.apply(self.file(release(files)), self.root)
        self.assertEqual(done["version"], version.VERSION)
        self.assertEqual(selfupdate.starts(self.root), "")
        (self.root / "app" / "modtrap" / "api.py").write_text("def broken(:\n")
        self.assertIn("SyntaxError", selfupdate.starts(self.root))

    def test_a_modtrap_run_from_its_source_folder_is_not_updated_this_way(self):
        self.assertIsNone(selfupdate.package_root())
        self.assertEqual(selfupdate.package_root(self.root / "app" / "modtrap"), self.root)
        a = api.Api()
        st = a.get("/api/selfupdate", {})[1]
        self.assertEqual((st["can"], st["version"]), (False, version.VERSION))
        with self.assertRaises(api.Bad):
            a.self_upload("ModTrap-1.0.1-win64.zip", 10, io.BytesIO(b"0123456789"))
        with self.assertRaises(api.Bad):
            a.post("/api/selfupdate/apply", {"id": "0123456789ab"})

    def test_a_file_handed_over_is_read_and_then_applied_by_the_server(self):
        a = api.Api()
        a._self_root = lambda: self.root
        data = release(self.new)
        got = a.self_upload("ModTrap-1.0.1-win64.zip", len(data), io.BytesIO(data))
        self.assertEqual((got["version"], got["current"], len(got["id"])), ("1.0.1", version.VERSION, 12))
        with self.assertRaises(api.Bad):
            a.self_upload("a mod.zip", 5, io.BytesIO(b"hello"))
        got = a.self_upload("ModTrap-1.0.1-win64.zip", len(data), io.BytesIO(data))
        kept = selfupdate.starts
        selfupdate.starts = lambda root: ""
        selfupdate.apply.__defaults__ = (None, selfupdate.starts)
        try:
            code, answer, after = a.post("/api/selfupdate/apply", {"id": got["id"]})
        finally:
            selfupdate.starts = kept
            selfupdate.apply.__defaults__ = (None, kept)
        self.assertEqual((code, answer["version"], answer["restart"], callable(after)), (200, "1.0.1", True, True))
        self.assertEqual(version.recorded(self.root / "app" / "modtrap")[0], "1.0.1")


if __name__ == "__main__":
    unittest.main()
