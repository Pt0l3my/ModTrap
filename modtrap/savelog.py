""""Save this session" (WHY§48): the current session's log and job records, cleaned of the owner's folders and
user name, packed into one .7z for the owner to download from the page and send when asking for help.

What goes in: what tells how a run went. The session's log, its history and probe outcome, each job's records
(plans, reports, xEdit's own log, the lists given to xEdit), the three list files of the open profile, and a
short description of the setup. What never goes in: plugins, archives, unpacked mods, the safe folders' copies or
anything else of a mod's content, and other sessions.

Every text is cleaned as it is packed, and a text that cannot be cleaned is left out, not passed through.
"""

from __future__ import annotations

import getpass
import json
import os
import platform
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Iterator

from . import NAME, VERSION, logbook, sevenz

BLOCK = 64 * 1024
LINE_CAP = 1024 * 1024                 # a line longer than this is cut where it stands
JSON_CAP = 64 * 1024 * 1024            # a .json larger than this is packed as plain text
FILE_CAP = 512 * 1024 * 1024           # a single file larger than this is left out
JOBS = 40                              # the newest jobs of the session
TOOL_LOGS = 6                          # the newest logs of each tool that are packed
TEXT_SUFFIXES = (".json", ".jsonl", ".txt", ".tsv", ".log", ".ini")
SKIP_DIRS = {"files", "out", "staged", "xedit-backups", "incoming"}      # mods' content: never packed
LEFT_OUT = "<a text that could not be cleaned was left out>"
# An absolute path that no known folder covered: a drive or a network share, then everything up to the end of the
# line or a character a path cannot hold. The placeholder <user> may stand inside it. Not a web address: the letter
# before the colon must stand alone.
_ABS = re.compile(r"""(?<![A-Za-z])(?:[A-Za-z]:[\\/]+|\\\\[^\\/\s"<>]+[\\/]+)(?:[^\r\n\t"<>|*?]|<user>)*""")
_UNIX = re.compile(r"""(?<![\w<>.:/\\])/(?:home|Users|root|tmp|var|mnt|media|private)/(?:[^\r\n\t"<>|*?:]|<user>)*""")

class Cleaner:
    """Takes the owner's folders and user name out of text. Known folders become placeholders such as <modlist>;
    the user name is replaced where it is part of a path; any other absolute path is cut down to its last part."""

    def __init__(self, folders: dict[str, str | None], home: str | None = None, user: str | None = None):
        items = dict(folders)
        items.setdefault("<home>", home if home is not None else os.path.expanduser("~"))
        masks = []
        for label, folder in items.items():
            if not folder or len(folder) < 4:
                continue
            parts = [re.escape(p) for p in re.split(r"[\\/]+", folder.rstrip("\\/")) if p != ""]
            if not parts:
                continue
            lead = r"[\\/]+" if folder.startswith(("/", "\\")) else ""
            masks.append((len(folder), re.compile(lead + r"[\\/]+".join(parts), re.IGNORECASE), label))
        masks.sort(key=lambda t: -t[0])
        self._masks = [(rx, label) for _, rx, label in masks]
        if user is None:
            try:
                user = getpass.getuser()
            except Exception:
                user = ""
        # Only as a part of a path: an account called "User" must not turn every "user" into a placeholder.
        self._user = re.compile(r"(?<=[\\/])" + re.escape(user) + r"(?=[\\/]|$|[\s\"'])", re.IGNORECASE) \
            if user and len(user) >= 2 else None

    @staticmethod
    def _last_part(m: re.Match) -> str:
        s = m.group(0).rstrip("\\/ ")
        tail = re.split(r"[\\/]+", s)[-1]
        return "<path>/" + tail if tail and not re.fullmatch(r"[A-Za-z]:", tail) else "<path>"

    def text(self, s: str) -> str:
        try:
            for rx, label in self._masks:
                s = rx.sub(lambda m, label=label: label, s)
            if self._user is not None:
                s = self._user.sub("<user>", s)
            s = _ABS.sub(self._last_part, s)
            return _UNIX.sub(self._last_part, s)
        except Exception:
            return LEFT_OUT

    def value(self, v: object, depth: int = 0) -> object:
        """A parsed JSON value with every string in it cleaned, keys too."""
        if isinstance(v, str):
            return self.text(v)
        if depth > 200:
            return LEFT_OUT
        if isinstance(v, list):
            return [self.value(x, depth + 1) for x in v]
        if isinstance(v, dict):
            return {self.text(str(k)): self.value(x, depth + 1) for k, x in v.items()}
        return v


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def _encode(text: str) -> bytes:
    return text.encode("utf-8", errors="backslashreplace")       # a lone surrogate from a JSON escape must not fail


def _clean_text_item(name: str, text: str, cleaner: Cleaner) -> str:
    """A text ModTrap wrote itself for the archive. JSON is cleaned value by value and written again, so that it
    stays valid: cleaning it as plain text can take the backslash of an escaped quote for part of a path."""
    if name.lower().endswith(".json"):
        try:
            return json.dumps(cleaner.value(json.loads(text)), ensure_ascii=False, indent=1) + "\n"
        except ValueError:
            pass
    return cleaner.text(text)


