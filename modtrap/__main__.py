"""`python -m modtrap scan FOLDER [--profile NAME] [--mod NAME]`: read an MO2 instance and print what ModTrap
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
        deps = m.dependants_of_mod(mod)
        print("  %d plugin(s) of other mods depend on it:" % len(deps))
        for r in deps:
            print("    %-50s position %-5s in mod '%s' (priority %s)" % (r.name, r.position, r.source,
                                                                         r.source_priority))
    return 1 if m.issues else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modtrap", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="read an instance and print a summary; writes nothing")
    s.add_argument("folder", help="the modlist's folder (the one holding ModOrganizer.ini)")
    s.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
    s.add_argument("--mod", help="also list this mod's plugins and what depends on them")
    a = ap.parse_args(argv)
    return scan(a)


if __name__ == "__main__":
    sys.exit(main())
