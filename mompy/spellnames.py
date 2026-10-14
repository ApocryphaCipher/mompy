"""Spell names, read from the running game: nothing from a game file is needed or shipped.

The game keeps the spell table of ``SPELLDAT.LBX`` in memory: 215 records of 36 bytes, the record index being the spell number
(0 is "None"), the name first (18 bytes, NUL-padded) and the realm at ``+23``. In the research setup the table starts at
0x906B0, 0x5DDF6 above the wizard table; checked on 2026-10-14 against the file: all 215 names match. It is a heap block, so
the offset is tried first and, if the table is not there, the whole memory is searched for it. No table means numbers, as before.
"""

from __future__ import annotations

import re
from typing import List, Optional

from . import layout
from .api import MEMORY_SIZE, ApiError, DosboxApi

RECORD, COUNT, REALM_AT = 36, 215, 23
EXPECTED_FROM_WIZARDS = 0x906B0 - layout.REFERENCE_WIZARD_BASE


def parse(raw: bytes) -> Optional[List[str]]:
    """The 215 names from the table's bytes, or None if they do not look like the spell table."""
    if len(raw) < RECORD * COUNT or raw[:5] != b"None\0":
        return None
    names = []
    for i in range(COUNT):
        rec = raw[i * RECORD:(i + 1) * RECORD]
        name = rec[:18].split(b"\0", 1)[0]
        if len(name) < 3 or not all(32 <= c < 127 for c in name) or (i > 0 and rec[REALM_AT] > 5):      # record 0, "None", has no realm
            return None
        names.append(name.decode("latin-1"))
    return names


def read(api: DosboxApi, wizard_base: int, hint=None):
    """(names, where): the spell names, and the table's address to remember (an int, or False when this game has no table).

    ``hint`` is what was remembered last time: an address to try first, or False to not search again for a table that was not there.
    Order: the remembered address, the place the table should be, then a search of all memory (the only slow step, done once).
    """
    if hint is False:
        return None, False
    tried = []
    try:
        for at in ([hint] if isinstance(hint, int) else []) + [wizard_base + EXPECTED_FROM_WIZARDS]:
            if at in tried:
                continue
            tried.append(at)
            names = parse(api.read(at, RECORD * COUNT)) if at >= 0 else None
            if names is not None:
                return names, at
        memory = api.read(0, MEMORY_SIZE)
    except ApiError:
        return None, None
    for hit in re.finditer(b"Earth to Mud\0", memory):          # spell 1, right after "None"
        start = hit.start() - RECORD
        if start >= 0:
            names = parse(memory[start:start + RECORD * COUNT])
            if names is not None:
                return names, start
    return None, False


def find(spells: List[str], text: str) -> int:
    """A spell number from a name (case, ``_`` and apostrophes ignored, a unique prefix allowed); a ValueError says why not."""
    key = _key(text)
    if not key:
        raise ValueError("which spell?")
    names = [_key(n) for n in spells]
    exact = [i for i, n in enumerate(names) if n == key and i > 0]
    found = exact or [i for i, n in enumerate(names) if n.startswith(key) and i > 0]
    if not found:
        raise ValueError(f"no spell is called {text!r}")
    if len(found) > 1:
        raise ValueError(f"{text!r} could be " + ", ".join(spells[i] for i in found[:6]) + (", ..." if len(found) > 6 else ""))
    return found[0]


def _key(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").replace("-", " ").replace("'", "").split())
