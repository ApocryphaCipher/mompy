"""``mompy poke wizard N cast unit.NAME``: put a unit of any type straight into the game, owned by a wizard.

A unit is one 32-byte record in the units table plus the live count beside it. The record layout and the type table were
read from the running game (docs/stories/STORY-016-spike-summon-a-unit.md): the type table sits in the game's data segment, and
each type's record holds a pointer to its *name*, so the names come from the running game, not from anything mompy ships.
Max moves and sight range come from the type's record. A War Bears written this way showed at once, walked, and survived End Turn.

The unit goes to the wizard's summoning circle unless ``--at`` says otherwise. No mana, no spell book, no checks the game would
make when casting. A tile holds at most nine units of one owner, so a full or foreign tile pushes the unit to a free neighbour.
It is a set of compare-and-swap writes, logged as one entry for ``mompy undo``.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import layout, locate, peek
from .peek import PeekError
from .api import DosboxApi, ApiError
from .poke import PokeError, _log, _write
from .where import PLANES, find_city, read_cities, _circle

DGROUP_BELOW_WIZARDS = 0x9ECA     # the data segment starts this far below the wizard table (0x289F0 vs 0x328BA)
TYPE_TABLE, TYPE_STRIDE, TYPE_COUNT = 0x19C, 36, 198
LAST_HERO, FIRST_FANTASTIC = 34, 154
MOVES_AT, SIGHT_AT = 9, 19        # inside a type record
STACK_LIMIT = 9
DEAD = 0xFF
DRAW_PRIORITY = 0x0A              # *guess*: what a Guardian Spirit carries; the game works it out again when the unit moves


@dataclass(frozen=True)
class UnitType:
    number: int
    name: str
    moves: int
    sight: int

    @property
    def fantastic(self) -> bool:
        return self.number >= FIRST_FANTASTIC


def read_types(api: DosboxApi, game: locate.Game) -> List[UnitType]:
    """All 198 unit types, with names read from the game; refused if the table does not look like one."""
    dgroup = game.base - DGROUP_BELOW_WIZARDS
    segment = api.read(dgroup, 0x10000)
    types = []
    for number in range(TYPE_COUNT):
        rec = segment[TYPE_TABLE + number * TYPE_STRIDE:TYPE_TABLE + (number + 1) * TYPE_STRIDE]
        pointer = struct.unpack("<H", rec[:2])[0]
        name = segment[pointer:pointer + 24].split(b"\0", 1)[0]
        if len(name) < 3 or not all(32 <= c < 127 for c in name):
            raise PokeError(f"the unit type table does not look right in this game (type {number}): not writing")
        types.append(UnitType(number, name.decode("latin-1"), rec[MOVES_AT], rec[SIGHT_AT]))
    return types


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower().replace("'", "")).strip()


def find_type(types: List[UnitType], text: str) -> UnitType:
    """A unit type by number, whole name or unique prefix; the same name in several races is listed, never guessed."""
    text = text.strip()
    if text.isdigit():
        if int(text) >= TYPE_COUNT:
            raise PokeError(f"there is no unit type {text} (0 to {TYPE_COUNT - 1})")
        return types[int(text)]
    key = _key(text)
    if not key:
        raise PokeError("which unit? e.g. unit.war_bears, or a type number: unit.179")
    exact = [t for t in types if _key(t.name) == key]
    found = exact or [t for t in types if _key(t.name).startswith(key)]
    if not found:
        raise PokeError(f"no unit is called {text!r}")
    if len({_key(t.name) for t in found}) > 1:
        raise PokeError(f"{text!r} could be " + ", ".join(sorted({t.name for t in found})) + ": give more of the name")
    if len(found) > 1:
        numbers = ", ".join(str(t.number) for t in found)
        raise PokeError(f"{found[0].name} exists for several races (types {numbers}): name the type, e.g. unit.{found[0].number}")
    return found[0]


def parse_place(api: DosboxApi, game: locate.Game, at: str) -> Tuple[int, int, int]:
    """(x, y, plane) from ``x,y,plane`` (plane 0/1 or arcanus/myrror), or a city's name or number."""
    parts = [p.strip() for p in at.split(",")]
    if len(parts) == 3:
        try:
            plane = {"arcanus": 0, "myrror": 1}.get(parts[2].lower()) if not parts[2].isdigit() else int(parts[2])
            x, y = int(parts[0]), int(parts[1])
        except ValueError:
            plane = None
        if plane is None or not (0 <= x < 60 and 0 <= y < 40 and plane in (0, 1)):
            raise PokeError(f"{at!r} is not a place: x 0 to 59, y 0 to 39, plane 0/arcanus or 1/myrror")
        return x, y, plane
    try:
        number = find_city(api, at)
    except PeekError as err:
        raise PokeError(str(err)) from None
    for city in read_cities(api, game):
        if city.slot + 1 == number:
            return city.x, city.y, city.plane
    raise PokeError(f"there is no city {at!r}")


