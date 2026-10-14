"""The tile under the game's mouse pointer, read from the game's own memory (no DOSBox help needed).

The game keeps the pointer's position on its 320 x 200 screen, the world tile at the top-left of the map view, and the plane
being viewed, all in its data segment (``layout.POINTER_IN_DGROUP`` and friends). The visible map is 12 x 10 tiles of 20 x 18
pixels starting at screen row 20, and the world wraps at 60 columns. Checked in the real game on 2026-10-13: the pointer on
Hellgate's tile gave (50, 18) from memory alone, and the game's own city list has Hellgate there.
"""

from __future__ import annotations

import struct
from typing import Tuple

from . import layout, locate
from .api import DosboxApi
from .poke import PokeError

TILE_W, TILE_H, MAP_TOP = 20, 18, 20
VIEW_COLUMNS, VIEW_ROWS = 12, 10


def tile_under_pointer(api: DosboxApi, game: locate.Game) -> Tuple[int, int, int]:
    """(x, y, plane) of the map tile under the pointer, or a PokeError that says why there is none."""
    dgroup = game.base - layout.DGROUP_BELOW_WIZARDS
    px, py = struct.unpack("<2H", api.read(dgroup + layout.POINTER_IN_DGROUP, 4))
    ox, oy = struct.unpack("<2H", api.read(dgroup + layout.VIEW_ORIGIN_IN_DGROUP, 4))
    plane = struct.unpack("<H", api.read(dgroup + layout.VIEW_PLANE_IN_DGROUP, 2))[0]
    column, row = px // TILE_W, (py - MAP_TOP) // TILE_H
    if py < MAP_TOP or column >= VIEW_COLUMNS or row >= VIEW_ROWS:
        raise PokeError(f"the pointer is not over the map (it is at screen pixel {px}, {py}): hold it over a tile")
    x, y = (ox + column) % 60, oy + row
    if not (0 <= y < 40 and plane in (0, 1) and ox < 60):
        raise PokeError("the map view does not look right in this game (is the overland map showing?): not using the pointer")
    return x, y, plane
