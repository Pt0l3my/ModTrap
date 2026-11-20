import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from modtrap import api, logbook, server
from tests import _fixtures as fx


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logbook.set_console(False)
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["MODTRAP_HOME"] = str(Path(cls.tmp.name) / "home")
        cls.root = fx.small_list(Path(cls.tmp.name) / "Example List")
        cls.api = api.Api()
        cls.app = server.App(cls.api)
        cls.httpd = server.Server(0, cls.app)
        cls.port = cls.httpd.port
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        os.environ.pop("MODTRAP_HOME", None)
        cls.tmp.cleanup()
        logbook.set_console(True)

    def call(self, method, path, body=None, *, token=True, host=None, origin=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Host": host or "127.0.0.1:%d" % self.port}
        if token:
            headers[server.TOKEN_HEADER] = self.app.token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
            if origin:
                headers["Origin"] = "http://127.0.0.1:%d" % self.port
        conn.request(method, path, body=data, headers=headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r, raw

    def ready(self):
        for _ in range(100):
            r, raw = self.call("GET", "/api/state")
            s = json.loads(raw)
            if s["status"] in ("ready", "error"):
                return s
            time.sleep(0.05)
        self.fail("the instance was never read")

    def test_page_and_its_headers(self):
        r, raw = self.call("GET", "/", token=False)
        self.assertEqual(r.status, 200)
        csp = r.getheader("Content-Security-Policy")
        self.assertIn("default-src 'none'", csp)
        self.assertIn("nonce-" + self.app.nonce, csp)
        page = raw.decode()
        self.assertNotIn("__NONCE__", page)
        self.assertNotIn("/*__JS__*/", page)
        self.assertNotIn("http://", page.replace("http://127.0.0.1", ""))   # nothing loaded from outside
        self.assertNotIn("https://", page)

    def test_guards(self):
        self.assertEqual(self.call("GET", "/api/state", token=False)[0].status, 403)
        self.assertEqual(self.call("GET", "/", host="evil.example")[0].status, 403)
        self.assertEqual(self.call("GET", "/api/state", host="127.0.0.1:1")[0].status, 403)
        self.assertEqual(self.call("POST", "/api/open", {"folder": "x"}, origin=False)[0].status, 403)
        self.assertEqual(self.call("PUT", "/api/state")[0].status, 405)
        self.assertEqual(self.call("GET", "/api/nothing")[0].status, 404)

    def test_open_read_and_nothing_written(self):
        before = sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in self.root.rglob("*"))
        r, _ = self.call("POST", "/api/open", {"folder": str(self.root)})
        self.assertEqual(r.status, 200)
        s = self.ready()
        self.assertEqual((s["status"], s["profile"], s["mods"], s["issue_count"]), ("ready", "Default", 7, 0))
        self.assertEqual(s["tools"], [{"title": "xEdit", "output_mod": ""}])
        mods = json.loads(self.call("GET", "/api/mods")[1])["mods"]
        self.assertEqual(mods[0]["name"], "Tool Output")                  # highest priority first
        bramble = next(m for m in mods if m["name"] == "Bramble")
        self.assertEqual((bramble["priority"], bramble["dependants"], bramble["plugins"]), (1, 4, ["Bramble.esp"]))
        plugins = json.loads(self.call("GET", "/api/plugins")[1])["plugins"]
        self.assertEqual([p["position"] for p in plugins], list(range(12)))
        d = json.loads(self.call("GET", "/api/mod?name=Bramble")[1])
        self.assertEqual([(g["mod"], g["reading"]) for g in d["groups"]],
                         [("Lantern", "whole mod"), ("Bramble - Lantern Patch", "whole mod"),
                          ("Patch Collection", "some plugins"), ("Tool Output", "output")])
        one = json.loads(self.call("GET", "/api/plugin?name=generated.esp")[1])
        self.assertEqual(one["masters"], ["Skyrim.esm", "Bramble.esp", "Quill.esp"])
        self.assertEqual(self.call("GET", "/api/mod?name=Nobody")[0].status, 400)
        after = sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in self.root.rglob("*"))
        self.assertEqual(before, after)
        # The log masks the folder.
        lines = json.loads(self.call("GET", "/api/log?after=0")[1])["lines"]
        text = " ".join(ln["text"] for ln in lines)
        self.assertIn("<modlist>", text)
        self.assertNotIn(str(self.root), text)

    def test_a_folder_that_is_not_an_instance(self):
        r, _ = self.call("POST", "/api/open", {"folder": self.tmp.name})
        self.assertEqual(r.status, 200)
        s = self.ready()
        self.assertEqual(s["status"], "error")
        self.assertIn("ModOrganizer.ini", s["message"])
        self.assertNotIn(self.tmp.name, s["message"])
        self.call("POST", "/api/open", {"folder": str(self.root)})
        self.assertEqual(self.ready()["status"], "ready")


class MaskTests(unittest.TestCase):
    def test_folders_become_placeholders(self):
        logbook.set_masks({"<modlist>": "C:\\Modlists\\Example", "<game>": "C:\\Games\\Skyrim"})
        self.assertEqual(logbook.mask("read c:/modlists/example/mods/A and C:\\Games\\Skyrim\\Data"),
                         "read <modlist>/mods/A and <game>\\Data")
        logbook.set_masks({})


if __name__ == "__main__":
    unittest.main()
