"""``mompy banish wizard N --dead``: finish a wizard the way the game leaves a defeated one.

The shape comes from a wizard the game itself eliminated (the Freya in ``JAFAR-PLAYED.GAM``, 2026-10-13): her fortress flag is
cleared, she owns no cities, no units and no heroes (every hero entry empty), and her gold, mana and power are 0, while her books,
retorts, spells and relations are untouched. This does the same to a living wizard, in one undoable change:

* the fortress flag cleared (banished);
* his cities go to the neutral player, with their enchantments cleared (they record the caster);
* the city enchantments he cast on anyone else's cities are cleared;
* his units die (the record marked dead the way ``pew`` does it), heroes included, and his hero list is emptied;
* his gold and mana are 0, and his global enchantments are off.

What the game does with such a wizard at End Turn is the point of the experiment (STORY-017); the player is refused without ``force``.
"""

from __future__ import annotations

import struct
from typing import List

from . import layout, peek
from .api import ApiError, DosboxApi
from .poke import PokeError, _log, _write
from .summon import DEAD
from .where import read_cities

NEUTRAL = 5
CITY_ENCHANTMENTS, CITY_ENCHANTMENT_COUNT = 67, 26          # city record +67 .. +92: 0 none, else the caster's wizard index + 1
HERO_LIST, HERO_ENTRY, HERO_ENTRIES = 0x76, 28, 6           # wizard record: unit index (i16, -1 none), name, items
EMPTY_HERO = b"\xff\xff" + bytes(HERO_ENTRY - 2)
GOLD, MANA, GLOBALS, GLOBAL_COUNT = 0x356, 0x25C, 0x482, 24


def eliminate(api: DosboxApi, number: int, force: bool = False, dry_run: bool = False) -> str:
    found = peek.find_game(api)
    if not 1 <= number <= 5:
        raise PokeError(f"there is no wizard {number} to eliminate (1 to 5; the neutral player has none)")
    names = list(found.names)
    who = f"wizard {number} ({names[number - 1]})"
    if number == 1 and not force:
        raise PokeError(f"{who} is you. Eliminating the player ends your own game; --force if you mean it")
    index = number - 1
    base = found.base
    wiz_at = base + layout.WIZARDS.offset + index * layout.WIZARDS.stride
    wiz = api.read(wiz_at, layout.WIZARDS.stride)

    plan: List[tuple] = []          # (address, old, new, what)

    def change(address: int, old: bytes, new: bytes, what: str) -> None:
        if old != new:
            plan.append((address, bytes(old), bytes(new), what))

    fort_at = base + layout.FORTRESSES.offset + index * layout.FORTRESSES.stride + 3
    change(fort_at, api.read(fort_at, 1), b"\x00", "fortress")

    city_at = base + layout.CITIES.offset
    city_raw = api.read(city_at, layout.CITIES.stride * layout.CITIES.count)
    own_cities = other_enchantments = 0
    for city in read_cities(api, found):
        rec = city_raw[city.slot * 114:(city.slot + 1) * 114]
        at = city_at + city.slot * 114
        enchantments = rec[CITY_ENCHANTMENTS:CITY_ENCHANTMENTS + CITY_ENCHANTMENT_COUNT]
        if city.owner == index:
            own_cities += 1
            change(at + 18, rec[18:19], bytes([NEUTRAL]), "city owner")
            change(at + CITY_ENCHANTMENTS, enchantments, bytes(CITY_ENCHANTMENT_COUNT), "city enchantments")
        elif index + 1 in enchantments:
            other_enchantments += 1
            cleaned = bytes(0 if b == index + 1 else b for b in enchantments)
            change(at + CITY_ENCHANTMENTS, enchantments, cleaned, "city enchantments")

    count_at = base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    live = struct.unpack("<H", api.read(count_at, 2))[0]
    if live > layout.UNITS.count:
        raise PokeError("the unit count does not look right in this game: not writing")
    unit_at = base + layout.UNITS.offset
    units = api.read(unit_at, 32 * live)
    killed = 0
    for i in range(live):
        rec = units[i * 32:(i + 1) * 32]
        if rec[3] == index and rec[2] != DEAD:
            killed += 1
            change(unit_at + i * 32 + 2, rec[2:4], bytes([DEAD, DEAD]), "unit")

    heroes = 0
    for h in range(HERO_ENTRIES):
        entry = wiz[HERO_LIST + h * HERO_ENTRY:HERO_LIST + (h + 1) * HERO_ENTRY]
        if struct.unpack("<h", entry[:2])[0] != -1:
            heroes += 1
        change(wiz_at + HERO_LIST + h * HERO_ENTRY, entry, EMPTY_HERO, "hero list")
    change(wiz_at + GOLD, wiz[GOLD:GOLD + 2], bytes(2), "gold")
    change(wiz_at + MANA, wiz[MANA:MANA + 2], bytes(2), "mana")
    change(wiz_at + GLOBALS, wiz[GLOBALS:GLOBALS + GLOBAL_COUNT], bytes(GLOBAL_COUNT), "global enchantments")

    summary = (f"{who}: {own_cities} cities to neutral, {killed} units killed, {heroes} heroes dropped"
               + (f", {other_enchantments} of his city enchantments on others' cities cleared" if other_enchantments else ""))
    if not plan:
        return f"{who} is already eliminated: nothing written"
    if dry_run:
        return f"(dry run) would eliminate {summary} ({len(plan)} writes)"
    done: List[dict] = []
    try:
        for address, old, new, what in plan:
            _write(api, address, new, old, what)
            done.append({"address": address, "old": old.hex(), "new": new.hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(done):            # all or none
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; part of it could NOT be put back: reload the game")
        raise PokeError(str(err)) from None
    _log(api.url, f"eliminate {who}", "alive", "eliminated", done)
    return f"{who} is eliminated: {summary[len(who) + 2:]}"
