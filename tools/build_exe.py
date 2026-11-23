#!/usr/bin/env python3
"""Builds ModTrap's package for Windows (MT51): a folder with ModTrap.exe.

    python3 tools/build_exe.py                                        # ModTrap alone: runs on the PC's own Python
    python3 tools/build_exe.py --python PATH/python.3.13.17.nupkg     # with Python inside: nothing needs installing
    python3 tools/build_exe.py --fetch                                # the same, fetching that file from NuGet first

Without Python inside, the package is ModTrap-<version>-win64.zip and its launcher starts the Python installed on the
PC; with it, ModTrap-<version>-win64-with-python.zip.

What goes in:
    ModTrap.exe, ModTrap (changes allowed).exe     ModTrap's own launcher (tools/exe/launcher.c), built here with
                                                   the MinGW-w64 cross compiler; the second passes --allow-changes
    python/        CPython for Windows as the Python Software Foundation publishes it on NuGet, unchanged, with the
                   parts ModTrap never uses left out (pip, the headers, tkinter's and the tests' files)
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
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_VERSION = "3.13.17"
PY_SHA256 = "dce409744b088f94c6e37ba41f8100c384c27e029e843237364c602d30d475e5"
PY_URL = "https://api.nuget.org/v3-flatcontainer/python/%s/python.%s.nupkg" % (PY_VERSION, PY_VERSION)
COMPILER = "x86_64-w64-mingw32-gcc"

# Parts of the Python package ModTrap never uses: left out, nothing else is touched.
LEFT_OUT = ("tools/include/", "tools/libs/", "tools/Lib/site-packages/", "tools/Lib/ensurepip/", "tools/Lib/venv/",
            "tools/Lib/idlelib/", "tools/Lib/tkinter/", "tools/Lib/turtledemo/", "tools/Lib/test/", "tools/Lib/pydoc_data/",
            "tools/Lib/__phello__/", "tools/pythonw.exe")
LEFT_OUT_FILES = ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll") + tuple("_test%s.pyd" % x for x in (
    "capi", "internalcapi", "buffer", "importmultiple", "multiphase", "singlephase", "consolea", "clinic", "clinic_limited", "limitedcapi")) + (
    "_ctypes_test.pyd", "xxlimited.pyd", "xxlimited_35.pyd")

CMD = """@echo off
rem Starts ModTrap as the .exe of the same name does: with the Python in the "python" folder beside this file where
rem there is one, else with the Python installed on this PC.
if exist "%~dp0python\\python.exe" (
  "%~dp0python\\python.exe" -m modtrapEXTRA %*
) else (
  set "PYTHONPATH=%~dp0app"
  where py >nul 2>nul
  if errorlevel 1 (python -m modtrapEXTRA %*) else (py -3 -m modtrapEXTRA %*)
)
if errorlevel 1 pause
"""

WITH_PYTHON = """Nothing needs to be installed: the "python" folder is the Python ModTrap runs on (CPython %s of the Python
Software Foundation, unchanged, without the parts ModTrap does not use; its licence is python\\LICENSE.txt), and the
"app" folder is ModTrap."""

WITHOUT_PYTHON = """ModTrap runs on the Python installed on this PC (3.10 or newer; python.org, with "Add python.exe to PATH"
ticked): the launcher finds it as Windows finds programs. The "app" folder is ModTrap."""

READ_ME = """ModTrap %(version)s for Windows
===========================

