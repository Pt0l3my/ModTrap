"""ModTrap updates itself from a release file the owner hands it (MT58).

A release file is the package `tools/build_exe.py` makes: `ModTrap-<version>-win64.zip`, one folder `ModTrap` with
`ModTrap.exe`, `ModTrap.cmd`, the program under `app/modtrap`, and perhaps a Python of its own under `python`.

What is done, and in which order:
- the file is read and checked before anything is written: it is such a package, every name stays inside its one
  folder, and the program in it is whole (the mark of its files is the one its own `version.json` names);
- the program in use is copied to ModTrap's own folder first (`updates/before-...`), so that it can be put back;
- the new files are written over the old ones, and files the new version no longer has are taken away; a Python
  inside the package is left as it is, since the running one cannot be replaced;
- the new program is started once, to see that it starts on this PC; if it does not, the copy is put back;
- ModTrap starts itself again; the new start takes over from this one (WHY§68).

Nothing is fetched from anywhere: the owner gives the file. ModTrap run from its source folder is not updated this
way.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from . import console, logbook, paths, version

log = logbook.get("update")
TOP = "ModTrap"
PROGRAM = "app/modtrap"
MAX_FILES = 20_000
MAX_BYTES = 600 * 1024 * 1024
KEEP = 3                       # copies of earlier versions kept
NAME = "ModTrap-<version>-win64.zip"


class Refused(Exception):
    """The update is not made; the text says why, in words for the page."""


def package_root(root: Path = version.ROOT) -> Path | None:
    """The folder of the package this ModTrap runs from (the one with ModTrap.exe), or None when it does not run
    from a package (the source folder, a checkout)."""
    app = root.parent
    if app.name != "app":
        return None
    top = app.parent
    return top if (top / "ModTrap.exe").is_file() or (top / "ModTrap.cmd").is_file() else None


def _mark_of(files: dict[str, bytes]) -> str:
    """The mark `version.code_mark` gives a program folder, worked out from the files' contents alone."""
    h = hashlib.sha256()
    for rel in sorted(files):
        if Path(rel).suffix.lower() in version.KINDS and "__pycache__" not in rel.split("/") and rel != version.RECORD:
            h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(files[rel].replace(b"\r", b"")).digest())
    return h.hexdigest()[:16]


def read(path: Path) -> dict:
    """What a release file is: {"version", "files", "bytes", "python"}; refused, in words, when it is not one."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise Refused("This is not a ModTrap release file: it is not a .zip. A release file is named %s." % NAME) from None
    with z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_BYTES:
            raise Refused("This file is larger than a ModTrap release file can be.")
        names = {i.filename for i in infos}
        for need in ("ModTrap.exe", PROGRAM + "/" + version.RECORD, PROGRAM + "/__main__.py", PROGRAM + "/page/index.html"):
            if TOP + "/" + need not in names:
                raise Refused("This is not a ModTrap release file: it has no %s in a folder “%s”. A release file is named %s."
                              % (need.rsplit("/", 1)[-1], TOP, NAME))
        for i in infos:
            parts = i.filename.replace("\\", "/").split("/")
            if parts[0] != TOP or len(parts) < 2 or any(p in ("", ".", "..") or ":" in p for p in parts) or i.filename.startswith("/"):
                raise Refused("This is not a ModTrap release file: it holds something outside its one folder “%s”." % TOP)
            if (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise Refused("This is not a ModTrap release file: it holds a link.")
        lead = TOP + "/" + PROGRAM + "/"
        try:
            program = {i.filename[len(lead):]: z.read(i) for i in infos if i.filename.startswith(lead)}
            said = json.loads(program[version.RECORD].decode("utf-8"))
            ver, mark = said["version"], said["mark"]
        except (zipfile.BadZipFile, OSError, ValueError, KeyError, TypeError, RuntimeError):
            raise Refused("The release file could not be read through: it is damaged. Download it again.") from None
        if not isinstance(ver, str) or not isinstance(mark, str) or _mark_of(program) != mark:
            raise Refused("The release file is not whole: the program in it is not the one its own version names. Download it again.")
        return {"version": ver, "files": len(infos), "bytes": sum(i.file_size for i in infos),
                "python": any(n.startswith(TOP + "/python/") for n in names)}


def newer(a: str, b: str) -> int:
    """1 when version `a` is the newer one, -1 when `b` is, 0 when they are the same or cannot be compared."""
    def nums(v: str) -> list[int] | None:
        try:
            return [int(x) for x in v.split(".")]
        except ValueError:
            return None
    x, y = nums(a), nums(b)
    if x is None or y is None or x == y:
        return 0
    return 1 if x > y else -1


def _tree(root: Path) -> dict[str, Path]:
    """The files of a package folder that an update owns: everything but a Python inside it and compiled caches."""
    out = {}
    for base, dirs, files in os.walk(root):
        rel_base = Path(base).relative_to(root).as_posix()
        dirs[:] = [d for d in dirs if d != "__pycache__" and not (rel_base == "." and d == "python")]
        for n in files:
            rel = n if rel_base == "." else rel_base + "/" + n
            out[rel] = Path(base) / n
    return out


def _put(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".new")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(tmp, target)
    except PermissionError:
        # A program that is running cannot be written over on Windows, but it can be renamed out of the way.
        aside = target.with_name(target.name + ".old")
        try:
            if aside.exists():
                aside.unlink()
        except OSError:
            pass
        os.replace(target, aside)
        os.replace(tmp, target)


def _write(root: Path, files: dict[str, bytes]) -> None:
    """Makes the package folder hold exactly `files` (a Python inside it apart): written, then what is left over of
    the older version's program is taken away."""
    for rel, data in files.items():
        _put(root.joinpath(*rel.split("/")), data)
    for rel, p in _tree(root).items():
        if rel not in files and rel.startswith(PROGRAM + "/") and not rel.endswith((".old", ".new")):
            try:
                p.unlink()
            except OSError:
                pass
    for base, dirs, _files in os.walk(root / "app"):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(Path(base) / d, ignore_errors=True)       # compiled from the older program


