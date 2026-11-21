"""One ModTrap at a time (WHY§68).

A ModTrap that is started while another is still running would open a second page on another port, and the owner
could go on working in the older one without knowing. So a running ModTrap leaves a note in its own folder (its
port, its version, a key made for this start), and a new start asks the running one, with that key, to save its
session and close. It then takes its place. A ModTrap in the middle of a job is not interrupted: the new start
says so and ends.

The key is not the page's token. It is read from ModTrap's folder on this PC, which no web page can read, and it
opens one thing only: this request."""

from __future__ import annotations

import http.client
import json
import os
import socket
import time

from . import VERSION, paths

PATH = "/api/handover"
HEADER = "X-ModTrap-Handover"
NOTE = "running.json"
HOST = "127.0.0.1"


def note(port: int, key: str) -> None:
    """Leaves this start's note. Not being able to is no reason not to run."""
    try:
        paths.write_atomic(paths.home() / NOTE, (json.dumps({"port": port, "key": key, "version": VERSION,
                                                              "pid": os.getpid()}, indent=1) + "\n").encode("utf-8"))
    except OSError:
        pass


def running() -> dict | None:
    try:
        with open(paths.home() / NOTE, "rb") as f:
            data = json.loads(f.read(65536).decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("port"), int) or not isinstance(data.get("key"), str):
        return None
    return data if 0 < data["port"] < 65536 else None


def clear(key: str | None = None) -> None:
    """Removes the note: this start's own at its end (by its key), or a note nobody answers for."""
    r = running()
    if r is not None and key is not None and r["key"] != key:
        return                                    # another start's note by now
    try:
        (paths.home() / NOTE).unlink()
    except OSError:
        pass


def _listening(port: int) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=0.5):
            return True
    except OSError:
        return False


def take_over(wait: float = 20.0) -> tuple[str, str, str]:
    """Asks the ModTrap that is running, if one is, to save and close. Answers (what, version, text):
    "none": nothing was running; "quit": it closed, and its port is free; "busy": it is in the middle of a job and
    stays, `text` being its page's address; "stays": it said it would close but its port is still held."""
    r = running()
    if r is None:
        return "none", "", ""
    was = str(r.get("version") or "")
    try:
        conn = http.client.HTTPConnection(HOST, r["port"], timeout=5)
        try:
            conn.request("POST", PATH, body=b"", headers={HEADER: r["key"], "Content-Length": "0"})
            resp = conn.getresponse()
            data = json.loads(resp.read(65536).decode("utf-8") or "{}")
        finally:
            conn.close()
    except (OSError, http.client.HTTPException, ValueError):
        clear()                                   # nobody answers there: a note left by a start that was ended
        return "none", "", ""
    if resp.status == 409:
        return "busy", was, "http://%s:%d/" % (HOST, r["port"])
    if resp.status != 200 or not isinstance(data, dict) or data.get("quit") is not True:
        clear()                                   # that port is another program's now
        return "none", "", ""
    end = time.monotonic() + wait
    while _listening(r["port"]):
        if time.monotonic() > end:
            return "stays", was, ""
        time.sleep(0.2)
    return "quit", was, ""

