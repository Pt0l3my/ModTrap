"""The history (MT15, DESIGN§12): a dated, append-only record of everything ModTrap changed in a modlist, kept in
the session's folder.

NOT WRITTEN TO YET, since ModTrap changes nothing yet: groundwork for the demaster step (WHY§36).

Each line of `history.jsonl` is one event. Kinds: "mod disabled", "mod enabled", "plugin deactivated", "plugin
activated", "mod added", "plugin demastered", "reverted", "verified". A mod's event carries its priority, and for
each of its plugins the position in the load order and the kind (esm, esp, esl), as they were at that moment. A
plugin's own event carries them as `position` and `plugin_kind`, with its mod and that mod's priority.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


class History:
    def __init__(self, session_dir: Path):
        self.path = session_dir / "history.jsonl"

    def add(self, kind: str, **data: object) -> dict:
        """Appends one event and flushes it to disk before returning."""
        event = {"n": len(self.all()) + 1, "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, **data}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as f:
            f.write((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        return event

    def all(self) -> list[dict]:
        try:
            with open(self.path, "rb") as f:
                lines = f.read(64 * 1024 * 1024).decode("utf-8").splitlines()
        except OSError:
            return []
        out = []
        for ln in lines:
            try:
                e = json.loads(ln)
                if isinstance(e, dict):
                    out.append(e)
            except ValueError:
                continue                    # a line cut short by a crash is passed over, never repaired in place
        return out

    def disabled_now(self) -> dict[str, dict]:
        """The mods and plugins ModTrap switched off and has not switched on again since: name to the event that
        switched it off (with its priority or position), for Re-enable."""
        out: dict[str, dict] = {}
        for e in self.all():
            what = str(e.get("kind", "")).split(" ")[0]            # "mod" or "plugin"
            name = e.get(what)
            if what not in ("mod", "plugin") or not isinstance(name, str):
                continue
            if e["kind"] in ("mod disabled", "plugin deactivated"):
                out[what + ":" + name.casefold()] = e
            elif e["kind"] in ("mod enabled", "plugin activated"):
                out.pop(what + ":" + name.casefold(), None)
        return out