def starts(root: Path) -> str:
    """Does the program in `root` start on this PC's Python? "" when it does, else what it said."""
    env = dict(os.environ, PYTHONPATH=str(root / "app"), PYTHONDONTWRITEBYTECODE="1")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        got = subprocess.run([sys.executable, "-c", "import modtrap.__main__, modtrap.api, modtrap.changes; print(modtrap.VERSION)"],
                             cwd=str(root), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=120, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "it could not be tried (%s)" % type(e).__name__
    if got.returncode != 0:
        lines = got.stderr.decode("utf-8", "replace").strip().splitlines()
        return lines[-1][:300] if lines else "it ended with an error"
    return ""


def apply(path: Path, root: Path, keep_dir: Path | None = None, try_start=starts) -> dict:
    """Updates the package in `root` from the release file. Returns {"version", "was", "kept", "python"}. On any
    failure the program that was there is put back, and the refusal says so."""
    info = read(path)
    keep_dir = keep_dir or paths.home() / "updates"
    was = version.recorded(root / "app" / "modtrap")[0]
    kept = keep_dir / ("before-%s-%s" % (info["version"], time.strftime("%Y%m%d-%H%M%S")))
    old = _tree(root)
    try:
        for rel, p in old.items():                              # the program in use, copied first
            target = kept.joinpath(*rel.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
        for rel, p in old.items():
            if kept.joinpath(*rel.split("/")).stat().st_size != p.stat().st_size:
                raise OSError("the copy of %s is not whole" % rel)
    except OSError as e:
        shutil.rmtree(kept, ignore_errors=True)
        raise Refused("The version in use could not be copied aside first (%s), so nothing was changed." % logbook.why(e)) from None
    lead = TOP + "/"
    try:
        with zipfile.ZipFile(path) as z:
            files = {i.filename[len(lead):]: z.read(i) for i in z.infolist()
                     if not i.is_dir() and not i.filename.startswith(lead + "python/")}
        _write(root, files)
        now = version.recorded(root / "app" / "modtrap")
        if now[0] != info["version"] or version.code_mark(root / "app" / "modtrap") != now[1]:
            raise OSError("the files written are not those of version %s" % info["version"])
        told = try_start(root)
        if told:
            raise OSError("version %s does not start on this PC: %s" % (info["version"], told))
    except (OSError, zipfile.BadZipFile, RuntimeError) as e:
        why = logbook.why(e) if not str(e).startswith(("version ", "the files")) else str(e)
        log.error("the update stopped: %s; putting version %s back", why, was)
        try:
            _write(root, {rel: kept.joinpath(*rel.split("/")).read_bytes() for rel in old})
            for rel in set(locals().get("files") or ()) - set(old):          # what only the new version brought
                try:
                    root.joinpath(*rel.split("/")).unlink()
                except OSError:
                    pass
        except OSError as e2:
            raise Refused("The update stopped (%s), and the version before could not be put back whole (%s). It is kept in "
                          "ModTrap's own folder, under updates; unpack your last release file over ModTrap's folder."
                          % (why, logbook.why(e2))) from None
        raise Refused("The update was not made: %s. The version you had (%s) is back in place." % (why, was)) from None
    for stale in sorted((d for d in keep_dir.iterdir() if d.is_dir() and d.name.startswith("before-")), key=lambda d: d.stat().st_mtime)[:-KEEP]:
        shutil.rmtree(stale, ignore_errors=True)
    log.info("ModTrap's files are now those of version %s (was %s); the version before is kept in ModTrap's own folder", info["version"], was)
    return {"version": info["version"], "was": was, "kept": kept.name, "python": info["python"]}


def restart(root: Path, argv: list[str]) -> None:
    """Starts ModTrap again from `root`, with what this one was started with and without a new browser tab: the page
    that is open loads itself anew. The new start takes over from this one."""
    args = [a for a in argv if a != "--no-browser"] + ["--no-browser"]
    if sys.platform == "win32" and console.SWITCH not in args:
        args.append(console.SWITCH)                             # the console made below is the new start's own (MT63)
    env = dict(os.environ, PYTHONPATH=str(root / "app"))
    cmd = [sys.executable, "-m", "modtrap", *args]
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = console.HIDE                           # hidden; the new start shows it if the setting says so
        subprocess.Popen(cmd, cwd=str(root), env=env, startupinfo=si, close_fds=True,
                         creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        subprocess.Popen(cmd, cwd=str(root), env=env, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)


__all__ = ["Refused", "apply", "newer", "package_root", "read", "restart", "starts"]
