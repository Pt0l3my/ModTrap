# ModTrap: notes for Claude

ModTrap is a local tool on the owner's PC for Mod Organizer 2 (MO2) and Skyrim. It "demasters" chosen mods in a
modlist: it removes them as masters from the plugins that depend on them, by running the owner's own xEdit inside the
MO2 instance with ModTrap's own script. Its decisions are in [docs/DECISIONS.md](docs/DECISIONS.md) (MT1 onwards), its
reasoning in [docs/REASONING.md](docs/REASONING.md), its research in [docs/research/](docs/research/README.md), its design
in [docs/design/](docs/design/).

## Reading the documents cheaply

- Never open a whole design or research document to find something. Use `wp` ([tools/workplan](tools/workplan/README.md)):
  `wp show CODE --list` for sizes, `wp show CODE` for one section, `wp refs CODE` for what cites it, `wp find` and
  `wp grep` to search. Codes: `DESIGN§6.3` (the design), `WHY§4` (the reasoning log), `MT5` (a decision), `MO01§3`
  and `XE01§7` (the research notes on MO2 and xEdit), `RES` (their index).
- Cite by code everywhere, so that `wp refs` finds every use.
- For code and other files: grep with line numbers first, then read only that range. Never re-read a file you have
  just edited.

## Privacy and safety: the sweep comes first

- Nothing is pushed or uploaded before the privacy and safety sweep passes. The sweep is the owner's `privsweep`, kept
  only in the owner's private Skyrizz repository under `tools/privsweep/`, never copied here or into any public
  repository, and installed as git's global pre-push gate. If `~/.config/privsweep` is missing, run
  `python3 -I tools/privsweep/privsweep.py install` in the Skyrizz checkout first. Sweep by hand what the gate does
  not cover: a message to another session (`privsweep.py text message`, the text on stdin) and a file sent to the
  owner (`privsweep.py files PATH`).
- Never bypass it: no `--no-verify`, no change to `core.hooksPath`, no HOME or GIT_CONFIG override.
- Nothing personal about the owner in any file, commit, page or upload: real name, account names, machine names,
  contact details, API keys, local paths, endpoint addresses or IPs. The owner's own local commands go in chat only.
  Examples and tests use placeholders, with paths on drive C:.
- Commit identities are noreply addresses only; use the environment's default git identity. No model identifiers of
  the assistant in files, apart from the commit trailer.
- No `Claude-Session` link in commit messages or pull requests (the owner's rule of 2026-11-16 for their other
  projects, MT12): it points to a private transcript and tells readers nothing. The `Co-Authored-By` trailer stays.

## Mods

- Never commit, upload or redistribute anyone's mod files, plugins or their contents, nor record names, FormIDs or
  text taken from a real mod. ModTrap's output stays on the owner's PC.
- Test fixtures are invented: tiny plugins written by ModTrap's own code, with invented names.
- ModTrap never changes a file in the game's folder or in a trapped mod's folder, and never deletes a mod or a
  plugin: a mod is only ever disabled (MT9). It changes no file before a copy of it is in the job's safe folder
  (MT14), writes only what a confirmed plan named (DESIGN§8), and records every change in its history (MT15).

## Licences

- ModTrap is MIT. Write our own code. Read a dependency's licence before adopting it and list it in `NOTICE`.
- MO2 is GPL-3.0 and xEdit is MPL-2.0: never copy their code or their scripts, never bundle them. ModTrap calls the
  owner's own installed copies. ModTrap's xEdit script is ours.
- Untrusted copies (clones, downloads, uploads) go in their own folder outside the repository, are read with
  `python3 -I` or grep, and are never built or run.

## Working rules

- Work on a topic branch (`design/`, `feat/`, `fix/`, `docs/`, `test/`, `chore/`), never directly on `main` unless
  the owner asks. Push only at meaningful milestones or when asked. Open a pull request only when asked.
- Ask the owner, with a recommendation, about anything the design leaves open, as an MT entry marked Open.
- At the start of a session, and after a switch of model, read the index of the reasoning log,
  [docs/REASONING.md](docs/REASONING.md) (`wp show WHY§n` opens an entry).
- Keep that log as you work: an entry of a few lines for each finding, conclusion, rejected path or workaround that
  DECISIONS.md does not hold, with its date, label (FACT, LIKELY, SPECULATION, METHOD, DECIDED), tags and
  references, added to the index in the same commit. Append only: never renumber or rewrite an entry; a later
  finding adds a dated Later line or a new entry.
- A fact read in MO2's or xEdit's source goes in a research note (`docs/research/`), with its label and its file
  and line at a named commit. A decision is recorded with its date and the owner's words, amended only by a dated
  note, and its id is never renumbered.
- Every change under `modtrap/` gets a version of its own (MT22): run `python3 tools/bump.py` before the commit
  (a test fails otherwise), and tell the owner the version with each change handed over.
- Text the owner reads uses British spelling.
