"""``mompy unit heal | weapons GRADE | experience max --at PLACE``: change every unit on a tile at once.

Each is one compare-and-swap per unit, one ``undo`` for the stack, and a line that says how many were changed and why the others were not.

* ``heal``: the unit's damage (``+17``) to 0, for every unit including heroes and summoned creatures.
* ``weapons``: the weapon grade, the low two bits of ``mutations`` (``+23``), for **ordinary units only**: summoned creatures carry no
  grade, and heroes are left alone (what their weapons show depends on their items). The mutation flags (undead...) are kept.
* ``experience max``: experience and level together, to the top the game allows each kind. An ordinary unit of a wizard with the **Warlord**
  retort is one level higher still, Ultra Elite (level 4 at 120 experience): Kevin's old units show exactly that, and the game adds it
  again at End Turn, so this writes it at once. The numbers are read from the game itself
  (its experience table, nine values at the data segment ``+0x1D74``: 0, 20, 60, 120, 200, 300, 450, 600, 1000). ReMoM's own code caps an
  ordinary unit at the Elite entry (120, level 3) and a hero at the last (1000, level 8, Demi-God); summoned creatures do not level.

``--skip-heroes`` leaves the heroes out of any of them.
"""

from __future__ import annotations

import struct
from typing import Callable, Dict, List, Optional, Tuple

from . import layout, peek
from .api import ApiError, DosboxApi
from .poke import PokeError, _log, _write
from .summon import DEAD, FIRST_FANTASTIC, LAST_HERO, _tile_name, parse_place
from .where import read_cities

DAMAGE, MUTATIONS, LEVEL, EXPERIENCE = 17, 23, 12, 14
GRADES = ("normal", "magic", "mithril", "adamantium")
EXPERIENCE_TABLE_IN_DGROUP, LEVELS = 0x1D74, 9
ELITE, DEMI_GOD = 3, 8

Change = Tuple[int, bytes, bytes]                      # (offset in the record, old bytes, new bytes)


def _is_hero(record: bytes) -> bool:
    return record[5] <= LAST_HERO


def _is_creature(record: bytes) -> bool:
    return record[5] >= FIRST_FANTASTIC


def experience_table(api: DosboxApi, game) -> List[int]:
    """The game's nine experience thresholds; refused if they do not look like the table."""
    raw = api.read(game.base - layout.DGROUP_BELOW_WIZARDS + EXPERIENCE_TABLE_IN_DGROUP, 2 * LEVELS)
    table = list(struct.unpack(f"<{LEVELS}h", raw))
    if table[0] != 0 or any(b <= a for a, b in zip(table, table[1:])) or table[-1] > 30000:
        raise PokeError("the experience table does not look right in this game: not writing")
    return table


def warlords(api: DosboxApi, game) -> set:
    """The wizards (0 to 4) whose retorts include Warlord: their ordinary units are a level above what experience gives."""
    from . import fields as F
    retorts = F.find("wizard", "retorts")
    spot = retorts.element("warlord")
    table = layout.WIZARDS
    raw = api.read(game.base + table.offset, table.stride * table.count)
    return {w for w in range(table.count) if raw[w * table.stride + retorts.offset + spot] != 0}


def _apply(api: DosboxApi, place: str, what: str, now: str, label: str, plan: Callable[[bytes], Tuple[Optional[Change], Optional[str]]],
           skip_heroes: bool, dry_run: bool) -> str:
    """Run ``plan`` on every live unit at ``place``; it returns (change or None, reason to skip or None)."""
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
    todo: List[Tuple[int, Change]] = []
    skipped: Dict[str, int] = {}
    unchanged = 0
    for i in here:
        record = raw[i * 32:(i + 1) * 32]
        if skip_heroes and _is_hero(record):
            skipped["heroes skipped"] = skipped.get("heroes skipped", 0) + 1
            continue
        change, reason = plan(record)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
        elif change is None or change[1] == change[2]:
            unchanged += 1
        else:
            todo.append((i, change))
    notes = [f"{why}: {n}" for why, n in skipped.items()] + ([f"already so: {unchanged}"] if unchanged else [])
    tail = f" ({', '.join(notes)})" if notes else ""
    counts = f"{len(todo)} of {len(here)} units at {where}{tail}"
    summary = f"{what} {counts}"
    if not todo:
        return f"nothing to do: {summary}"
    if dry_run:
        return f"(dry run) would {now} {counts}"
    writes: List[dict] = []
    try:
        for i, (offset, old, new) in todo:
            address = start + i * 32 + offset
            _write(api, address, new, old, f"unit {i}")
            writes.append({"address": address, "old": old.hex(), "new": new.hex()})
    except (PokeError, ApiError) as err:
        for w in reversed(writes):          # all or none
            try:
                api.write(w["address"], bytes.fromhex(w["old"]), expect=bytes.fromhex(w["new"]))
            except ApiError:
                err = PokeError(f"{err}; some units could NOT be put back: check them in the game")
        raise PokeError(str(err)) from None
    _log(api.url, f"unit {label} at {where}", "before", "after", writes)
    return summary


def heal(api: DosboxApi, place: str, skip_heroes: bool = False, dry_run: bool = False) -> str:
    def plan(r: bytes):
        return (DAMAGE, r[DAMAGE:DAMAGE + 1], b"\x00"), None
    return _apply(api, place, "healed", "heal", "heal", plan, skip_heroes, dry_run)


def weapons(api: DosboxApi, place: str, grade: str, skip_heroes: bool = False, dry_run: bool = False) -> str:
    word = (grade or "").strip().lower()
    if word.isdigit() and int(word) < 4:
        word = GRADES[int(word)]
    if word not in GRADES:
        raise PokeError(f"weapons are {', '.join(GRADES)} (or 0 to 3)")
    value = GRADES.index(word)

    def plan(r: bytes):
        if _is_creature(r):
            return None, "summoned creatures carry no weapons"
        if _is_hero(r):
            return None, "heroes left alone"
        old = r[MUTATIONS]
        return (MUTATIONS, bytes([old]), bytes([(old & ~3) | value])), None
    return _apply(api, place, f"gave {word} weapons to", f"give {word} weapons to", "weapons", plan, False, dry_run)


def experience(api: DosboxApi, place: str, how: str, skip_heroes: bool = False, dry_run: bool = False) -> str:
    if (how or "").strip().lower() not in ("max", "maximum"):
        raise PokeError("experience takes 'max': mompy unit experience max --at PLACE")
    game = peek.find_game(api)
    table = experience_table(api, game)
    bonus = warlords(api, game)

    def plan(r: bytes):
        if _is_creature(r):
            return None, "summoned creatures do not level"
        level = DEMI_GOD if _is_hero(r) else ELITE
        shown = level + (1 if not _is_hero(r) and r[3] in bonus else 0)           # Warlord: Ultra Elite
        old = r[LEVEL:LEVEL + 4]
        have_level, have_xp = old[0], struct.unpack("<h", old[2:4])[0]
        # never lower anything: a unit already above the table's top for its kind (a level a retort gave it) is left as it is
        new = bytes([max(shown, have_level), old[1]]) + struct.pack("<h", max(table[level], have_xp))
        return (LEVEL, bytes(old), new), None
    return _apply(api, place, "set maximum experience on", "set maximum experience on", "experience", plan, skip_heroes, dry_run)
