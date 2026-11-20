"""Shared paths, file helpers and the citation codes the ModTrap documents use.

Taken from the workplan tool of the owner's EldenNet (MIT; NOTICE), itself adapted from the one in the owner's
Skyrizz: only the section index, with ModTrap's own documents and codes.
"""
import json
import os
import pathlib
import re

WP = pathlib.Path(__file__).resolve().parent.parent          # tools/workplan
ROOT = WP.parent.parent                                        # the repository
DATA = WP / "data"                                             # generated, not committed
CHUNK_TOKENS = 6000                                            # sections larger than this are cut into pieces


def load(path, default=None):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save(path, obj, indent=1):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")       # atomic, so a parallel reader never sees half a file
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def tokens(text_or_bytes):
    """A rough token count: four bytes a token, the usual rule for English text."""
    n = len(text_or_bytes.encode("utf-8")) if isinstance(text_or_bytes, str) else int(text_or_bytes)
    return max(1, n // 4)


# --- citation codes ---------------------------------------------------------------------------------------------
#
# Canonical forms:  MO01, MO01§3.2   MO2 research note 01 (docs/research/mo2/01-*.md)
#                   XE01, XE01§4     xEdit research note 01 (docs/research/xedit/01-*.md)
#                   TL01, TL01§3     tools research note 01 (docs/research/tools/01-*.md)
#                   DESIGN§6.3       the design (docs/design/0001-design.md)
#                   WHY§12           an entry of the reasoning log (docs/REASONING.md)
#                   MT4              one of the owner's decisions (docs/DECISIONS.md)

NOTE = re.compile(r"(?<![\w#/-])(MO|XE|TL)(0\d)(?![\w-])(?:\s?§\s?(\d+(?:\.\d+)*[a-z]?))?")
DOC_SECTION = re.compile(r"(?<![\w:-])(DESIGN|WHY)\s?§\s?(\d+(?:\.\d+)*)")
# The owner's decisions, MT1 onwards (docs/DECISIONS.md), cited as codes of their own: `wp refs MT4`.
DECISION = re.compile(r"(?<![\w:#-])(MT\d{1,3})(?![\w-])")


def aliases_for(path):
    """Which prefixes mean which note series. ModTrap's notes cite each other in the full form only."""
    return {"MO": "MO", "XE": "XE", "TL": "TL"}


def cited_codes(text, path=""):
    """Every code a text cites, in order of first appearance, without repeats. A note cited with a section
    yields both the section (XE01§5) and the note (XE01), so `refs XE01` finds every citation of the note."""
    alias = aliases_for(path)
    found = []
    for m in NOTE.finditer(text):
        series = alias.get(m.group(1))
        if not series:
            continue
        note = series + m.group(2)
        found.append((m.start(), note))
        if m.group(3):
            found.append((m.start(), note + "§" + m.group(3).rstrip(".")))
    for m in DOC_SECTION.finditer(text):
        found.append((m.start(), m.group(1) + "§" + m.group(2).rstrip(".")))
    for m in DECISION.finditer(text):
        found.append((m.start(), m.group(1)))
    seen, out = set(), []
    for _, c in sorted(found):
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out