def clean_blocks(path: Path, cleaner: Cleaner) -> Iterator[bytes]:
    """A file's cleaned content, in blocks. Its size is noted when it is opened and no more than that is read, so
    a file still being written is taken as it was then. Text is cleaned block by block, each block cut at a line
    end so that no path is cut in two; a .json is parsed whole, cleaned and written again, and stays valid."""
    kind = path.suffix.lower()
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        if kind == ".json" and size <= JSON_CAP:
            raw = f.read(size)
            try:
                data = json.loads(_decode(raw))
            except ValueError:
                yield _encode(cleaner.text(_decode(raw)))
                return
            yield _encode(json.dumps(cleaner.value(data), ensure_ascii=False, indent=1) + "\n")
            return
        left, carry = size, b""
        while left > 0 or carry:
            block = f.read(min(BLOCK, left)) if left > 0 else b""
            left -= len(block)
            if left > 0 and not block:
                left = 0                                    # shorter than it said: taken as far as it reads
            data = carry + block
            if left > 0:
                cut = data.rfind(b"\n")
                if cut < 0 and len(data) < LINE_CAP:
                    carry = data
                    continue
                cut = len(data) if cut < 0 else cut + 1
                data, carry = data[:cut], data[cut:]
            else:
                carry = b""
            if not data:
                continue
            if kind == ".jsonl":
                out = []
                for line in _decode(data).splitlines(keepends=True):
                    body = line.rstrip("\r\n")
                    try:
                        out.append(json.dumps(cleaner.value(json.loads(body)), ensure_ascii=False) + line[len(body):])
                    except ValueError:
                        out.append(cleaner.text(line))       # a torn last line: cleaned as plain text
                yield _encode("".join(out))
            else:
                yield _encode(cleaner.text(_decode(data)))


# --- what to collect ----------------------------------------------------------------------------------------------------

def _job_files(job: Path, into: str, out: list, notes: list, depth: int = 0) -> None:
    try:
        entries = sorted(os.scandir(job), key=lambda e: e.name.lower())
    except OSError:
        return
    for e in entries:
        try:
            if e.is_symlink():
                continue
            if e.is_dir():
                if e.name.lower() in SKIP_DIRS or e.name.lower().startswith("built-") or depth >= 3:
                    continue
                _job_files(Path(e.path), into + "/" + e.name, out, notes, depth + 1)
            elif e.is_file():
                if not e.name.lower().endswith(TEXT_SUFFIXES):
                    continue
                if e.stat().st_size > FILE_CAP:
                    notes.append("%s/%s was left out: it is larger than is packed" % (into, e.name))
                    continue
                out.append((into + "/" + e.name, Path(e.path)))
        except OSError:
            continue


