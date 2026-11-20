"""The safe folder and Revert (MT14, DESIGN§11): a copy of every file a job will change, taken before it changes
any, and the way back.

NOT USED BY A JOB THAT WRITES YET (there is none): groundwork for the demaster step, built and tested ahead of it
(WHY§36). The dry run keeps its copies of the dependants with the simpler code in dryrun.py.

The rules it keeps:
- no file is changed before its copy is here and matches it by size and SHA-256;
- what ModTrap then writes is noted, so that Revert can tell ModTrap's own change from someone else's;
- Revert first checks every file, and writes nothing if any of them was changed since by something else, unless
  the owner says to go ahead for those;
- the manifest is written after every step, so that a crash leaves a record of exactly how far things got.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from . import paths


class Refused(Exception):
    """The safe folder cannot do what was asked; the text says why. Nothing was changed in the modlist."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Safe:
    def __init__(self, folder: Path):
        self.folder = folder
        self.files = folder / "files"
        self._manifest = folder / "manifest.json"
        self.items: list[dict] = []        # kept files: {"path", "copy", "size", "sha256", "written": sha or ""}
        self.added: list[dict] = []        # files ModTrap created: {"path", "sha256"}
        self.reverted = ""
        if self._manifest.is_file():
            try:
                with open(self._manifest, "rb") as f:
                    data = json.loads(f.read(64 * 1024 * 1024).decode("utf-8"))
                self.items, self.added = list(data["items"]), list(data["added"])
                self.reverted = str(data.get("reverted", ""))
            except (OSError, ValueError, KeyError, TypeError):
                raise Refused("the safe folder's record cannot be read; its copies are still in place") from None

    def _save(self) -> None:
        data = {"format": "modtrap-safe/1", "items": self.items, "added": self.added, "reverted": self.reverted}
        paths.write_atomic(self._manifest, (json.dumps(data, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    def _find(self, path: Path) -> dict | None:
        key = os.path.normcase(str(path))
        return next((i for i in self.items if os.path.normcase(i["path"]) == key), None)

    def take(self, path: Path) -> dict:
        """Copies `path` here, once, and checks the copy. Returns its record."""
        hit = self._find(path)
        if hit is not None:
            return hit
        if not path.is_file():
            raise Refused("%s is not there to be copied" % path.name)
        self.files.mkdir(parents=True, exist_ok=True)
        copy = "%04d-%s" % (len(self.items) + 1, path.name)
        shutil.copy2(path, self.files / copy)
        digest, size = sha256(path), path.stat().st_size
        if (self.files / copy).stat().st_size != size or sha256(self.files / copy) != digest:
            raise Refused("the copy of %s in the safe folder does not match the original" % path.name)
        item = {"path": str(path), "copy": copy, "size": size, "sha256": digest, "written": "",
                "taken": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self.items.append(item)
        self._save()
        return item

    def may_change(self, path: Path) -> None:
        """The check before every write to a file of the modlist (DESIGN§8 rule 3)."""
        item = self._find(path)
        if item is None:
            raise Refused("%s has no copy in the safe folder: it must not be changed" % path.name)
        if not (self.files / item["copy"]).is_file() or sha256(self.files / item["copy"]) != item["sha256"]:
            raise Refused("the safe folder's copy of %s is no longer what was taken" % path.name)

    def wrote(self, path: Path) -> None:
        """Notes what ModTrap left in a kept file, after writing it."""
        item = self._find(path)
        if item is None:
            raise Refused("%s has no copy in the safe folder" % path.name)
        item["written"] = sha256(path)
        self._save()

    def created(self, path: Path) -> None:
        """Notes a file ModTrap made (in its own mod): Revert removes it, if it is still as made."""
        self.added.append({"path": str(path), "sha256": sha256(path)})
        self._save()

    def check(self) -> dict:
        """What Revert would do, without doing it: per kept file "unchanged" (nothing to do), "ours" (ModTrap's
        change: put the original back), "foreign" (changed by something else since) or "gone"; and the same for
        the files ModTrap made."""
        out = {"restore": [], "nothing": [], "foreign": [], "remove": [], "foreign_added": []}
        for item in self.items:
            p = Path(item["path"])
            if not p.is_file():
                out["restore"].append(item["path"])                 # deleted since: the original comes back
                continue
            now = sha256(p)
            if now == item["sha256"]:
                out["nothing"].append(item["path"])
            elif item["written"] and now == item["written"]:
                out["restore"].append(item["path"])
            else:
                out["foreign"].append(item["path"])
        for a in self.added:
            p = Path(a["path"])
            if p.is_file():
                (out["remove"] if sha256(p) == a["sha256"] else out["foreign_added"]).append(a["path"])
        return out

    def revert(self, overwrite_foreign: bool = False) -> dict:
        """Puts every original back and removes what ModTrap made. If a file was changed since by something else,
        nothing at all is written, unless `overwrite_foreign` (the owner was shown those files and said yes)."""
        plan = self.check()
        if (plan["foreign"] or plan["foreign_added"]) and not overwrite_foreign:
            raise Refused("changed since by something other than ModTrap: %s. Nothing was put back." % ", ".join(
                Path(p).name for p in plan["foreign"] + plan["foreign_added"]))
        todo = plan["restore"] + (plan["foreign"] if overwrite_foreign else [])
        for item in reversed(self.items):
            if item["path"] not in todo:
                continue
            src, dst = self.files / item["copy"], Path(item["path"])
            if sha256(src) != item["sha256"]:
                raise Refused("the safe folder's copy of %s is no longer what was taken; stopped" % dst.name)
            tmp = dst.with_name(dst.name + ".modtrap-revert")
            shutil.copy2(src, tmp)
            os.replace(tmp, dst)
            if sha256(dst) != item["sha256"]:
                raise Refused("%s was put back but does not read back as the original; stopped" % dst.name)
        for a in self.added:
            p = Path(a["path"])
            if p.is_file() and (a["path"] in plan["remove"] or overwrite_foreign):
                p.unlink()
                try:
                    p.parent.rmdir()                                # only if ModTrap's folder is now empty
                except OSError:
                    pass
        self.reverted = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save()
        return plan
