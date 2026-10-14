"""``mompy poke city NAME cast mass.flight`` and ``mompy unit cast mass.flight --at pointer``: a unit enchantment on a whole stack.

A unit's enchantments are a u32 at ``+24`` of its record (ReMoM's ``UE_FLAGS_L`` is the low word, ``UE_FLAGS_H`` the high word; Mirror's
unit-movement.md records Flight as 0x20000, Wind Walking 0x10000, Water Walking 0x100, Invisibility 0x8000 from kazzmir's remake,
which agree). There is no caster in the record: the unit's owner pays the upkeep at End Turn. ``cast`` sets the bit on every unit on
a tile, with no mana and no checks; ``dispel`` clears it. One compare-and-swap per unit, one ``undo`` for the stack.
"""

from __future__ import annotations

import re
import struct
from typing import List, Optional

from . import layout, peek
from .api import ApiError, DosboxApi
from .poke import PokeError, _log, _write
from .summon import DEAD, _tile_name, parse_place
from .where import read_cities

ENCHANTMENTS_AT = 24

# bit -> name, low word first then high word (ReMoM MOM_DAT.h, UE_FLAGS_L and UE_FLAGS_H)
_LOW = ["Immolation", "Guardian Wind", "Berserk", "Cloak of Fear", "Black Channels", "Wraith Form", "Regeneration", "Path Finding",
        "Water Walking", "Resist Elements", "Elemental Armor", "Stone Skin", "Iron Skin", "Endurance", "Spell Lock", "Invisibility"]
_HIGH = ["Wind Walking", "Flight", "Resist Magic", "Magic Immunity", "Flame Blade", "Eldritch Weapon", "True Sight", "Holy Weapon",
         "Heroism", "Bless", "Lionheart", "Giant Strength", "Planar Travel", "Holy Armor", "Righteousness", "Invulnerability"]
ENCHANTMENTS = {name: 1 << i for i, name in enumerate(_LOW)} | {name: 1 << (16 + i) for i, name in enumerate(_HIGH)}


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower().replace("'", "")).strip()


def find_enchantment(text: str) -> str:
    """The enchantment's name from what was typed (``mass.`` prefix, case, ``_`` and a unique prefix allowed)."""
    key = _key(text.strip().lower().removeprefix("mass."))
    if not key:
        raise PokeError("which enchantment? e.g. mass.flight")
    exact = [n for n in ENCHANTMENTS if _key(n) == key]
    found = exact or [n for n in ENCHANTMENTS if _key(n).startswith(key)]
    if not found:
        raise PokeError(f"no unit enchantment is called {text!r}. Known: " + ", ".join(ENCHANTMENTS))
    if len(found) > 1:
        raise PokeError(f"{text!r} could be " + ", ".join(found) + ": give more of the name")
    return found[0]


def change(api: DosboxApi, place: str, text: str, on: bool, dry_run: bool = False) -> str:
    """Put (or take) the enchantment on every unit on ``place`` (a city, ``x,y,plane`` or ``pointer``)."""
    name = find_enchantment(text)
    bit = ENCHANTMENTS[name]
    found = peek.find_game(api)
    x, y, plane = parse_place(api, found, place)
    where = _tile_name(x, y, plane, read_cities(api, found))
    table = layout.UNITS
    count_at = found.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    live = struct.unpack("<H", api.read(count_at, 2))[0]
    if live > table.count:
        raise PokeError("the unit count does not look right in this game: not writing")
    start = found.base + table.offset
    raw = api.read(start, table.stride * live)
    here = [i for i in range(live) if tuple(raw[i * 32:i * 32 + 3]) == (x, y, plane) and raw[i * 32 + 3] != DEAD]
    if not here:
        raise PokeError(f"there are no units at {where}")
    todo, new_values = [], {}
    for i in here:
        old = struct.unpack_from("<I", raw, i * 32 + ENCHANTMENTS_AT)[0]
        new = old | bit if on else old & ~bit
        if new != old:
            todo.append(i)
            new_values[i] = new
    verb = "on" if on else "off"
    if not todo:
        return f"{name} is already {verb} for all {len(here)} units at {where}, nothing written"
    summary = f"{name} {verb} for {len(todo)} of {len(here)} units at {where}"
    if dry_run:
        return f"(dry run) would put {summary}"
    writes: List[dict] = []
    try:
        for i in todo:
            address = start + i * 32 + ENCHANTMENTS_AT
            old = raw[i * 32 + ENCHANTMENTS_AT:i * 32 + ENCHANTMENTS_AT + 4]
            new = struct.pack("<I", new_values[i])
            _write(api, address, new, old, f"unit {i}'s enchantments")
            writes.append({"address": address, "old": old.hex(), "new": new.hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(writes):          # all or none
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; some units could NOT be put back: check them in the game")
        raise PokeError(str(err)) from None
    _log(api.url, f"mass {name}", "off" if on else "on", verb, writes)
    return summary + (". The owner pays its upkeep at End Turn; " if on else ". ") + "the map may need a nudge to redraw"
