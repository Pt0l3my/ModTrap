"""A stand-in for a modlist's tool started through MO2, for tests: it writes one file where it is told, or
nothing, and ends."""

import os
import sys
import time

if __name__ == "__main__":
    target = os.environ.get("FAKE_TOOL_WRITES", "")
    time.sleep(float(os.environ.get("FAKE_TOOL_SECONDS", "0.1")))
    if target:
        with open(target, "wb") as f:
            f.write(b"made again " + str(time.time()).encode())
    sys.exit(0)
