"""ModTrap's command line.

`python -m modtrap` starts ModTrap: a page in your browser, served on this PC only (127.0.0.1).
`python -m modtrap scan FOLDER [--profile NAME] [--mod NAME] [--plugin NAME]` prints what ModTrap sees in an MO2
instance. Both only read the instance: its text files and each plugin's header."""

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
    s = sub.add_parser("scan", help="read an instance and print a summary; writes nothing")
    s.add_argument("folder", help="the modlist's folder (the one holding ModOrganizer.ini)")
    s.add_argument("--profile", help="the profile to read (default: the one MO2 last used)")
    s.add_argument("--mod", help="also list this mod's plugins and what depends on them")
    s.add_argument("--plugin", help="also list this plugin's masters and what needs it")
    a = ap.parse_args(argv)
    return scan(a) if a.cmd == "scan" else serve(a)


if __name__ == "__main__":
    sys.exit(main())