def collect(session_dir: Path | None, profile_dir: Path | None, home_dir: Path, about: dict) -> list[tuple[str, object]]:
    """The archive's files, as (name in the archive, a file's path or its text). Sub-folders with mods' content
    are passed over; only text records are taken."""
    notes: list[str] = []
    items: list[tuple[str, object]] = []
    lines = ["%s  %-5s %-8s %s" % (ln.get("t", ""), ln.get("level", ""), ln.get("source", ""), ln.get("text", ""))
             for ln in logbook.dump()]
    items.append(("log.txt", "\r\n".join(lines) + "\r\n" if lines else ""))
    if session_dir is not None and session_dir.is_dir():
        for name in ("session.json", "history.jsonl", "probe.json"):
            if (session_dir / name).is_file():
                items.append(("session/" + name, session_dir / name))
        try:
            jobs = sorted((p for p in (session_dir / "jobs").iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
        except OSError:
            jobs = []
        if len(jobs) > JOBS:
            notes.append("%d older job(s) of this session were left out; the newest %d are here" % (len(jobs) - JOBS, JOBS))
        for job in jobs[-JOBS:]:
            _job_files(job, "jobs/" + job.name, items, notes)
        # The tools' own logs of the runs ModTrap started (WHY§88): the newest few of each tool.
        try:
            for d in sorted(p for p in (session_dir / "tool-logs").iterdir() if p.is_dir()):
                logs = sorted((f for f in d.iterdir() if f.is_file() and f.name.lower().endswith(TEXT_SUFFIXES)),
                              key=lambda f: f.stat().st_mtime)
                if len(logs) > TOOL_LOGS:
                    notes.append("%d older log(s) of %s were left out; the newest %d are here" % (len(logs) - TOOL_LOGS, d.name, TOOL_LOGS))
                for f in logs[-TOOL_LOGS:]:
                    if f.stat().st_size > FILE_CAP:
                        continue
                    items.append(("tool-logs/%s/%s" % (d.name, f.name), f))
        except OSError:
            pass
        try:
            for d in sorted((session_dir / "incoming").iterdir()):
                if (d / "staged.json").is_file():
                    items.append(("incoming/%s/staged.json" % d.name, d / "staged.json"))
        except OSError:
            pass
    if profile_dir is not None:
        for name in ("modlist.txt", "plugins.txt", "loadorder.txt"):
            if (profile_dir / name).is_file():
                items.append(("profile/" + name, profile_dir / name))
    if (home_dir / "settings.json").is_file():
        items.append(("modtrap/settings.json", home_dir / "settings.json"))
    about = dict(about, left_out=notes)
    items.insert(0, ("about.json", json.dumps(about, ensure_ascii=False, indent=1) + "\n"))
    return items


def describe() -> dict:
    return {"name": NAME, "version": VERSION, "python": sys.version.split()[0], "system": platform.system(),
            "release": platform.release(), "saved": time.strftime("%Y-%m-%dT%H:%M:%S")}


# --- packing ------------------------------------------------------------------------------------------------------------

class SaveJob:
    """One packing at a time. The archive is written to the system's temporary folder, outside ModTrap's own,
    handed out once, and removed after that or at the next press."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.state = "idle"            # idle, packing, ready, nothing, failed
        self.done = self.total = self.bytes = self.size = 0
        self.message = ""
        self.download_name = ""
        self._path: Path | None = None
        self._thread: threading.Thread | None = None

    def public(self) -> dict:
        return {"state": self.state, "done": self.done, "total": self.total, "bytes": self.bytes, "size": self.size,
                "message": self.message, "name": self.download_name}

    def _forget(self) -> None:
        if self._path is not None:
            try:
                self._path.unlink()
            except OSError:
                pass
            self._path = None

    def start(self, gather: Callable[[], tuple[list, Cleaner, str]]) -> bool:
        """Starts packing; False when one is already going (a second press is ignored)."""
        with self._lock:
            if self.state == "packing":
                return False
            self._forget()                                  # a stale archive goes at the next press
            self.state, self.message = "packing", ""
            self.done = self.total = self.bytes = self.size = 0
        self._thread = threading.Thread(target=self._run, args=(gather,), name="save-session", daemon=True)
        self._thread.start()
        return True

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    def _run(self, gather: Callable[[], tuple[list, Cleaner, str]]) -> None:
        log = logbook.get("app")
        path: Path | None = None
        writer: sevenz.Writer | None = None
        try:
            items, cleaner, name = gather()
            self.total = len(items)
            fd, tmp = tempfile.mkstemp(prefix="modtrap-save-", suffix=".7z")
            os.close(fd)
            path = Path(tmp)
            writer = sevenz.Writer(path)
            skipped = 0
            for arc, source in items:
                arc = cleaner.text(arc)
                if isinstance(source, Path):
                    try:
                        mtime = source.stat().st_mtime
                        blocks = clean_blocks(source, cleaner)
                        first = next(blocks, b"")           # a file that cannot be opened is passed over
                    except OSError:
                        skipped += 1
                        self.done += 1
                        continue

                    def rest(first=first, blocks=blocks) -> Iterator[bytes]:
                        yield first
                        try:
                            yield from blocks
                        except OSError:
                            return                          # failed part way: what was packed is kept
                    self.bytes += writer.add(arc, mtime, rest())
                else:
                    self.bytes += writer.add(arc, time.time(), [_encode(_clean_text_item(arc, str(source), cleaner))])
                self.done += 1
            with_data = writer.close()
            writer = None
            if not with_data:
                path.unlink()
                self.state, self.message = "nothing", "There is nothing to save yet: this session has no log lines."
                return
            with self._lock:
                self._path, self.size, self.download_name = path, path.stat().st_size, name
                self.state = "ready"
            log.info("this session's logs are packed for download: %d file(s), %s%s", self.total - skipped,
                     "%.1f KB" % (self.size / 1024), (", %d could not be opened" % skipped) if skipped else "")
        except Exception as e:
            if writer is not None:
                writer.abort()
            if path is not None:
                try:
                    path.unlink()
                except OSError:
                    pass
            self.state, self.message = "failed", "The session could not be packed: %s" % logbook.why(e)
            log.error("packing the session's logs failed: %s", logbook.why(e))

    def take(self) -> tuple[Path, str] | None:
        """The archive, once: after this it is the caller's to send and remove."""
        with self._lock:
            if self.state != "ready" or self._path is None or not self._path.is_file():
                return None
            path, self._path = self._path, None
            self.state = "idle"
            return path, self.download_name

    def close(self) -> None:
        with self._lock:
            self._forget()


def archive_name(session_name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", session_name).strip("-.")[:60] or "session"
    return "ModTrap-%s-%s.7z" % (safe, time.strftime("%Y%m%d-%H%M%S"))


__all__ = ["Cleaner", "SaveJob", "collect", "clean_blocks", "describe", "archive_name", "LEFT_OUT"]
