"""What ModTrap is doing, as stages and their tasks, for the Process tab (DESIGN§18, WHY§70).

A board: each job says what its tasks are when it starts and marks each as it goes. The page reads the board with
the state, every second, and draws it. The board decides nothing and holds no file's content: task texts are
ModTrap's own words with names of plugins and mods, as the log has them."""

from __future__ import annotations

import re
import threading

WAITING, GOING, DONE, FAILED, SKIPPED, YOURS = "waiting", "going", "done", "failed", "skipped", "yours"
STATES = (WAITING, GOING, DONE, FAILED, SKIPPED, YOURS)

# The tasks of each stage a job runs, in order: (key, text).
DRY = (("prepare", "Write the job for xEdit; copy and hash the dependants"),
       ("start", "Start xEdit through MO2"),
       ("ok", "Press OK in xEdit's Module Selection window"),
       ("load", "xEdit loads the plugins"),
       ("read", "Read what each dependant takes from the mod"),
       ("own", "Look through the mod's own plugins and the patches made for it"),
       ("close", "Close xEdit"),
       ("check", "Check that no plugin was changed; read the report"))
CHANGE = (("safe", "Copy every file that will change into the safe folder"),
          ("start", "Start xEdit through MO2 with the change script"),
          ("ok", "Press OK in xEdit's Module Selection window"),
          ("load", "xEdit loads the plugins"),
          ("change", "Take the mod out of each plugin, in memory; write the new plugins beside the originals"),
          ("close", "Close xEdit without saving anything"),
          ("verify", "Verify each new plugin: the mod is no longer a master, nothing else changed"))
INSTALL = (("mo2", "MO2 is closed"),
           ("mod", "Add ModTrap's own mod with the new plugins"),
           ("off", "Deactivate the patches made only for the mod"),
           ("disable", "Disable the mods"),
           ("reread", "Read the modlist again"),
           ("health", "Check the load order: no missing or inactive masters"))


class Board:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stages: dict[str, dict[str, dict]] = {}

    def begin(self, stage: str, tasks: tuple | list, drop: tuple = ()) -> None:
        """A stage starts over: its tasks, all waiting. Stages that come after it and are now out of date go."""
        with self._lock:
            for d in drop:
                self._stages.pop(d, None)
            self._stages[stage] = {k: {"key": k, "text": t, "state": WAITING, "note": ""} for k, t in tasks}

    def mark(self, stage: str, task: str, state: str, note: str | None = None, text: str | None = None) -> None:
        with self._lock:
            t = self._stages.setdefault(stage, {}).setdefault(task, {"key": task, "text": text or task,
                                                                     "state": WAITING, "note": ""})
            if t["state"] == FAILED and state == GOING:
                return
            t["state"] = state
            if note is None and state in (DONE, SKIPPED) and t["note"].startswith("waiting"):
                t["note"] = ""                    # what it waited for has come
            if note is not None:
                t["note"] = note
            if text is not None:
                t["text"] = text

    def state_of(self, stage: str, task: str) -> str:
        with self._lock:
            return self._stages.get(stage, {}).get(task, {}).get("state", "")

    def settle(self, stage: str, upto: str) -> None:
        """Every task before `upto` that is still waiting or going is done: the job got past it."""
        with self._lock:
            for k, t in self._stages.get(stage, {}).items():
                if k == upto:
                    return
                if t["state"] in (WAITING, GOING):
                    t["state"] = DONE
                    if t["note"].startswith("waiting"):
                        t["note"] = ""

    def stop(self, stage: str, why: str, state: str = FAILED) -> None:
        """The stage ended early: the task that was going, or else the first still waiting, carries why."""
        with self._lock:
            tasks = list(self._stages.get(stage, {}).values())
            hit = next((t for t in tasks if t["state"] == GOING), None) or \
                next((t for t in tasks if t["state"] == WAITING), None)
            if hit is not None:
                hit["state"], hit["note"] = state, why
            for t in tasks:
                if t["state"] == GOING:
                    t["state"] = WAITING

    def drop(self, *stages: str) -> None:
        with self._lock:
            for s in stages:
                self._stages.pop(s, None)

    def tasks(self, stage: str) -> list[dict]:
        with self._lock:
            return [dict(t) for t in self._stages.get(stage, {}).values()]


