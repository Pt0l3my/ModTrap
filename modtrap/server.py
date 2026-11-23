"""The HTTP server: the Host, Origin and token guard, the headers and the content policy, the page's assembly
(DESIGN§2).

Taken from DataPiler's page server (the owner's MIT project; NOTICE): `App`, `Handler`, `Server` and `Bad`, with
ModTrap's token header and page files, its own log, and no upload path. ModTrap's endpoints live in api.py. The
server binds 127.0.0.1 only."""

from __future__ import annotations

import hmac
import http.server
import json
import os
import re
import secrets
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Protocol

from . import NAME, logbook

HOST = "127.0.0.1"
PAGE_DIR = Path(__file__).resolve().parent / "page"
# The page's script and style, each assembled from these files in this order.
PAGE_JS = ("app.js",)
PAGE_CSS = ("app.css",)
TOKEN_HEADER = "X-ModTrap-Token"
HANDOVER_PATH = "/api/handover"
HANDOVER_HEADER = "X-ModTrap-Handover"
LOCATE_PATH = "/api/locate"
SAVE_PATH = "/api/save/download"  # the packed session, handed out once (WHY§48)
UPLOAD_PATH = "/api/add/upload"   # a dropped mod archive, as its bytes (DESIGN§16.1)
LIST_PATH = "/api/updates/upload" # the list of a dropped Wabbajack file, as its bytes (DESIGN§20)
SELF_PATH = "/api/selfupdate/upload"   # a ModTrap release file, as its bytes (MT58)
SELF_MAX = 600 * 1024 * 1024
METAS_PATH = "/api/updates/metas" # dropped meta files, as their texts
METAS_MAX = 4 * 1024 * 1024
UPLOAD_MAX = 64 * 1024 ** 3
LOCATE_MAX = 3 * 1024 * 1024      # a dropped folder's ModOrganizer.ini in base64, and the folder's name
POST_MAX = 64 * 1024
# A request refused before its body is read: the answer is sent, then whatever of the body is still arriving is read
# and dropped, up to these limits, before the connection closes. Closing with it unread makes Windows send a reset,
# which a client may meet before it reads the answer (WinError 10053); Linux's client meets a broken pipe instead.
LINGER_BYTES = 8 * 1024 * 1024
LINGER_SECONDS = 3.0
CSP = ("default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; connect-src 'self'; img-src 'self' data:; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
# A browser that closes or resets a connection mid-answer (a reload, a closed tab): dropped without a line.
# ConnectionError covers ConnectionResetError, ConnectionAbortedError and BrokenPipeError.
QUIET_ERRORS = (ConnectionError, TimeoutError)

log = logbook.get("page")


class Bad(Exception):
    """A request refused, in words the page shows (ModTrap's own; masked before they leave)."""

    def __init__(self, text: str, field: str | None = None):
        super().__init__(text)
        self.field = field


class ApiLike(Protocol):
    def get(self, path: str, query: dict[str, str]) -> tuple[int, object]: ...
    def post(self, path: str, body: dict) -> tuple[int, object, Callable[[], None] | None]: ...


class App:
    """One start's page: its server, token, nonce, the hosts and origins it answers, the API and the page."""

    def __init__(self, api: ApiLike | None = None):
        self.httpd: "Server | None" = None
        self.token = secrets.token_urlsafe(24)
        self.nonce = secrets.token_urlsafe(16)
        self.handover = secrets.token_urlsafe(24)     # for another start of ModTrap on this PC, never the page (WHY§68)
        self.hosts: set[str] = set()
        self.origins: set[str] = set()
        self.api = api
        self.page = b""

    def bound(self, port: int) -> None:
        self.hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        self.origins = {"http://127.0.0.1:%d" % port, "http://localhost:%d" % port}
        self.page = assemble(self.nonce, self.token)


def _joined(folder: Path, names: tuple[str, ...]) -> str:
    """The files joined with a newline, in order; a missing one raises OSError (FileNotFoundError)."""
    return "\n".join((folder / name).read_text(encoding="utf-8") for name in names)


def assemble(nonce: str, token: str, folder: Path = PAGE_DIR) -> bytes:
    """index.html with PAGE_CSS's files in its one <style nonce> and PAGE_JS's in its one <script nonce>: each
    tuple's files joined with a newline, in order. A missing file is an error."""
    html = (folder / "index.html").read_text(encoding="utf-8")
    css = _joined(folder, PAGE_CSS)
    js = _joined(folder, PAGE_JS)
    page = html.replace("/*__CSS__*/", css).replace("/*__JS__*/", js)
    return page.replace("__NONCE__", nonce).replace("__TOKEN__", token).encode("utf-8")


class _Refusals:
    """Refused requests are logged by reason only, at most once per reason in 10 s."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}

    def note(self, why: str) -> None:
        now = time.monotonic()
        with self._lock:
            if now - self._last.get(why, -1e9) < 10:
                return
            self._last[why] = now
        log.warn("refused a request: %s", why)


_refusals = _Refusals()


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = NAME
    sys_version = ""
    protocol_version = "HTTP/1.1"
    server: "Server"

    def log_message(self, *a: object) -> None:
        pass

    def setup(self) -> None:
        super().setup()
        self._unread = 0

    def _will_not_read(self) -> None:
        """This request's body will not be read: drain it after the answer (LINGER_BYTES, LINGER_SECONDS)."""
        self.close_connection = True
        headers = getattr(self, "headers", None)  # the standard library's errors can come before the headers
        try:
            n = int(headers.get("Content-Length") or 0) if headers is not None else 0
        except ValueError:
            n = LINGER_BYTES
        if headers is not None and headers.get("Transfer-Encoding"):
            n = LINGER_BYTES
        self._unread = max(0, min(n, LINGER_BYTES))

    def finish(self) -> None:
        try:
            super().finish()
        finally:
            if self._unread:
                self._drain()

    def _drain(self) -> None:
        sock = self.connection
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            return
        left = self._unread
        end = time.monotonic() + LINGER_SECONDS
        try:
            while left > 0:
                wait = end - time.monotonic()
                if wait <= 0:
                    break
                sock.settimeout(min(wait, 0.5))
                chunk = sock.recv(min(65536, left))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def version_string(self) -> str:
        return self.server_version

    @property
    def app(self) -> App:
        return self.server.app

    def send(self, code: int, body: object, ctype: str = "application/json", extra: dict | None = None) -> None:
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CSP % (self.app.nonce, self.app.nonce))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_file(self, path, name: str) -> None:
        """A file as a download, sent once and then removed (the packed session, WHY§48). Its name is ModTrap's
        own: letters, digits, dots, dashes."""
        try:
            size = os.path.getsize(path)
            f = open(path, "rb")
        except OSError:
            return self.send(404, {"error": "the file to download is no longer there"})
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-7z-compressed")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % re.sub(r"[^A-Za-z0-9._-]", "-", name))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", CSP % (self.app.nonce, self.app.nonce))
            self.end_headers()
            while True:
                block = f.read(256 * 1024)
                if not block:
                    break
                self.wfile.write(block)
        finally:
            f.close()
            try:
                os.remove(path)
            except OSError:
                pass

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """The standard library's own errors (a bad request line, a method it lacks) with ModTrap's headers."""
        try:
            self._will_not_read()
            self.send(code, {"error": "not understood" if code < 500 else "failed"})
        except OSError:
            pass

    def guard(self, post: bool) -> str:
        """Only this page: the Host it was opened at, its own Origin on a write, and this start's token."""
        if self.headers.get("Host", "") not in self.app.hosts:
            return "not this page's host"
        if post and self.headers.get("Origin", "") not in self.app.origins:
            return "not this page's origin"
        if self.path.split("?")[0].startswith("/api/"):
            got = self.headers.get(TOKEN_HEADER, "").encode("utf-8", "surrogateescape")
            if not hmac.compare_digest(got, self.app.token.encode("ascii")):
                return "no token"
        return ""

    def _refuse(self, why: str) -> None:
        _refusals.note(why)
        # A refused request's body is never read, so the connection cannot carry another request: on a kept-alive
        # connection the unread body would be read as the next request line. What is still arriving is drained.
        self._will_not_read()
        self.send(403, {"error": why}, extra={"Connection": "close"})

    def _error(self, e: BaseException) -> None:
        if isinstance(e, Bad):
            body = {"error": logbook.mask(str(e))}
            if e.field:
                body["field"] = e.field
            return self.send(400, body)
        if isinstance(e, OSError):
            return self.send(500, {"error": logbook.why(e)})
        if isinstance(e, ValueError):
            return self.send(400, {"error": "the request was not accepted"})
        logbook.get("app").error("a request failed: %s", logbook.why(e))
        return self.send(500, {"error": logbook.why(e)})

    def do_GET(self) -> None:  # noqa: N802 - the standard library's name
        why = self.guard(False)
        if why:
            return self._refuse(why)
        path, _, q = self.path.partition("?")
        try:
            query = {k: v[0] for k, v in urllib.parse.parse_qs(q, keep_blank_values=True).items()}
        except ValueError:
            query = {}
        try:
            if path == "/":
                return self.send(200, self.app.page, "text/html; charset=utf-8")
            if path == SAVE_PATH and self.app.api is not None:
                take = getattr(self.app.api, "save_take", None)
                got = take() if take is not None else None
                if got is None:
                    return self.send(404, {"error": "there is nothing to download: press “Save this session” again"})
                return self.send_file(got[0], got[1])
            if path.startswith("/api/") and self.app.api is not None:
                code, body = self.app.api.get(path, query)
                return self.send(code, body)
        except Exception as e:
            return self._error(e)
        return self.send(404, {"error": "not found"})

    def do_HEAD(self) -> None:  # noqa: N802
        why = self.guard(False)
        if why:
            return self._refuse(why)
        if self.path.partition("?")[0] == "/":
            return self.send(200, self.app.page, "text/html; charset=utf-8")
        return self.send(404, {"error": "not found"})

    def _handover(self) -> None:
        """Another start of ModTrap on this PC asks this one to save and close (WHY§68). It is not a page: it sends
        no Origin, and it has this start's key from ModTrap's own folder, which no web page can read."""
        got = self.headers.get(HANDOVER_HEADER, "").encode("utf-8", "surrogateescape")
        if (self.headers.get("Host", "") not in self.app.hosts or self.headers.get("Origin") is not None
                or (self.headers.get("Content-Length") or "0") != "0" or self.headers.get("Transfer-Encoding")
                or not hmac.compare_digest(got, self.app.handover.encode("ascii"))):
            return self._refuse("not a handover")
        ask = getattr(self.app.api, "handover", None)
        if ask is None:
            return self.send(404, {"error": "not found"})
        try:
            answer, after = ask()
        except Bad as e:
            return self.send(409, {"error": str(e)})
        except Exception as e:
            return self._error(e)
        self.send(200, answer)
        if after is not None:
            try:
                self.wfile.flush()
            except OSError:
                pass
            threading.Thread(target=after, name="after-answer", daemon=True).start()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == HANDOVER_PATH:
            return self._handover()
        why = self.guard(True)
        if why:
            return self._refuse(why)
        path = self.path.split("?")[0]
        if self.headers.get("Transfer-Encoding"):
            self._will_not_read()
            return self.send(400, {"error": "a request needs its length"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        cap = LOCATE_MAX if path == LOCATE_PATH else UPLOAD_MAX if path in (UPLOAD_PATH, LIST_PATH) else METAS_MAX if path == METAS_PATH else SELF_MAX if path == SELF_PATH else POST_MAX
        if n < 0:
            self._will_not_read()
            return self.send(400, {"error": "no length"})
        if n > cap:
            self._will_not_read()
            return self.send(413, {"error": "too large"})
        if path == LIST_PATH:
            take = getattr(self.app.api, "updates_upload", None)
            if take is None:
                self._will_not_read()
                return self.send(404, {"error": "not found"})
            try:
                return self.send(200, take(urllib.parse.parse_qs(self.path.partition("?")[2], keep_blank_values=True), n, self.rfile))
            except Exception as e:
                self.close_connection = True          # what is left of the body is not read
                return self._error(e)
        if path == SELF_PATH:
            take = getattr(self.app.api, "self_upload", None)
            if take is None:
                self._will_not_read()
                return self.send(404, {"error": "not found"})
            try:
                query = urllib.parse.parse_qs(self.path.partition("?")[2], keep_blank_values=True)
                return self.send(200, take(query.get("name", [""])[0], n, self.rfile))
            except Exception as e:
                self.close_connection = True          # what is left of the body is not read
                return self._error(e)
        if path == UPLOAD_PATH:
            # The body is the file itself, written to ModTrap's work folder as it arrives; never held in memory.
            upload = getattr(self.app.api, "upload", None)
            if upload is None:
                self._will_not_read()
                return self.send(404, {"error": "not found"})
            try:
                query = urllib.parse.parse_qs(self.path.partition("?")[2], keep_blank_values=True)
                updates = query.get("updates", [""])[0]
                return self.send(200, upload(query.get("name", [""])[0], n, self.rfile, updates) if updates
                                 else upload(query.get("name", [""])[0], n, self.rfile))
            except Exception as e:
                self.close_connection = True          # what is left of the body is not read
                return self._error(e)
        try:
            raw = self.rfile.read(n) if n else b""
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                raise Bad("a request is a JSON object") from None
            if not isinstance(body, dict):
                raise Bad("a request is a JSON object")
            if path.startswith("/api/") and self.app.api is not None:
                code, answer, after = self.app.api.post(path, body)
                if code == 404:
                    return self.send(404, {"error": "not found"})
                self.send(code, answer)
                if after is not None:
                    try:
                        self.wfile.flush()
                    except OSError:
                        pass
                    threading.Thread(target=after, name="after-answer", daemon=True).start()
                return
        except Exception as e:
            return self._error(e)
        return self.send(404, {"error": "not found"})

    def _no(self) -> None:
        why = self.guard(False)
        if why:
            return self._refuse(why)
        self._will_not_read()
        self.send(405, {"error": "not allowed"})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _no


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    # Never SO_REUSEADDR on Windows, where it would let another program bind the page's port beside this one. Elsewhere
    # it only lets the port be bound again while the last run's closed connections wait out TIME_WAIT, as Windows
    # allows without it. A port another program listens on is refused either way.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, port: int, app: App):
        self.app = app
        super().__init__((HOST, port), Handler)
        app.httpd = self
        app.bound(self.server_address[1])

    def handle_error(self, request: object, client_address: object) -> None:
        """Replaces socketserver's, which prints the traceback (ModTrap's folders and the user's home in it) to
        stderr, the window the owner reads and copies from. A connection the browser dropped is not an error;
        anything else is logged by its type only."""
        e = sys.exc_info()[1]
        if e is None or isinstance(e, QUIET_ERRORS):
            return
        log.error("a request failed: %s", logbook.why(e))

    @property
    def port(self) -> int:
        return int(self.server_address[1])
