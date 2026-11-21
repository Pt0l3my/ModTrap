"""ModTrap's command line.

`python -m modtrap` starts ModTrap: a page in your browser, served on this PC only (127.0.0.1).
`python -m modtrap scan FOLDER [--profile NAME] [--mod NAME] [--plugin NAME]` prints what ModTrap sees in an MO2
instance. `python -m modtrap add FOLDER --mod NAME` prints what it takes to add a mod MO2 has installed. All three
only read the instance: its text files, each plugin's header, and file names in mod folders."""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser

from . import NAME, VERSION, instance, logbook, model, paths


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
        for g in gs:
            if g.reading == "output":
                what = "made by a tool: " + ", ".join(g.made_by)
            elif g.reading == "whole mod":
                what = "every plugin of this mod depends on it"
            elif g.reading == "most of the mod":
                what = "most of this mod depends on it; the rest (%s) is needed by nothing else" % ", ".join(g.leftover)
            else:
                what = "%d other plugin(s) of this mod do not depend on it" % g.others
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


def add(a: argparse.Namespace) -> int:
    """What it takes to add mods that MO2 has installed (MT21, DESIGN§16). Reads only."""
    from . import adding

    try:
        inst = instance.load(a.folder, a.profile)
    except instance.Unusable as e:
        print("%s cannot read this folder: %s" % (NAME, e))
        return 2
    m = model.build(inst)
    rep = adding.analyse(m, a.mod)
    print("%s %s (read-only: adding mods)" % (NAME, VERSION))
    for n in rep["unknown"]:
        print("No mod named '%s' in this profile." % n)
    if not rep["mods"]:
        return 1
    s = rep["slots"]
    print("Room in the load order: full plugins %d -> %d of %d, light plugins %d -> %d of %d" % (
        s["full"]["now"], s["full"]["after"], s["full"]["limit"],
        s["light"]["now"], s["light"]["after"], s["light"]["limit"]))
    place = rep["place"]
    print("Place for a mod still to enable: %s" % (("directly before '%s'" % place["before"]) if place["before"]
                                                  else "last in MO2's list"))
    for o in place["outputs"][:12]:
        print("  stays after it: %s (%s)" % (o["mod"], o["why"]))
    for x in rep["mods"]:
        print("\n%s: %s, %d file(s)%s" % (x["name"], "enabled at priority %d" % x["priority"] if x["enabled"] else
                                         "disabled", x["files"], ", listing cut short" if x["cut"] else ""))
        print("  carries: %s" % (", ".join("%d %s" % (n, k) for k, n in sorted(x["kinds"].items())) or "nothing"))
        for p in x["plugins"]:
            if p["unreadable"]:
                print("  plugin %s could not be read: %s" % (p["name"], p["unreadable"]))
                continue
            pr = p["proposed"]
            print("  plugin %s [%s]: %s" % (p["name"], p["kind"], ("active at position %s" % p["position"])
                                            if p["active"] else "to go %s (%s)" % (
                ("directly before " + pr["before"]) if pr["before"] else "at the end", pr["why"])))
            for mm in p["masters"]:
                if mm["state"] != "active":
                    print("    master %s: %s" % (mm["name"], mm["state"]))
            for n in p["notes"]:
                print("    note: " + n)
        for word, lst in (("would replace files of", x["wins"]), ("would lose files to", x["loses"])):
            for c in lst[:15]:
                print("  %s '%s': %d (%s)%s" % (word, c["mod"], c["files"],
                                               ", ".join("%d %s" % (n, k) for k, n in sorted(c["kinds"].items())),
                                               "  [a tool's output]" if c["output"] else ""))
            if len(lst) > 15:
                print("  ... and %d more mod(s)" % (len(lst) - 15))
    if rep["cut"]:
        print("\nThe search for shared files was cut short: there may be more.")
    print("\nSteps:")
    for st in rep["steps"]:
        print("  %d. [%s] %s  (%s)" % (st["n"], st["state"], st["title"], "you" if st["who"] == "you" else NAME))
        for it in st["items"][:12]:
            print("       - " + it["text"])
        if len(st["items"]) > 12:
            print("       ... and %d more" % (len(st["items"]) - 12))
    return 0


DEFAULT_PORT = 8737


def serve(a: argparse.Namespace) -> int:
    from . import api as api_mod, server          # imported here so that `scan` needs neither

    api = api_mod.Api()
    app = server.App(api)
    try:
        httpd = server.Server(a.port, app)
    except OSError:
        if a.port == 0:
            raise
        try:
            httpd = server.Server(0, app)         # the usual port is taken: any free one
        except OSError as e:
            print("%s could not open a port on this PC: %s" % (NAME, logbook.why(e)))
            return 2
    url = "http://127.0.0.1:%d/" % httpd.port
    log = logbook.get("app")
    log.info("%s %s, Python %s on %s", NAME, VERSION, sys.version.split()[0], sys.platform)
    log.info("the page is at %s (this PC only)", url)
    # Quit (MT20): the answer is sent first, then the server stops and this program ends.
    api.on_quit = lambda: threading.Thread(target=httpd.shutdown, name="quit", daemon=True).start()
    if a.allow_changes:
        from . import changes                     # never imported otherwise: nothing can then change a modlist
        api.changes = changes.Changes(api)
        log.warn("started with --allow-changes: ModTrap may now put mods into this modlist when you press "
                 "“Add it for me”. Every change goes through the safe folder and can be reverted.")
    if a.folder:
        api.open(a.folder, a.profile or None)
    elif not api.restore():                       # the session ModTrap was closed in comes back
        folder = paths.load_settings().get("folder")
        if isinstance(folder, str) and folder:
            api.open(folder, paths.load_settings().get("profile") or None)
    if not a.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print("%s is running. Leave this window open; press Ctrl+C here to stop it." % NAME, file=sys.stderr)
    try:
        httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        api.save_log()
        httpd.server_close()
    print("%s has closed. Your session is saved; start %s again to carry on where you were." % (NAME, NAME),
          file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modtrap", description="ModTrap: demaster mods in an MO2 modlist")
    sub = ap.add_subparsers(dest="cmd")
    v = sub.add_parser("serve", help="start ModTrap and open its page (the default)")
    for p in (ap, v):
        p.add_argument("--port", type=int, default=DEFAULT_PORT, help="the port on 127.0.0.1 (default %(default)s)")
        p.add_argument("--no-browser", action="store_true", help="do not open the browser")
        p.add_argument("--folder", help="open this modlist folder at start")
        p.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
        p.add_argument("--allow-changes", action="store_true",
                       help="let ModTrap change the modlist when asked to (adding a mod, Revert); off by default")
    s = sub.add_parser("scan", help="read an instance and print a summary; writes nothing")
    s.add_argument("folder", help="the modlist's folder (the one holding ModOrganizer.ini)")
    s.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
    s.add_argument("--mod", help="also list this mod's plugins and what depends on them")
    s.add_argument("--plugin", help="also list this plugin's masters and what needs it")
    d = sub.add_parser("add", help="what it takes to add mods MO2 has installed; writes nothing")
    d.add_argument("folder", help="the modlist's folder (the one holding ModOrganizer.ini)")
    d.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
    d.add_argument("--mod", action="append", required=True, help="a mod to add, by its name in MO2 (repeat for more)")
    a = ap.parse_args(argv)
    return scan(a) if a.cmd == "scan" else add(a) if a.cmd == "add" else serve(a)


if __name__ == "__main__":
    sys.exit(main())
