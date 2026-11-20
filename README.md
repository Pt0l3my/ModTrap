# ModTrap

A local tool for Mod Organizer 2 and Skyrim that takes a mod out of a modlist the way Soul Trap takes a soul from a
body: it removes the mod as a master from every plugin that depends on it, so that the mod can be disabled without
"missing master" errors.

**Status: design, and the first piece of version 0.1.** The reader exists: it reads an MO2 instance and works out
which plugins depend on which. Nothing that changes a file exists yet.

```
python -m modtrap scan "C:\Modlists\Example" --mod "Some Mod"
```

prints the mods, the load order's health and what depends on a mod. It needs Python 3.10 or newer and writes
nothing. See:

- [docs/design/0001-design.md](docs/design/0001-design.md): what ModTrap is to do and how;
- [docs/DECISIONS.md](docs/DECISIONS.md): the owner's decisions, and the questions still open;
- [docs/research/](docs/research/README.md): what MO2's and xEdit's own sources say, each fact with its source;
- [docs/REASONING.md](docs/REASONING.md): why the design is the way it is, and what was ruled out.

ModTrap runs on your own PC, serves a page to your browser on 127.0.0.1 only, and calls your own installed MO2 and
xEdit. It contains neither of them, and no mod files. MIT licence.
