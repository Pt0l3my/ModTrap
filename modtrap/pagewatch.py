"""Is ModTrap's page still open? (MT64, DESIGN§26)

ModTrap has no window (MT63), so a closed tab would leave it running unseen. A browser gives a page no sure way to
say "my tab was closed"; what there is, is used together:

- every request of a page carries that page's own mark, so ModTrap knows which pages there are and when each last
  asked something (an open page asks about once a second, a hidden one at least once a minute);
- a page that is left (closed, reloaded, sent elsewhere) says goodbye as it goes. A reload says goodbye too and is
  back at once, so ModTrap waits a few seconds before it believes it;
- a page the browser puts to sleep says so first, and is then not counted as gone for being silent;
- a page that neither asks nor said anything for minutes is gone without a word: its browser was ended.

`due()` says when ModTrap should close for want of a page. It never says so before a page was first open, and
whoever asks decides whether anything is in hand that must not be left.
"""

from __future__ import annotations

import re
import threading
import time

GRACE = 8.0            # after the last page's goodbye: a reload is back well within this
SILENCE = 240.0        # without a word from a page that did not say goodbye
STALL = 30.0           # a gap this long between two looks means the PC slept: nobody is counted as gone for it
MARK = re.compile(r"^[A-Za-z0-9_-]{6,40}$")


class Watch:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._pages: dict[str, float] = {}       # a page's mark -> when it last asked
        self._asleep: set[str] = set()
        self._left: float | None = None          # when the last page said goodbye
        self._looked = clock()
        self.ever = False                        # a page was open at some time
        self._why = "its page was closed"

    def seen(self, page: str | None) -> None:
        if not page or not MARK.match(page):
            return
        with self._lock:
            self._pages[page] = self._clock()
            self._asleep.discard(page)
            self._left = None
            self.ever = True

    def said(self, page: str | None, what: str) -> bool:
        """A page's word as it goes: "bye" (left) or "asleep" (put to sleep by the browser)."""
        if not page or not MARK.match(page) or what not in ("bye", "asleep"):
            return False
        with self._lock:
            if what == "asleep":
                if page in self._pages:
                    self._asleep.add(page)
                return True
            self._pages.pop(page, None)
            self._asleep.discard(page)
            if not self._pages:
                self._left, self._why = self._clock(), "its page was closed"
            return True

    def pages(self) -> int:
        with self._lock:
            return len(self._pages)

    def due(self) -> str:
        """Why ModTrap should close now for want of a page, or "" while it should not."""
        now = self._clock()
        with self._lock:
            if now - self._looked > STALL:        # the PC slept, or this program was held: time that no page could use
                gap = now - self._looked
                self._pages = {k: v + gap for k, v in self._pages.items()}
                if self._left is not None:
                    self._left += gap
            self._looked = now
            if not self.ever:
                return ""
            silent = [k for k, v in self._pages.items() if now - v > SILENCE and k not in self._asleep]
            for k in silent:
                del self._pages[k]
            if self._pages:
                return ""
            if silent:
                self._why = "no page has asked anything for %d minutes" % (SILENCE // 60)
                self._left = now - GRACE
            elif self._left is None:
                self._left = now
            if now - self._left < GRACE:
                return ""
            return self._why


__all__ = ["GRACE", "SILENCE", "Watch"]
