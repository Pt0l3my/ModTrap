# wp: read ModTrap's documents by section, not whole

`wp` cuts every document into sections by heading and keeps a small index of each section's code, size and
citations, so you can read exactly the part you need. It is taken from the owner's EldenNet (MIT; see `NOTICE`),
which adapted it from the workplan tool in the owner's Skyrizz. Only the index is kept, with ModTrap's own
documents and codes.

The index lives in `tools/workplan/data/index.json`. That file is generated and gitignored, and it rebuilds
itself whenever an indexed file changes, so there is nothing to remember.

## Codes

| Code | Means |
|---|---|
| `DESIGN§6.3` | The design (`docs/design/0001-design.md`), one of its sections |
| `WHY`, `WHY§4` | The reasoning log (`docs/REASONING.md`), or one of its entries |
| `MT5` | One of the owner's decisions (`docs/DECISIONS.md`; `wp show DEC§mt5` prints it) |
| `MO01`, `MO01§3` | MO2 research note 01 (`docs/research/mo2/01-*.md`), or one of its sections |
| `XE01`, `XE01§7` | xEdit research note 01 (`docs/research/xedit/01-*.md`), or one of its sections |
| `RES`, `README`, `CLAUDE`, `WP` | The research index, the root README, CLAUDE.md and this file |

A numbered heading gets its number (`XE01§5`). Any other heading gets a slug of its title (`DEC§mt5`, `WHY§index`).

## Commands

```
python3 -I tools/workplan/wp.py show XE01 --list         # a document's sections, sizes only
python3 -I tools/workplan/wp.py show DESIGN§6.3          # one section
python3 -I tools/workplan/wp.py show DESIGN§6 --all      # a section and everything under it
python3 -I tools/workplan/wp.py refs MT5                 # every section that cites a code
python3 -I tools/workplan/wp.py find in:docs/research text:'plugins file'   # sections matching all terms
python3 -I tools/workplan/wp.py grep 'autoexit' in:docs  # matching sentences, with lines
python3 -I tools/workplan/wp.py stat                     # the largest files and sections
```

`show` accepts `--max-tokens N` to stop before printing more than N tokens.

## The rule

Never open a whole design or research document to find something. Look it up by code, or with `find` or `grep`,
check the size, and read only that section.
