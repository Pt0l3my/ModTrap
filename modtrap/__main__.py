"""`python -m modtrap scan FOLDER [--profile NAME] [--mod NAME] [--plugin NAME]`: read an MO2 instance and print what ModTrap
sees. Read-only: it opens the instance's text files and each plugin's header, and writes nothing anywhere."""

from __future__ import annotations

import argparse
import sys

from . import NAME, VERSION, instance, model


def scan(a: argparse.Namespace) -> int:
    try:
        inst = instance.load(a.folder, a.profile)
    except instance.Unusable as e:
        print("%s cannot read this folder: %s" % (NAME, e))
        return 2
    m = model.build(inst)
    real = [x for x in inst.mods if x.kind == "mod"]
    rows = [m.plugins[f] for f in m.order]
    print("%s %s (read-only scan)" % (NAME, VERSION))
    print("Game: %s   Profile: %s   Other profiles: %d" % (inst.game_name or "?", inst.profile,
                                                           len(inst.profiles) - 1))
    print("Mods: %d (%d enabled), separators: %d" % (len(real), sum(x.enabled for x in real),
                                                     sum(x.kind == "separator" for x in inst.mods)))
    print("Plugins: %d in the load order, %d active, %d unreadable" % (
        sum(r.position is not None for r in rows), sum(r.active for r in rows),
        sum(bool(r.unreadable) and r.source is not None for r in rows)))
    print("Tools set up in MO2: %s" % (", ".join(e.title for e in inst.executables) or "none found"))
    for note in inst.notes:
        print("Note: " + note)
    if m.issues:
        print("Health check: %d problem(s)" % len(m.issues))
        for i in m.issues[:50]:
            print("  %s needs %s, which is %s" % (i.plugin, i.master,
                                                  "not active" if i.what == "inactive" else "missing"))
    else:
        print("Health check: clean (no active plugin has a missing or inactive master)")
    if a.mod:
        mod = inst.mod(a.mod)
        if mod is None:
            print("No mod of that name in this profile.")
            return 1
        print("\n%s: priority %d, %s" % (mod.name, mod.priority, "enabled" if mod.enabled else "disabled"))
        for r in m.provided_by(mod):
            print("  plugin %s  [%s]  position %s  masters: %s" % (r.name, r.kind, r.position,
                                                                  ", ".join(r.masters) or "none"))
        gs = model.groups(m, mod)
        print("  %d plugin(s) in %d other mod(s) depend on it:" % (sum(len(g.dependants) for g in gs), len(gs)))
        words = {"output": "made by a tool: %s",
                 "whole mod": "every plugin of this mod depends on it",
                 "some plugins": "%d other plugin(s) of this mod do not depend on it"}
        for g in gs:
            what = words[g.reading] % (", ".join(g.made_by) if g.reading == "output" else g.others) \
                if g.reading != "whole mod" else words[g.reading]
            print("  in mod '%s' (priority %d): %s" % (g.mod.name, g.mod.priority, what))
            for r in g.dependants:
                print("    %-58s position %-5s masters: %d" % (r.name, r.position, len(r.masters)))
    if a.plugin:
        r = m.row(a.plugin)
        if r is None:
            print("No plugin of that name in this profile.")
            return 1
        print("\n%s  [%s]  position %s  %s  in mod '%s'" % (r.name, r.kind or "?", r.position,
                                                         "active" if r.active else "not active", r.source))
        if r.unreadable:
            print("  could not be read: " + r.unreadable)
        print("  masters (%d): %s" % (len(r.masters), ", ".join(r.masters) or "none"))
        print("  needed by (%d): %s" % (len(r.dependants), ", ".join(r.dependants) or "nothing"))
    return 1 if m.issues else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modtrap", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="read an instance and print a summary; writes nothing")
    s.add_argument("folder", help="the modlist's folder (the one holding ModOrganizer.ini)")
    s.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
    s.add_argument("--mod", help="also list this mod's plugins and what depends on them")
    s.add_argument("--plugin", help="also list this plugin's masters and what needs it")
    a = ap.parse_args(argv)
    return scan(a)


if __name__ == "__main__":
    sys.exit(main())
