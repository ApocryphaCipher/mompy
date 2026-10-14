"""``mompy unit mercury``: give units all the movement they can hold, for this turn.

A unit's *moves left* is one byte of its record (``+8``), counted in half-moves, and signed: 127 is the top, 63.5 moves
(Kevin's real-game check, 2026-10-13: a Cavalry set to 127 showed 63.5 and crossed most of a continent in one turn; 255 would
read as -1). Max moves (``+4``) is left alone: the game fills moves left up from it at the start of each turn, so this is a
boost for one turn. Each write is a compare-and-swap, and one ``undo`` puts every unit's moves back.
"""

from __future__ import annotations

import struct
from typing import List, Optional

from . import layout, peek
from .api import ApiError, DosboxApi
from .poke import PokeError, _log, _write
from .summon import DEAD, parse_place

MERCURY = 127           # half-moves: the largest a signed byte holds
MOVES_LEFT = 8


def mercury(api: DosboxApi, at: Optional[str] = None, wizard: Optional[int] = None, dry_run: bool = False) -> str:
    """Top up the moves of the units on a tile (``at``: a city or x,y,plane) or of every unit of ``wizard``."""
    if (at is None) == (wizard is None):
        raise PokeError("say which units: --at CITY (or x,y,plane) for a stack, or --wizard N for all of a wizard's units")
    found = peek.find_game(api)
    names = list(found.names)
    if wizard is not None and not 1 <= wizard <= 5:
        raise PokeError(f"there is no wizard {wizard} (1 to 5)")
    table = layout.UNITS
    count_at = found.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    live = struct.unpack("<H", api.read(count_at, 2))[0]
    if live > table.count:
        raise PokeError("the unit count does not look right in this game: not writing")
    start = found.base + table.offset
    raw = api.read(start, table.stride * live)
    if at is not None:
        x, y, plane = parse_place(api, found, at)
        chosen = [i for i in range(live) if tuple(raw[i * 32:i * 32 + 3]) == (x, y, plane) and raw[i * 32 + 3] != DEAD]
        who = f"the units at ({x}, {y})"
    else:
        chosen = [i for i in range(live) if raw[i * 32 + 3] == wizard - 1 and raw[i * 32 + 2] != DEAD]
        who = f"wizard {wizard} ({names[wizard - 1]})'s units"
    if not chosen:
        raise PokeError(f"there are no units for {who}")
    todo = [i for i in chosen if raw[i * 32 + MOVES_LEFT] != MERCURY]
    if not todo:
        return f"{who}: all {len(chosen)} already have {MERCURY / 2:g} moves, nothing written"
    summary = f"{len(todo)} of {len(chosen)} units set to {MERCURY / 2:g} moves ({who})"
    if dry_run:
        return f"(dry run) would set {summary}"

    writes: List[dict] = []
    try:
        for i in todo:
            address = start + i * 32 + MOVES_LEFT
            old = bytes([raw[i * 32 + MOVES_LEFT]])
            _write(api, address, bytes([MERCURY]), old, f"unit {i}'s moves")
            writes.append({"address": address, "old": old.hex(), "new": bytes([MERCURY]).hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(writes):          # all or none
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; some units' moves could NOT be put back: check them in the game")
        raise PokeError(str(err)) from None
    _log(api.url, "unit mercury", f"{len(todo)} units", f"{MERCURY / 2:g} moves", writes)
    return summary
