# Research index

What MO2's and xEdit's own sources say, kept apart from the design so that a fact and its source can be checked.
Every statement carries a label: **FACT** (read in the named source at the named commit), **LIKELY** (inferred, not
yet proven), **SPECULATION**, **METHOD** (how something is or will be found out). The reasoning that follows from
these notes is in [REASONING.md](../REASONING.md) (`WHY§n`).

Sources are read only, never built or run, each cloned in its own folder outside this repository.

| Code | Note | Source |
|---|---|---|
| MO01 | [MO2: the instance and the command line](mo2/01-instance-and-command-line.md) | `github.com/ModOrganizer2/modorganizer`, `master` at `4ba22f0` (2026-10-05); GPL-3.0 by its `LICENSE` |
| XE01 | [xEdit: the command line and scripting](xedit/01-command-line-and-scripting.md) | `github.com/TES5Edit/TES5Edit`, tag `xedit-4.1.5f` at `f5c00f3` (2024-04-27); MPL-2.0 by its `LICENSE.txt` |

Not yet researched: MO2's file formats for `modlist.txt` and `plugins.txt` in its source (MO01§2 holds them as
LIKELY), the virtual file system's handling of a changed file (MO01§5), and xEdit versions newer than 4.1.5f.
