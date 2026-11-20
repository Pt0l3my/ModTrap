"""Sessions (MT20, WHY§33): one piece of work on one modlist, kept in a folder of its own under ModTrap's work
folder, so that quitting ModTrap and starting it again brings the same state back.

A session holds: its name (the modlist's, until the owner renames it), the modlist's folder and profile, what the
page looked like (the ticked mods, the tab, the search and filters, the folded groups), its log and its jobs.

One session at a time holds a modlist. A second session on the same modlist can be made, but it waits, locked,
until the one before it is finished: two sessions changing one modlist would trip over each other.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths

ACTIVE, WAITING, FINISHED = "active", "waiting", "finished"
NAME_MAX = 80
UI_MAX = 256 * 1024              # what the page may ask to have remembered, in bytes of JSON


class Refused(Exception):
    """What was asked of a session cannot be done; the text says why, in words for the page."""


def modlist_key(folder: str) -> str:
    """One key for one modlist folder, however its path is written."""
    return os.path.normcase(os.path.abspath(folder)).rstrip("\\/").casefold()


def clean_name(name: str) -> str:
    name = re.sub(r"[\x00-\x1f\x7f]+", " ", name).strip()
    if not name:
        raise Refused("a session needs a name")
    if len(name) > NAME_MAX:
        raise Refused("a session's name can be at most %d characters" % NAME_MAX)
    return name


@dataclass
class Session:
    id: str
    name: str
    folder: str
    profile: str = ""
    status: str = ACTIVE
    created: str = ""
    updated: str = ""
    finished: str = ""
    ui: dict = field(default_factory=dict)
    last_job: str = ""

    @property
    def key(self) -> str:
        return modlist_key(self.folder)

    def brief(self) -> dict:
        return {"id": self.id, "name": self.name, "modlist": Path(self.folder.replace("\\", "/")).name,
                "folder": self.folder, "profile": self.profile, "status": self.status, "created": self.created,
                "updated": self.updated, "finished": self.finished}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Store:
    """The sessions on disk: `<ModTrap's folder>/sessions/<id>/session.json`, and beside it the session's log and
    its jobs. Every change is written at once, atomically."""

    def __init__(self, base: Path | None = None):
        self.base = base or paths.home() / "sessions"

    def dir(self, sid: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", sid):
            raise Refused("that is not a session")
        return self.base / sid

    def all(self) -> list[Session]:
        """Every session, oldest first. A folder that does not hold a readable session is passed over."""
        out = []
        try:
            names = sorted(os.listdir(self.base))
        except OSError:
            return []
        for name in names:
            try:
                with open(self.base / name / "session.json", "rb") as f:
                    data = json.loads(f.read(4 * 1024 * 1024).decode("utf-8"))
                known = {k: data[k] for k in Session.__dataclass_fields__ if k in data}
                s = Session(**known)
                if s.id == name and s.status in (ACTIVE, WAITING, FINISHED):
                    out.append(s)
            except (OSError, ValueError, TypeError):
                continue
        out.sort(key=lambda s: (s.created, s.id))
        return out

    def get(self, sid: str) -> Session:
        self.dir(sid)
        for s in self.all():
            if s.id == sid:
                return s
        raise Refused("that session no longer exists")

    def save(self, s: Session) -> None:
        s.updated = _now()
        paths.write_atomic(self.dir(s.id) / "session.json",
                           (json.dumps(asdict(s), indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    def unfinished(self, folder: str) -> list[Session]:
        key = modlist_key(folder)
        return [s for s in self.all() if s.status != FINISHED and s.key == key]

    def holder(self, folder: str) -> Session | None:
        """The session that holds this modlist now, if any."""
        return next((s for s in self.unfinished(folder) if s.status == ACTIVE), None)

    def _free_name(self, wanted: str) -> str:
        taken = {s.name.casefold() for s in self.all() if s.status != FINISHED}
        if wanted.casefold() not in taken:
            return wanted
        for n in range(2, 1000):
            name = "%s (%d)" % (wanted[:NAME_MAX - 7], n)
            if name.casefold() not in taken:
                return name
        raise Refused("too many sessions of that name")

    def create(self, folder: str, profile: str = "") -> Session:
        """A new session on this modlist, named after it. It holds the modlist if no other unfinished session
        does; otherwise it waits."""
        name = self._free_name(clean_name(Path(folder.replace("\\", "/")).name or "Modlist"))
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "session"
        stamp = time.strftime("%Y%m%d-%H%M%S")
        status = WAITING if self.holder(folder) else ACTIVE
        for n in range(100):
            sid = "%s-%s%s" % (slug, stamp, "-%d" % n if n else "")
            d = self.base / sid
            try:
                d.mkdir(parents=True)
            except FileExistsError:
                continue
            s = Session(id=sid, name=name, folder=folder, profile=profile, status=status, created=_now())
            self.save(s)
            return s
        raise Refused("a folder for the session could not be made")

    def open_for(self, folder: str, profile: str = "") -> Session:
        """The session to use when a modlist is opened: the one that holds it, else a waiting one, else a new one."""
        return self.holder(folder) or next(iter(self.unfinished(folder)), None) or self.create(folder, profile)

    def rename(self, sid: str, name: str) -> Session:
        s = self.get(sid)
        name = clean_name(name)
        if any(o.id != sid and o.status != FINISHED and o.name.casefold() == name.casefold() for o in self.all()):
            raise Refused("another open session already has that name")
        s.name = name
        self.save(s)
        return s

    def finish(self, sid: str) -> tuple[Session, Session | None]:
        """Marks a session finished, and hands its modlist to the session that has waited longest for it.
        Returns the finished session and the one that now holds the modlist, if any. Whether the session is safe
        to finish is the caller's to check first."""
        s = self.get(sid)
        if s.status == FINISHED:
            raise Refused("that session is already finished")
        held = s.status == ACTIVE
        s.status, s.finished = FINISHED, _now()
        self.save(s)
        nxt = None
        if held:
            waiting = [o for o in self.unfinished(s.folder) if o.status == WAITING]
            if waiting:
                nxt = waiting[0]
                nxt.status = ACTIVE
                self.save(nxt)
        return s, nxt

    def set_ui(self, sid: str, ui: dict) -> None:
        if len(json.dumps(ui)) > UI_MAX:
            raise Refused("that is more than ModTrap remembers of a page")
        s = self.get(sid)
        s.ui = ui
        self.save(s)
