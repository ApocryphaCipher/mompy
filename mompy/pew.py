"""``mompy pew PLACE``: kill the units on a tile. The city, the node and the terrain stay.

PLACE is ``pointer`` (the tile under the mouse), a city's name, or ``x,y,plane``. A dead unit is marked in place the way the game
marks it: plane and owner both 0xFF, the live count unchanged, the record swept at End Turn (Mirror's live-ram-map.md, 2026-09-23,
the node guardians dying in a real fight). Until that sweep ``undo`` brings the stack back.

The game also keeps its own picture of each stack, built earlier, and marking the records dead does not update it: the map keeps
drawing a ghost (the unit's picture without a banner, and still clickable) until the map view is nudged (scrolled a little),
the plane is flipped and flipped back, or End Turn comes (Kevin, 2026-10-13).

Heroes are spared: a hero is also an entry in his wizard's hero list, and killing only the unit record could leave that entry
dangling. Say so, never silently.
"""

from __future__ import annotations

import struct
from typing import List

from . import layout, peek
from .api import ApiError, DosboxApi
from .poke import PokeError, _log, _write
from .summon import DEAD, LAST_HERO, _tile_name, parse_place, read_types
from .where import read_cities


def pew(api: DosboxApi, at: str, dry_run: bool = False) -> str:
    found = peek.find_game(api)
    x, y, plane = parse_place(api, found, at)
    types = read_types(api, found)
    cities = read_cities(api, found)
    names = list(found.names)
    table = layout.UNITS
    count_at = found.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    live = struct.unpack("<H", api.read(count_at, 2))[0]
    if live > table.count:
        raise PokeError("the unit count does not look right in this game: not writing")
    start = found.base + table.offset
    raw = api.read(start, table.stride * live)
    here = [i for i in range(live) if tuple(raw[i * 32:i * 32 + 3]) == (x, y, plane) and raw[i * 32 + 3] != DEAD]
    place = _tile_name(x, y, plane, cities)
    if not here:
        raise PokeError(f"there are no units at {place}")
    heroes = [i for i in here if raw[i * 32 + 5] <= LAST_HERO]
    victims = [i for i in here if i not in heroes]
    spared = f"; {len(heroes)} hero{'es' if len(heroes) != 1 else ''} spared" if heroes else ""
    if not victims:
        raise PokeError(f"only heroes at {place}: not killed (their hero list entry would be left behind)")

    def what(i: int) -> str:
        owner = raw[i * 32 + 3]
        return f"{types[raw[i * 32 + 5]].name} ({names[owner] if owner < len(names) else 'neutral'})"

    listing = ", ".join(what(i) for i in victims)
    if dry_run:
        return f"(dry run) would kill {len(victims)} at {place}: {listing}{spared}"
    writes: List[dict] = []
    try:
        for i in victims:
            address = start + i * 32 + 2
            old = raw[i * 32 + 2:i * 32 + 4]
            _write(api, address, bytes([DEAD, DEAD]), old, f"unit {i}")
            writes.append({"address": address, "old": old.hex(), "new": bytes([DEAD, DEAD]).hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(writes):          # all or none
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; some units could NOT be brought back: check them in the game")
        raise PokeError(str(err)) from None
    _log(api.url, f"pew {place}", f"{len(victims)} units", "dead", writes)
    return (f"pew! {len(victims)} killed at {place}: {listing}{spared}.\n"
            "The map keeps drawing them (a ghost) until you nudge the map view, flip the plane, or end the turn; do not order a ghost around. "
            "undo brings them back until End Turn sweeps them.")
