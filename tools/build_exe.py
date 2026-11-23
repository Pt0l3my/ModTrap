#!/usr/bin/env python3
"""Builds ModTrap's package for Windows (MT51): a folder with ModTrap.exe.

    python3 tools/build_exe.py

The package is ModTrap-<version>-win64.zip, with the one folder ModTrap inside. Python is not in it: ModTrap needs
the Python installed on the PC (3.10 or newer), and its launcher finds that one (MT51, the owner's word of
2026-11-23: "we ship without python, and make it dependency").

What goes in, in a folder named ModTrap (the version is in the archive's name and in the programs' properties):
    ModTrap.exe    ModTrap's own launcher (tools/exe/launcher.c), built here with the MinGW-w64 cross compiler;
                   it starts ModTrap with --allow-changes: the one program, able to do all of ModTrap's work (MT53)
    app/modtrap/   ModTrap itself, as it is in this repository
    LICENSE, NOTICE, READ ME FIRST.txt

The result is dist/ModTrap-<version>-win64.zip. Nothing built is committed: dist/ and build/ are ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILER = "x86_64-w64-mingw32-gcc"
RESOURCES = "x86_64-w64-mingw32-windres"
FOLDER = "ModTrap"                       # the one folder inside the archive, the same for every version (MT52)

# What Windows shows under a program's Properties, Details.
VERSION_RC = """1 VERSIONINFO
FILEVERSION %(commas)s
PRODUCTVERSION %(commas)s
FILEFLAGSMASK 0x3fL
FILEFLAGS 0x0L
FILEOS 0x40004L
FILETYPE 0x1L
FILESUBTYPE 0x0L
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040904b0"
    BEGIN
      VALUE "FileDescription", "%(what)s"
      VALUE "FileVersion", "%(version)s"
      VALUE "InternalName", "ModTrap"
      VALUE "OriginalFilename", "%(file)s"
      VALUE "ProductName", "ModTrap"
      VALUE "ProductVersion", "%(version)s"
      VALUE "LegalCopyright", "MIT licence"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x409, 1200
  END
END
"""

CMD = """@echo off
rem Starts ModTrap as the .exe of the same name does, with the Python installed on this PC (3.10 or newer).
set "PYTHONPATH=%~dp0app"
where py >nul 2>nul
if errorlevel 1 (python -m modtrapEXTRA %*) else (py -3 -m modtrapEXTRA %*)
if errorlevel 1 pause
"""

NEEDS_PYTHON = """ModTrap needs Python on this PC: version 3.10 or newer, from python.org, installed with "Add python.exe to PATH"
ticked. Nothing else needs installing. The launcher finds that Python as Windows finds programs, and says so where
there is none. The "app" folder is ModTrap."""

READ_ME = """ModTrap %(version)s for Windows
===========================

Unpack this whole folder somewhere of your own (not inside the game's folder, not inside a modlist), and start:

  ModTrap.exe

Your browser opens ModTrap's page, and that is all there is to see: ModTrap has no window of its own. What its
program writes is on the page (History, then Log). ModTrap closes when you close its tab (never in the middle
of a job), or with "Quit" at the top of the page. When your browser brings the tab back and ModTrap is not running,
the tab offers to start it: your browser asks whether the page may open ModTrap; say yes. For that, ModTrap enters
one kind of link (modtrap:) for your Windows account; Settings, "Let ModTrap's page start ModTrap" takes it out
again. To see the program's console window after all, minimised in the taskbar: Settings, "Show ModTrap's console
window".

%(python)s

To update ModTrap later: press the version at the top of its page and give it the newer release file (this kind of
zip). ModTrap checks it, keeps the version in use aside, puts the new one in place and starts again.

ModTrap keeps its sessions, settings and downloads in its own folder under your Windows profile, not in here, so a
newer ModTrap can also simply replace this folder: the folder is named ModTrap in every version, and the version is
in the archive's name and in the programs' Properties.

Windows may warn about a program it does not know, the first time: "More info", then "Run anyway". Or, before
unpacking: right-click the zip file, Properties, tick "Unblock".

Should ModTrap.exe not start, ModTrap.cmd does the same thing, in a window that shows what it says.

To give ModTrap further switches, start it from a command prompt: ModTrap.exe --help

ModTrap's licence is LICENSE; NOTICE lists what ModTrap builds on.
"""


def version() -> str:
    return json.loads((ROOT / "modtrap" / "version.json").read_text(encoding="utf-8"))["version"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Builds ModTrap's package for Windows.")
    ap.add_argument("--out", type=Path, default=ROOT / "dist", help="where the package goes (default: dist/)")
    a = ap.parse_args()

    if shutil.which(COMPILER) is None or shutil.which(RESOURCES) is None:
        print("%s and %s are not installed (Debian and Ubuntu: the package gcc-mingw-w64-x86-64)" % (COMPILER, RESOURCES), file=sys.stderr)
        return 1

    ver = version()
    name = "ModTrap-%s-win64" % ver
    work = a.out / (name + ".build")
    if work.exists():
        shutil.rmtree(work)
    out = work / FOLDER
    out.mkdir(parents=True)

    # The launcher, with its version for Windows' Properties.
    src = ROOT / "tools" / "exe" / "launcher.c"
    numbers = [int(x) for x in ver.split(".")[:4] if x.isdigit()]
    commas = ",".join(str(x) for x in (numbers + [0, 0, 0, 0])[:4])
    for exe, extra, what in (("ModTrap.exe", " --allow-changes", "ModTrap"),):
        rc = work / "version.rc"
        rc.write_text(VERSION_RC % {"commas": commas, "version": ver, "what": what, "file": exe}, encoding="ascii")
        res = work / "version.o"
        subprocess.run([RESOURCES, "-O", "coff", "-i", str(rc), "-o", str(res)], check=True)
        cmd = [COMPILER, "-O2", "-s", "-municode", "-mwindows", "-Wall", "-Wextra", "-o", str(out / exe), str(src), str(res), "-luser32"]
        if extra:
            cmd.insert(1, '-DEXTRA_ARGS=L"%s"' % extra)
        subprocess.run(cmd, check=True)
        rc.unlink()
        res.unlink()

    # ModTrap itself.
    shutil.copytree(ROOT / "modtrap", out / "app" / "modtrap", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for f in ("LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / f, out / f)
    # A second way in, should Windows not let the launcher run: the same start, as a command file.
    for cmd_name, extra in (("ModTrap.cmd", " --allow-changes"),):
        (out / cmd_name).write_text(CMD.replace("EXTRA", extra).replace("\n", "\r\n"), encoding="ascii", newline="")
    (out / "READ ME FIRST.txt").write_text(READ_ME % {"version": ver, "python": NEEDS_PYTHON},
                                             encoding="utf-8", newline="\r\n")

    archive = a.out / (name + ".zip")
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, (Path(FOLDER) / f.relative_to(out)).as_posix())
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print("%s: %.1f MB unpacked; it runs on the PC's own Python" % (out, size / 1048576))
    print("%s: %.1f MB, sha256 %s" % (archive, archive.stat().st_size / 1048576, sha256(archive)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
