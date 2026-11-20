"""A stand-in for "MO2 starting xEdit with ModTrap's script", for the tests: it reads the job file the real script
would read and writes the progress and report files the real script would write. It is given MO2's command line.
What it reports is invented: for each dependant, one record of the trapped plugin's own, one FormID-list entry and,
for a dependant whose name holds "Lantern", one field that needs the owner."""

import re
import sys
import time
from pathlib import Path


def chain(*steps):
    """The chain the real script writes for an element: steps from the element up to its record."""
    return "\x1e".join("\x1f".join(str(x) for x in st) for st in steps)


def main(argv):
    args = argv[argv.index("-a") + 1]
    mode = argv[argv.index("-a") + 2]   # the tool's title; the tests use it to choose a behaviour
    script = Path(re.search(r'-script:"([^"]+)"', args).group(1))
    plugins = Path(re.search(r'-P:"([^"]+)"', args).group(1))
    job = dict(ln.split("=", 1) for ln in (script.parent / "modtrap-job.txt").read_text(encoding="utf-8-sig").splitlines() if "=" in ln)
    loaded = [ln[1:] for ln in plugins.read_text(encoding="cp1252").splitlines() if ln.startswith("*")]
    trap = [job["trap.%d" % i] for i in range(int(job["trap.count"]))]
    deps = [job["dep.%d" % i] for i in range(int(job["dep.count"]))]
    progress, out = Path(job["progress"]), []
    said = []

    def say(s):
        said.append(s)
        progress.write_text("\r\n".join(said) + "\r\n")

    time.sleep(0.05)
    say("started")
    say("xEdit has loaded %d files; %d trapped plugin(s)" % (len(loaded) + 5, len(trap)))
    if mode == "crash":
        return 3
    out.append("H\tmodtrap-report/2\treport\t67175680")
    for d in deps:
        if d not in loaded:
            out.append("M\t" + d)
            continue
        out.append("F\t%s\t3\tSkyrim.esm,%s" % (d, trap[0]))
        say("reading %s (3 records)" % d)
        out.append("R\t%s\tMISC\t05000801\t%s\t1\tInventedThing" % (d, trap[0]))
        out.append("R\t%s\tFLST\t00012345\tSkyrim.esm\t0\tInventedList" % d)
        out.append("E\t%s\t00012345\tFLST \\ FormIDs \\ LNAM - FormID\t%s\t05000801\t%s" % (d, trap[0], chain(
            ("LNAM - FormID", "etSubRecord", "dtFormID", 0, 2), ("FormIDs", "etSubRecordArray", "dtSubRecordArray", 4, 1))))
        n = 2
        if "Lantern" in d:
            out.append("R\t%s\tNPC_\t00054321\tSkyrim.esm\t0\tInventedPerson" % d)
            out.append("E\t%s\t00054321\tNPC_ \\ RNAM - Race\t%s\t05000802\t%s" % (d, trap[0], chain(
                ("RNAM - Race", "etSubRecord", "dtFormID", 0, 9))))
            n = 3
        out.append("D\t%s\t3\t%d" % (d, n))
        say("done %s: %d of 3 records need a trapped plugin" % (d, n))
    if mode == "touch":                 # a misbehaving run that alters a dependant on disk
        target = next(Path(p) for p in argv if p.endswith(".esp") and Path(p).exists())
        target.write_bytes(target.read_bytes() + b"x")
    out.append("X\tok\t")
    Path(job["out"]).write_text("\r\n".join(out) + "\r\n")
    say("finished")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