BOARD = Board()          # one ModTrap, one job at a time: one board

_LOADED = re.compile(r"^xEdit has loaded (\d+) files")
_READING = re.compile(r"^reading (.+) \((\d+) records\)$")
_DONE = re.compile(r"^done (.+?): ")
_LOOKED = re.compile(r"^looked through (.+?): ")
_CHANGING = re.compile(r"^changing (.+) in memory: ")
_WRITTEN = re.compile(r"^written: (.+)$")
_KEPT = re.compile(r"^kept as it was: (.+?)( \(| still)")


class Lines:
    """Reads the lines ModTrap's scripts write as they go, and marks the board from them."""

    def __init__(self, stage: str, total: int = 0, own_total: int = 0, board: Board | None = None):
        self.board, self.stage, self.total, self.own_total = board or BOARD, stage, total, own_total
        self.read = self.own = self.written = self.kept = 0

    def take(self, ln: str) -> None:
        b, s = self.board, self.stage
        got = _LOADED.match(ln)
        if ln == "started":
            if b.state_of(s, "ok") != DONE:
                b.mark(s, "ok", SKIPPED, "xEdit did not ask")
            b.settle(s, "load")
            b.mark(s, "load", GOING)
        elif got:
            b.settle(s, "load")
            b.mark(s, "load", DONE, "%s files" % got.group(1))
            b.mark(s, "read" if s == "dry" else "change", GOING)
        elif s == "dry" and _READING.match(ln):
            b.mark(s, "read", GOING, "%d of %d read; now %s" % (self.read, self.total, _READING.match(ln).group(1)))
        elif s == "dry" and _DONE.match(ln):
            self.read += 1
            b.mark(s, "read", DONE if self.total and self.read >= self.total else GOING,
                   "%d of %d read" % (self.read, self.total))
            if self.total and self.read >= self.total and self.own_total:
                b.mark(s, "own", GOING, "0 of %d" % self.own_total)
        elif s == "dry" and _LOOKED.match(ln):
            self.own += 1
            b.settle(s, "own")
            b.mark(s, "own", DONE if self.own_total and self.own >= self.own_total else GOING,
                   "%d of %d; last %s" % (self.own, self.own_total, _LOOKED.match(ln).group(1)))
        elif s != "dry" and _CHANGING.match(ln):
            b.mark(s, "change", GOING, "%d of %d written; now %s" % (self.written, self.total, _CHANGING.match(ln).group(1)))
        elif s != "dry" and _WRITTEN.match(ln):
            self.written += 1
            b.mark(s, "change", GOING, "%d of %d written" % (self.written, self.total))
        elif s != "dry" and _KEPT.match(ln):
            self.kept += 1
            b.mark(s, "change", GOING, "%d of %d written; kept as it was: %s" % (self.written, self.total, _KEPT.match(ln).group(1)))
        elif ln == "finished":
            b.settle(s, "close")
            if s != "dry":
                b.mark(s, "change", DONE, "%d of %d written%s" % (self.written, self.total,
                                                               ", %d kept as they were" % self.kept if self.kept else ""))
            b.mark(s, "close", GOING)
        elif ln.startswith("failed: "):
            b.stop(s, ln[len("failed: "):])


def stage_state(tasks: list[dict]) -> str:
    states = [t["state"] for t in tasks]
    if not states:
        return WAITING
    if FAILED in states:
        return FAILED
    if GOING in states:
        return GOING
    if all(x in (DONE, SKIPPED) for x in states):
        return DONE
    if YOURS in states:
        return YOURS
    return GOING if DONE in states else WAITING


__all__ = ["Board", "BOARD", "Lines", "stage_state", "DRY", "CHANGE", "INSTALL",
           "WAITING", "GOING", "DONE", "FAILED", "SKIPPED", "YOURS"]
