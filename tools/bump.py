"""Raises ModTrap's version after a change to its files (WHY§68).

    python3 tools/bump.py           write the new mark; raise the version if this commit has not raised it yet
    python3 tools/bump.py --check   say whether the version matches the files; exit 1 when it does not
    python3 tools/bump.py --raise   raise it even where git cannot tell what the last commit held

Run it before every commit that changes anything under `modtrap/`. `tests/test_version.py` fails until it is."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from modtrap import version  # noqa: E402


def committed() -> tuple[str, str]:
    """The version and mark of the last commit, or two empty texts when git cannot say."""
    try:
        out = subprocess.run(["git", "show", "HEAD:modtrap/" + version.RECORD], cwd=REPO, capture_output=True,
                             timeout=20, check=True).stdout
        data = json.loads(out.decode("utf-8"))
        return str(data["version"]), str(data["mark"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return "", ""


def main(argv: list[str]) -> int:
    now, (was, mark) = version.code_mark(), version.recorded()
    if now == mark:
        print("ModTrap %s: the version matches the files" % was)
        return 0
    if "--check" in argv:
        print("ModTrap %s: the files have changed since this version was written; run tools/bump.py" % was)
        return 1
    last, last_mark = committed()
    # Raised once for each commit: a second run before the commit only writes the new mark. Files brought back to
    # the last commit's state take its version back.
    if not last:                                  # the last commit has no version yet, or git cannot say
        new = was if was != "unknown" and "--raise" not in argv else version.raised(was if was != "unknown" else "0.3.0")
    else:
        new = last if now == last_mark else was if was != last else version.raised(was)
    (REPO / "modtrap" / version.RECORD).write_text(json.dumps({"version": new, "mark": now}, indent=1) + "\n",
                                                   encoding="utf-8", newline="\n")
    print("ModTrap %s -> %s" % (was, new))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
