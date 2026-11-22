"""A stand-in for a modlist's tool started through MO2, for tests: it writes one file where it is told, or
nothing, and ends; or, as a MO2 that stops at a message after the tool, stays until a file appears."""

import os
import sys
import time

if __name__ == "__main__":
    target = os.environ.get("FAKE_TOOL_WRITES", "")
    time.sleep(float(os.environ.get("FAKE_TOOL_SECONDS", "0.1")))
    if target:
        with open(target, "wb") as f:
            f.write(b"made again " + str(time.time()).encode())
    until = os.environ.get("FAKE_TOOL_UNTIL", "")          # a MO2 that stops at a message until it is closed
    end = time.time() + 10
    while until and not os.path.exists(until) and time.time() < end:
        time.sleep(0.02)
    sys.exit(0)
