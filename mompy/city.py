"""``mompy poke city NAME build``: finish the building or unit in production at the next End Turn.

The game completes an item when the stored production reaches its cost; buying fills the store to the cost (checked
live: Granary 0 -> 40, then 0 after it was built). So this writes a store that is certainly enough. It is one ``poke``
of ``production_stored``: a compare-and-swap, logged for ``undo``. mompy does not know the cost (that table is in the
game's files, which mompy does not read), hence an amount that is more than any building costs.
"""

from __future__ import annotations

import struct

from . import peek
from .api import DosboxApi
from .poke import PokeError, poke

ENOUGH = 2000                    # more than any building costs (the dearest are a few hundred); *guess*, see the story
FIRST_BUILDING, LAST_BUILDING = 3, 35
FIRST_UNIT, LAST_UNIT = 100, 0xFFFB     # units are 100 and up (cities seen building 158 to 228); 0xFFFC is "nothing"


def build(api: DosboxApi, number: int, dry_run: bool = False, force: bool = False) -> str:
    """Fill city ``number``'s production store so its item completes next turn."""
    found = peek.find_game(api)
    record = peek.read_record(api, found, "city", number)       # refuses an empty slot
    name = record[:14].split(b"\0", 1)[0].decode("latin-1")
    item = struct.unpack("<H", record[0x1C:0x1E])[0]
    if item in (1, 2):
        raise PokeError(f"{name} is making {'Trade Goods' if item == 1 else 'Housing'}, not a building: change its production in the game first")
    known = FIRST_BUILDING <= item <= LAST_BUILDING or FIRST_UNIT <= item <= LAST_UNIT
    if not known and not force:
        raise PokeError(f"{name}'s item {item} is neither a building (3 to 35) nor a unit (100 and up). --force to fill its store anyway")
    stored = struct.unpack("<H", record[0x5E:0x60])[0]
    if stored >= ENOUGH:
        return f"{name} already has {stored} stored, nothing written"
    return poke(api, number, "production_stored", str(ENOUGH), dry_run=dry_run, force=True, block_name="city") + f"  (item {item}: it completes at End Turn)"
