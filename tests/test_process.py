"""The board the Process tab reads (DESIGN§18, WHY§70)."""

from __future__ import annotations

import unittest

from modtrap import process as P


class TheBoard(unittest.TestCase):
    def states(self, b: P.Board, stage: str) -> dict:
        return {t["key"]: t["state"] for t in b.tasks(stage)}

    def test_a_dry_run_told_line_by_line(self) -> None:
        b = P.Board()
        b.begin("dry", P.DRY)
        self.assertEqual(P.stage_state(b.tasks("dry")), P.WAITING)
        b.mark("dry", "prepare", P.DONE)
        b.mark("dry", "start", P.DONE)
        b.mark("dry", "ok", P.GOING, "waiting for xEdit's window")
        told = P.Lines("dry", 2, 1, b)
        told.take("started")                           # the script runs: xEdit never asked which plugins to load
        self.assertEqual((self.states(b, "dry")["ok"], self.states(b, "dry")["load"]), (P.SKIPPED, P.GOING))
        told.take("xEdit has loaded 81 files; 1 trapped plugin(s)")
        told.take("reading Lantern.esp (3 records)")
        self.assertEqual([t["note"] for t in b.tasks("dry") if t["key"] == "read"], ["0 of 2 read; now Lantern.esp"])
        told.take("done Lantern.esp: 1 of 3 records need a trapped plugin")
        self.assertEqual(self.states(b, "dry")["read"], P.GOING)
        told.take("done Generated.esp: 2 of 3 records need a trapped plugin")
        self.assertEqual((self.states(b, "dry")["read"], self.states(b, "dry")["own"]), (P.DONE, P.GOING))
        told.take("looked through Bramble.esp: it changes 2 record(s) of other plugins, and has a stake in 1")
        self.assertEqual(self.states(b, "dry")["own"], P.DONE)
        told.take("finished")
        self.assertEqual(self.states(b, "dry")["close"], P.GOING)
        self.assertEqual(P.stage_state(b.tasks("dry")), P.GOING)

    def test_a_pressed_ok_stays_pressed(self) -> None:
        b = P.Board()
        b.begin("dry", P.DRY)
        b.mark("dry", "ok", P.GOING, "waiting for xEdit's window")
        b.mark("dry", "ok", P.DONE, "pressed")
        P.Lines("dry", 1, 0, b).take("started")
        self.assertEqual([(t["state"], t["note"]) for t in b.tasks("dry") if t["key"] == "ok"], [(P.DONE, "pressed")])

    def test_a_stop_names_the_task_it_stopped_at(self) -> None:
        b = P.Board()
        b.begin("change", P.CHANGE)
        b.mark("change", "safe", P.DONE)
        b.mark("change", "start", P.GOING)
        b.stop("change", "xEdit closed before the script finished")
        got = {t["key"]: (t["state"], t["note"]) for t in b.tasks("change")}
        self.assertEqual(got["start"], (P.FAILED, "xEdit closed before the script finished"))
        self.assertEqual(P.stage_state(b.tasks("change")), P.FAILED)
        b.mark("change", "start", P.GOING)             # a late mark does not paint over the failure
        self.assertEqual(self.states(b, "change")["start"], P.FAILED)
        b.begin("change", P.CHANGE, drop=("install",))  # a new run starts the stage over
        self.assertEqual(set(self.states(b, "change").values()), {P.WAITING})

    def test_the_change_run_counts_what_was_written_and_what_was_kept(self) -> None:
        b = P.Board()
        b.begin("change", P.CHANGE)
        told = P.Lines("change", 2, 0, b)
        for ln in ("started", "xEdit has loaded 81 files", "changing Lantern.esp in memory: 2 thing(s) to take out",
                   "written: Lantern.esp", "kept as it was: Generated.esp still needs a trapped plugin", "finished"):
            told.take(ln)
        got = {t["key"]: (t["state"], t["note"]) for t in b.tasks("change")}
        self.assertEqual(got["change"], (P.DONE, "1 of 2 written, 1 kept as they were"))
        self.assertEqual(got["close"][0], P.GOING)

    def test_a_stage_waits_for_the_owner_when_nothing_else_moves(self) -> None:
        self.assertEqual(P.stage_state([{"state": P.DONE}, {"state": P.YOURS}]), P.YOURS)
        self.assertEqual(P.stage_state([{"state": P.DONE}, {"state": P.SKIPPED}]), P.DONE)
        self.assertEqual(P.stage_state([{"state": P.DONE}, {"state": P.WAITING}]), P.GOING)
        self.assertEqual(P.stage_state([]), P.WAITING)


if __name__ == "__main__":
    unittest.main()