Unpack this whole folder somewhere of your own (not inside the game's folder, not inside a modlist), and start:

  ModTrap.exe                      ModTrap as it comes: it reads and reports, and changes nothing in a modlist.
  ModTrap (changes allowed).exe    The same, started with its switch for changes: demaster, install mods, update.

A console window opens and says where ModTrap's page is; your browser opens it. Closing the window, or Quit on the
page, ends ModTrap.

%(python)s
ModTrap keeps its sessions, settings and downloads in its own folder under your Windows profile, not in here, so a
newer ModTrap can simply replace this folder.

Windows may warn about a program it does not know, the first time: "More info", then "Run anyway". Or, before
unpacking: right-click the zip file, Properties, tick "Unblock".

Should a .exe not start, the two .cmd files of the same names do the same thing.

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
    ap.add_argument("--python", type=Path, help="the NuGet package of CPython %s for Windows, already fetched" % PY_VERSION)
    ap.add_argument("--fetch", action="store_true", help="fetch that package from NuGet into build/")
    ap.add_argument("--out", type=Path, default=ROOT / "dist", help="where the package goes (default: dist/)")
    a = ap.parse_args()

    nupkg = a.python
    if nupkg is None and a.fetch:
        nupkg = ROOT / "build" / ("python.%s.nupkg" % PY_VERSION)
        if not nupkg.is_file():
            nupkg.parent.mkdir(parents=True, exist_ok=True)
            print("fetching", PY_URL)
            with urllib.request.urlopen(PY_URL, timeout=300) as r, open(nupkg, "wb") as f:
                shutil.copyfileobj(r, f)
    if nupkg is not None and sha256(nupkg) != PY_SHA256:
        print("the Python package is not the one this script was written for (its checksum differs): %s" % nupkg, file=sys.stderr)
        return 1
    if shutil.which(COMPILER) is None:
        print("%s is not installed (Debian and Ubuntu: the package gcc-mingw-w64-x86-64)" % COMPILER, file=sys.stderr)
        return 1

    ver = version()
    name = "ModTrap-%s-win64%s" % (ver, "-with-python" if nupkg is not None else "")
    out = a.out / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # The launcher, twice.
    src = ROOT / "tools" / "exe" / "launcher.c"
    for exe, extra in (("ModTrap.exe", None), ("ModTrap (changes allowed).exe", ' --allow-changes')):
        cmd = [COMPILER, "-O2", "-s", "-municode", "-Wall", "-Wextra", "-o", str(out / exe), str(src), "-luser32"]
        if extra:
            cmd.insert(1, '-DEXTRA_ARGS=L"%s"' % extra)
        subprocess.run(cmd, check=True)

    kept = 0
    if nupkg is not None:
        # Python, as published, without what ModTrap never uses.
        with zipfile.ZipFile(nupkg) as z:
            for info in z.infolist():
                n = info.filename
                if not n.startswith("tools/") or n.endswith("/") or n.startswith(LEFT_OUT) or n.rsplit("/", 1)[-1] in LEFT_OUT_FILES:
                    continue
                dest = out / "python" / n[len("tools/"):]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as r, open(dest, "wb") as f:
                    shutil.copyfileobj(r, f)
                kept += 1
        # Where this Python finds its own library and ModTrap: nothing else of the PC is on its path.
        (out / "python" / ("python%s._pth" % "".join(PY_VERSION.split(".")[:2]))).write_text("Lib\nDLLs\n..\\app\n", encoding="ascii", newline="\r\n")

    # ModTrap itself.
    shutil.copytree(ROOT / "modtrap", out / "app" / "modtrap", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for f in ("LICENSE", "NOTICE"):
        shutil.copyfile(ROOT / f, out / f)
    # A second way in, should Windows not let the launcher run: the same start, as a command file.
    for cmd_name, extra in (("ModTrap.cmd", ""), ("ModTrap (changes allowed).cmd", " --allow-changes")):
        (out / cmd_name).write_text(CMD.replace("EXTRA", extra).replace("\n", "\r\n"), encoding="ascii", newline="")
    (out / "READ ME FIRST.txt").write_text(READ_ME % {"version": ver, "python": WITH_PYTHON % PY_VERSION if nupkg is not None else WITHOUT_PYTHON},
                                             encoding="utf-8", newline="\r\n")

    archive = a.out / (name + ".zip")
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, (Path(name) / f.relative_to(out)).as_posix())
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print("%s: %s, %.1f MB unpacked" % (out, "%d files of Python kept" % kept if nupkg is not None else "without Python inside", size / 1048576))
    print("%s: %.1f MB, sha256 %s" % (archive, archive.stat().st_size / 1048576, sha256(archive)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
