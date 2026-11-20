"""The folder picker behind the page's Browse button (WHY§38): lists the folders inside one folder, by name only,
and says which of them hold an MO2 instance. It never lists files and never reads one; the single thing it asks
of a folder is whether a ModOrganizer.ini is in it.

In-page, not a native dialog: a dialog opened by ModTrap's own process tends to open behind the browser, where the
owner does not see it (the lesson of the owner's DataPiler).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import locate
from .instance import INI_NAME, fold

MAX_FOLDERS = 3000
_UNC = re.compile(r"^[\\/]{2}")
_DEVICE = re.compile(r"^[\\/]{2}[.?][\\/]")


class Refused(Exception):
    """That place cannot be shown; the text says why."""


def _is_modlist(folder: str) -> bool:
    try:
        return os.path.isfile(os.path.join(folder, INI_NAME))
    except OSError:
        return False


def places() -> list[dict]:
    """Where browsing starts: this PC's fixed drives on Windows, the root elsewhere."""
    roots = locate.drive_roots() if os.name == "nt" else [Path("/")]
    return [{"name": str(r), "path": str(r)} for r in roots]


def _crumbs(path: str) -> list[dict]:
    p = Path(path)
    parts = [p, *p.parents][::-1]
    return [{"name": (x.name or str(x)), "path": str(x)} for x in parts]


def listing(path: str) -> dict:
    """The folders in `path`, each with whether it is an MO2 instance; `path` empty gives the places to start."""
    if not path:
        return {"path": "", "parent": None, "crumbs": [], "modlist": False, "cut": False,
                "folders": [dict(p, modlist=_is_modlist(p["path"])) for p in places()]}
    if len(path) > 1000 or "\x00" in path:
        raise Refused("that is not a folder's path")
    if _DEVICE.match(path) or _UNC.match(path):
        raise Refused("network and device paths are not browsed; paste the path into the box if you mean one")
    if not os.path.isabs(path):
        raise Refused("a full path is needed")
    full = os.path.abspath(path)
    if not os.path.isdir(full):
        raise Refused("that folder is not there")
    folders, cut = [], False
    try:
        with os.scandir(full) as it:
            for e in it:
                try:
                    if not e.is_dir(follow_symlinks=False) or locate._is_link(e):
                        continue
                except OSError:
                    continue
                if e.name.startswith("$") or fold(e.name) in locate.SKIP:
                    continue
                if len(folders) >= MAX_FOLDERS:
                    cut = True
                    break
                folders.append(e.name)
    except PermissionError:
        raise Refused("Windows does not let ModTrap look into that folder") from None
    except OSError as err:
        raise Refused("that folder could not be listed (%s)" % type(err).__name__) from None
    folders.sort(key=fold)
    parent = os.path.dirname(full.rstrip("\\/")) if full.rstrip("\\/") else ""
    at_root = os.path.abspath(parent or full) == full
    return {"path": full, "parent": "" if at_root else parent, "crumbs": _crumbs(full), "modlist": _is_modlist(full),
            "cut": cut,
            "folders": [{"name": n, "path": os.path.join(full, n), "modlist": _is_modlist(os.path.join(full, n))}
                        for n in folders]}
