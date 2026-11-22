"""MO2's list of programs it leaves alone (MO01§11, WHY§94): one value of its settings file, changed with care."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modtrap import mo2fix


class LeaveAlone(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ini = self.root / "ModOrganizer.ini"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_the_list_is_mo2s_default_until_the_file_names_one(self) -> None:
        self.ini.write_bytes(b"[General]\r\ngameName=Invented\r\n\r\n[Settings]\r\nstyle=dark.qss\r\n")
        self.assertEqual(mo2fix.listed(self.root), (list(mo2fix.DEFAULT), False))
        self.assertEqual(mo2fix.missing(self.root, ["csc.exe", "steam.EXE"]), ["csc.exe"])      # by name, whatever the case

    def test_adding_keeps_what_is_there_and_every_other_byte(self) -> None:
        raw = b"[General]\r\ngameName=Invented\r\nname=\\x4e2d\r\n\r\n[Settings]\r\nexecutable_blacklist=Chrome.exe;Own.exe\r\nstyle=dark.qss\r\n\r\n[Widgets]\r\nx=1\r\n"
        self.ini.write_bytes(raw)
        got = mo2fix.add(self.root, ["csc.exe", "Own.exe", "VBCSCompiler.dll"], self.root / "kept")
        self.assertEqual((got["added"], got["listed"]), (["csc.exe", "VBCSCompiler.dll"], ["Chrome.exe", "Own.exe", "csc.exe", "VBCSCompiler.dll"]))
        self.assertEqual(self.ini.read_bytes(), raw.replace(b"executable_blacklist=Chrome.exe;Own.exe",
                                                            b'executable_blacklist="Chrome.exe;Own.exe;csc.exe;VBCSCompiler.dll"'))
        self.assertEqual((self.root / "kept" / got["kept"]).read_bytes(), raw)                  # the file as it was
        self.assertEqual(mo2fix.listed(self.root), (["Chrome.exe", "Own.exe", "csc.exe", "VBCSCompiler.dll"], True))
        again = mo2fix.add(self.root, ["csc.exe"], self.root / "kept")                           # nothing to add: nothing written
        self.assertEqual((again["added"], again["kept"]), ([], ""))

    def test_a_file_without_the_key_or_the_section_gets_it_with_mo2s_default_kept(self) -> None:
        self.ini.write_bytes(b"[General]\ngameName=Invented\n\n[Settings]\nstyle=dark.qss\n\n[Widgets]\nx=1\n")
        mo2fix.add(self.root, ["csc.exe"], self.root / "kept")
        value = ";".join(mo2fix.DEFAULT) + ";csc.exe"
        self.assertEqual(self.ini.read_bytes(), ('[General]\ngameName=Invented\n\n[Settings]\nstyle=dark.qss\nexecutable_blacklist="%s"\n\n[Widgets]\nx=1\n' % value).encode())
        self.ini.write_bytes(b"[General]\ngameName=Invented")
        mo2fix.add(self.root, ["csc.exe"], self.root / "kept")
        self.assertEqual(self.ini.read_bytes(), ('[General]\ngameName=Invented\n[Settings]\nexecutable_blacklist="%s"\n' % value).encode())

    def test_only_a_plain_program_name_is_ever_written(self) -> None:
        self.ini.write_bytes(b"[Settings]\nstyle=dark.qss\n")
        for bad in ('x";evil=1', "C:\\Tools\\csc.exe", "", "notes.txt"):
            self.assertEqual(mo2fix.missing(self.root, [bad]), [])
            self.assertEqual(mo2fix.add(self.root, [bad], self.root / "kept")["added"], [])
        self.assertEqual(self.ini.read_bytes(), b"[Settings]\nstyle=dark.qss\n")


if __name__ == "__main__":
    unittest.main()