def _tile_name(x: int, y: int, plane: int, cities) -> str:
    here = next((c.name for c in cities if (c.x, c.y, c.plane) == (x, y, plane)), None)
    return f"{here} ({PLANES[plane]} {x}, {y})" if here else f"{PLANES[plane]} ({x}, {y})"


def _free_tile(origin, count, owner, units, cities):
    """The first of the tile and its eight neighbours that holds ``count`` more units of ``owner`` and nothing foreign."""
    x0, y0, plane = origin
    for dx, dy in [(0, 0)] + [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]:
        x, y = (x0 + dx) % 60, y0 + dy
        if not 0 <= y < 40:
            continue
        here = [u for u in units if (u[0], u[1], u[2]) == (x, y, plane)]
        if any(u[3] != owner for u in here) or len(here) + count > STACK_LIMIT:
            continue
        if any((c.x, c.y, c.plane) == (x, y, plane) and c.owner != owner for c in cities):
            continue
        return x, y, plane
    return None


def make_record(unit: UnitType, owner: int, x: int, y: int, plane: int) -> bytes:
    rec = bytearray(32)
    rec[0:6] = bytes([x, y, plane, owner, unit.moves, unit.number])
    rec[6] = 0xFF                           # hero slot: none
    rec[7] = 1
    rec[8] = unit.moves                     # moves left: a full turn
    rec[11] = 1
    rec[12] = 0 if unit.fantastic else 1    # level; *guess* for ordinary units: level 1 is a recruit
    rec[18] = DRAW_PRIORITY
    rec[22] = unit.sight
    rec[28] = 0xFF
    return bytes(rec)


def summon(api: DosboxApi, number: int, text: str, count: int = 1, at: Optional[str] = None, dry_run: bool = False) -> str:
    """Put ``count`` units named ``text`` under wizard ``number``, at ``at`` or at his summoning circle."""
    found = peek.find_game(api)
    if not 1 <= number <= 5:
        raise PokeError(f"there is no wizard {number} (1 to 5)")
    if not 1 <= count <= STACK_LIMIT:
        raise PokeError(f"a tile holds at most {STACK_LIMIT} units: count 1 to {STACK_LIMIT}")
    types = read_types(api, found)
    unit = find_type(types, text)
    if unit.number <= LAST_HERO:
        raise PokeError(f"{unit.name} is a hero: a hero also needs a place in the wizard's hero list, which mompy cannot write yet")
    names = list(found.names)
    who = f"wizard {number} ({names[number - 1]})"
    owner = number - 1
    cities = read_cities(api, found)
    if at is not None:
        origin = parse_place(api, found, at)
    else:
        origin = _circle(api, found, owner)
        if origin is None:
            raise PokeError(f"{who} has no summoning circle position that makes sense: say where with --at")

    table = layout.UNITS
    count_at = found.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    count_raw = api.read(count_at, 2)
    live = struct.unpack("<H", count_raw)[0]
    if live > table.count:
        raise PokeError("the unit count does not look right in this game: not writing")
    start = found.base + table.offset
    raw = api.read(start, table.stride * live)
    records = [raw[i * 32:(i + 1) * 32] for i in range(live)]
    alive = [r for r in records if r[3] != DEAD and r[2] != DEAD]
    place = _free_tile(origin, count, owner, alive, cities)
    if place is None:
        raise PokeError(f"no room for {count} at {_tile_name(*origin, cities)} or beside it (nine to a tile, one owner to a tile)")
    dead = [i for i, r in enumerate(records) if r[3] == DEAD and r[2] == DEAD]
    slots = dead[:count] + list(range(live, live + max(0, count - len(dead))))
    if slots[-1] >= table.count:
        raise PokeError("the units table is full")
    new_live = max(live, slots[-1] + 1)
    plural = f"{count} " if count > 1 else ""
    moved = "" if place == origin else f" (the tile at {_tile_name(*origin, cities)} had no room)"
    summary = f"{plural}{unit.name} for {who} at {_tile_name(*place, cities)}{moved}, unit slot{'s' if count > 1 else ''} " \
              + ", ".join(str(s) for s in slots)
    if dry_run:
        return f"(dry run) would put {summary}"

    record = make_record(unit, owner, *place)
    writes, label = [], f"wizard {number} cast unit.{unit.name}"
    try:
        for slot in slots:
            address = start + slot * table.stride
            old = records[slot] if slot < live else api.read(address, table.stride)
            _write(api, address, record, old, f"unit slot {slot}")
            writes.append({"address": address, "old": old.hex(), "new": record.hex()})
        if new_live != live:
            _write(api, count_at, struct.pack("<H", new_live), count_raw, "the unit count")
            writes.append({"address": count_at, "old": count_raw.hex(), "new": struct.pack("<H", new_live).hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(writes):          # both or neither: take back what was written
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; a written unit record could NOT be put back: check the units with peek")
        raise PokeError(str(err)) from None
    _log(api.url, label, f"{live} units", f"{new_live} units", writes)
    return summary
