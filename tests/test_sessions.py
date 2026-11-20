import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from modtrap import api, logbook, sessions
from modtrap.server import Bad
from tests import _fixtures as fx

FAKE = str(Path(__file__).with_name("fake_xedit.py"))


def fake_launcher(cmd, cwd):
    return subprocess.Popen([sys.executable, FAKE, *cmd[1:]], cwd=cwd)


class Base(unittest.TestCase):
    def setUp(self):
        logbook.set_console(False)
        logbook.clear()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(self.tmp.name) / "home")
        self.root = fx.small_list(Path(self.tmp.name) / "Example List")
        fx.write(self.root / "ModOrganizer.exe", b"not a real program")

    def tearDown(self):
        os.environ.pop("MODTRAP_HOME", None)
        self.tmp.cleanup()
        logbook.set_console(True)

    def new_api(self):
        a = api.Api()
        a.launcher, a.running, a.poll = fake_launcher, (lambda image: None), 0.05
        return a


class StoreTests(Base):
    def test_one_session_holds_a_modlist_and_the_next_waits(self):
        st = sessions.Store()
        a = st.create(str(self.root))
        self.assertEqual((a.name, a.status), ("Example List", sessions.ACTIVE))
        b = st.create(str(self.root).upper() if os.name == "nt" else str(self.root) + "/")   # the same folder, written otherwise
        self.assertEqual((b.name, b.status), ("Example List (2)", sessions.WAITING))
        self.assertEqual(st.open_for(str(self.root)).id, a.id)        # opening the modlist goes to its holder
        self.assertEqual(st.holder(str(self.root)).id, a.id)
        other = st.create(str(Path(self.tmp.name) / "Another List"))
        self.assertEqual(other.status, sessions.ACTIVE)               # another modlist is not held up
        done, nxt = st.finish(a.id)
        self.assertEqual((done.status, nxt.id, st.get(b.id).status), (sessions.FINISHED, b.id, sessions.ACTIVE))
        with self.assertRaises(sessions.Refused):
            st.finish(a.id)
        self.assertTrue((st.dir(a.id) / "session.json").is_file())

    def test_names(self):
        st = sessions.Store()
        a = st.create(str(self.root))
        b = st.create(str(Path(self.tmp.name) / "Another List"))
        self.assertEqual(st.rename(a.id, "  Taking out Bramble  ").name, "Taking out Bramble")
        for bad in ("", "   ", "x" * 81, "another list"):
            with self.subTest(bad[:12]):
                with self.assertRaises(sessions.Refused):
                    st.rename(a.id, bad)
        self.assertEqual(st.get(b.id).name, "Another List")
        for sid in ("../x", "", "A B", "x/../../y"):
            with self.assertRaises(sessions.Refused):
                st.dir(sid)


class ApiTests(Base):
    def test_opening_makes_a_session_and_reopening_returns_to_it(self):
        a = self.new_api()
        a.open(str(self.root), wait=True)
        s = a.state()
        self.assertEqual((s["session"]["name"], s["session"]["status"], s["session"]["locked"]),
                         ("Example List", "active", ""))
        first = s["session"]["id"]
        a.open(str(self.root), wait=True)
        self.assertEqual(a.state()["session"]["id"], first)
        self.assertEqual(len(a.state()["sessions"]), 1)

    def test_a_second_session_is_locked_until_the_first_is_finished(self):
        a = self.new_api()
        a.open(str(self.root), wait=True)
        first = a.session.id
        made = a.session_new()
        self.assertEqual(made["status"], "waiting")
        self.assertEqual(a.session.name, "Example List (2)")
        self.assertIn("still holds this modlist", a.state()["session"]["locked"])
        for call in (a.dry_plan, a.dry_start):
            with self.assertRaises(Bad) as c:
                call({"mods": ["Bramble"]})
            self.assertIn("waiting", str(c.exception))
        a.session_rename({"name": "Second go"})
        out = a.session_finish({"id": first})
        self.assertEqual(out["unlocked"], a.session.id)
        self.assertEqual((a.state()["session"]["status"], a.state()["session"]["locked"]), ("active", ""))
        self.assertEqual(a.dry_plan({"mods": ["Bramble"]})["trapped"], ["Bramble.esp"])
        # The finished session can still be looked at, and says why it cannot work.
        a.session_switch({"id": first})
        self.assertIn("finished", a.state()["session"]["locked"])
        with self.assertRaises(Bad):
            a.dry_plan({"mods": ["Bramble"]})

    def test_quit_and_start_again_brings_the_same_state_back(self):
        a = self.new_api()
        a.open(str(self.root), wait=True)
        ui = {"tab": "plugins", "picked": ["Bramble"], "order": "deps", "search": "lan", "collapsed": ["Outputs_separator"]}
        a.session_ui({"ui": ui})
        a.session_rename({"name": "Taking out Bramble"})
        a.dry_start({"mods": ["Bramble"]})
        a.job.join(20)
        self.assertEqual(a.job.state, "done", a.job.message)
        sid, job_id = a.session.id, a.job.id
        quit_called = []
        a.on_quit = lambda: quit_called.append(True)
        answer, after = a.quit({})
        self.assertEqual(answer, {"quit": True})
        after()
        self.assertEqual(quit_called, [True])

        logbook.clear()                                       # a new start of ModTrap
        b = self.new_api()
        self.assertTrue(b.restore())
        for _ in range(200):
            if b.status in ("ready", "error"):
                break
            import time
            time.sleep(0.02)
        s = b.state()
        self.assertEqual((s["status"], s["session"]["id"], s["session"]["name"]), ("ready", sid, "Taking out Bramble"))
        self.assertEqual(s["session"]["ui"], ui)
        job = b.job_state()["job"]
        self.assertEqual((job["id"], job["state"], job["past"]), (job_id, "done", True))
        self.assertEqual(len(job["result"]["files"]), 4)
        text = " ".join(ln["text"] for ln in logbook.lines_after(0)[0])
        self.assertIn("xEdit: finished", text)                # the log is back
        self.assertIn("ModTrap is closing", text)
        self.assertEqual(b._cache.read_count, 0)              # no plugin had to be read again

    def test_quit_while_a_dry_run_is_going_asks_first(self):
        a = self.new_api()
        a.open(str(self.root), wait=True)

        class Going:
            state, id = "reading", "x"

            def stop(self):
                self.stopped = True

            def public(self):
                return {}
        a.job = Going()
        with self.assertRaises(Bad):
            a.quit({})
        with self.assertRaises(Bad):
            a.session_new()
        with self.assertRaises(Bad):
            a.session_finish({})
        answer, _ = a.quit({"force": True})
        self.assertTrue(answer["quit"] and a.job.stopped)

    def test_a_job_cut_short_by_closing_says_so_afterwards(self):
        a = self.new_api()
        a.open(str(self.root), wait=True)
        d = a.store.dir(a.session.id) / "jobs" / "dryrun-20260101-000000"
        d.mkdir(parents=True)
        a.session.last_job = d.name
        a.store.save(a.session)
        b = self.new_api()
        b.restore()
        b_job = None
        for _ in range(200):
            if b.status == "ready":
                b_job = b.job_state()["job"]
                break
            import time
            time.sleep(0.02)
        self.assertEqual(b_job["state"], "failed")
        self.assertIn("closed while this dry run was going", b_job["message"])


if __name__ == "__main__":
    unittest.main()
