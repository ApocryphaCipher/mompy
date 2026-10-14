"""Find the game's tables in DOSBox's memory, and say whether they look right.

DOSBox's API does not say where a program was loaded, and the address moves with the DOSBox build
(STORY-008). So the wizard table is *found*: five names, printable, one wizard record apart. The other
tables sit at fixed offsets from it (``layout``), and each is checked for plausible records before
anything is written.
"""

from __future__ import annotations

import re
import struct
from typing import List, NamedTuple, Optional

from . import layout

_NAME = re.compile(rb"[A-Za-z' ]{3,19}\x00")


class Candidate(NamedTuple):
    base: int            # address of the first wizard record
    names: List[str]


class Game(NamedTuple):
    base: int                        # where the wizard table is
    names: List[str]
    checks: List["TableCheck"]
    alternatives: List[int]          # other places that also looked like the wizard table


class GameNotFound(Exception):
    """No usable game in memory; the message says why, in words for the player."""


class TableCheck(NamedTuple):
    name: str
    address: int
    ok: bool
    detail: str


def _name_at(memory: bytes, record_start: int) -> Optional[str]:
    """The wizard name in the record at ``record_start``, if it is a plausible one.

    One to 19 printable characters, NUL-padded to the end of the field. (The scan *finds* a table through a name of three or
    more letters, but a wizard called "Al" must not stop the other four from counting.)"""
    at = record_start + layout.WIZARD_NAME_AT
    field = memory[at:at + layout.WIZARD_NAME_LEN]
    if len(field) < layout.WIZARD_NAME_LEN:
        return None
    name = field.split(b"\0", 1)[0]
    if not 1 <= len(name) <= 19 or not all(32 <= c < 127 for c in name):      # the game allows a name of one letter
        return None
    if any(field[len(name):]):          # a name is NUL-padded to the end of its field
        return None
    return name.decode("ascii")


def find_wizard_tables(memory: bytes) -> List[Candidate]:
    """Every place with five named wizard records one record apart (usually exactly one).

    A game that is not loaded yet has no names there; a game with fewer than five wizards
    (a small world) would not be found, and ``doctor`` says so.
    """
    found: List[Candidate] = []
    seen = set()
    for m in _NAME.finditer(memory):
        # the name found may be any of the five wizards' (the first may be "Al"): try each place it could sit
        hit = m.start() - layout.WIZARD_NAME_AT
        for slot in range(layout.WIZARD_COUNT):
            base = hit - slot * layout.WIZARD_STRIDE
            if base < 0 or base in seen:
                continue
            names = [_name_at(memory, base + i * layout.WIZARD_STRIDE) for i in range(layout.WIZARD_COUNT)]
            if all(names):
                seen.add(base)
                found.append(Candidate(base, names))
    return found


def _valid_city(rec: bytes) -> bool:
    name = rec[:14].split(b"\0", 1)[0]
    race, x, y, plane, owner = rec[14], rec[15], rec[16], rec[17], rec[18]
    return (len(name) >= 2 and all(32 <= c < 127 for c in name)
            and x < 60 and y < 40 and plane in (0, 1) and owner <= 5)


def _valid_unit(rec: bytes) -> bool:
    x, y, plane, owner = rec[0], rec[1], rec[2], rec[3]
    if plane == 0xFF and owner == 0xFF:
        return True                 # a unit that died this turn: the game leaves the record until End Turn sweeps it
    kind = rec[5]
    return x < 60 and y < 40 and plane in (0, 1) and owner <= 5 and kind < 198


def _valid_node(rec: bytes) -> bool:
    x, y, plane = rec[0], rec[1], rec[2]
    owner = struct.unpack("<b", rec[3:4])[0]
    return x < 60 and y < 40 and plane in (0, 1) and -1 <= owner <= 4


def _records(memory: bytes, address: int, table: layout.Table) -> List[bytes]:
    return [memory[address + i * table.stride: address + (i + 1) * table.stride]
            for i in range(table.count)]


def check_tables(memory: bytes, wizard_base: int) -> List[TableCheck]:
    """Check each table, at its fixed distance from the wizard table, for plausible records."""
    shift = wizard_base - layout.REFERENCE_WIZARD_BASE
    results: List[TableCheck] = []

    names = [_name_at(memory, wizard_base + i * layout.WIZARD_STRIDE) for i in range(layout.WIZARD_COUNT)]
    results.append(TableCheck("wizards", wizard_base, all(names), ", ".join(n or "?" for n in names)))

    def at(table: layout.Table) -> int:
        return table.reference + shift

    addr = at(layout.CITIES)
    if addr < 0 or addr + layout.CITIES.stride * layout.CITIES.count > len(memory):
        results.append(TableCheck("cities", addr, False, "outside memory"))
    else:
        good = sum(_valid_city(r) for r in _records(memory, addr, layout.CITIES))
        results.append(TableCheck("cities", addr, good >= 1, f"{good} plausible of {layout.CITIES.count} slots"))

    addr = at(layout.UNITS)
    count_at = layout.UNIT_COUNT_REFERENCE + shift
    if addr < 0 or addr + layout.UNITS.stride * layout.UNITS.count > len(memory) or count_at + 2 > len(memory):
        results.append(TableCheck("units", addr, False, "outside memory"))
    else:
        live = struct.unpack("<H", memory[count_at:count_at + 2])[0]
        recs = _records(memory, addr, layout.UNITS)[:min(live, layout.UNITS.count)]
        good = sum(_valid_unit(r) for r in recs)
        ok = live <= layout.UNITS.count and good == len(recs) and (live == 0 or good >= 1)
        results.append(TableCheck("units", addr, ok, f"{live} live, {good} plausible"))

    addr = at(layout.NODES)
    if addr < 0 or addr + layout.NODES.stride * layout.NODES.count > len(memory):
        results.append(TableCheck("nodes", addr, False, "outside memory"))
    else:
        good = sum(_valid_node(r) for r in _records(memory, addr, layout.NODES))
        results.append(TableCheck("nodes", addr, good >= 1, f"{good} plausible of {layout.NODES.count} slots"))

    return results


def find_game(memory: bytes) -> Game:
    """The game's wizard table, if memory holds one whose surrounding tables look right.

    Raises ``GameNotFound`` otherwise. When several places qualify the first is used and the others are
    reported in ``alternatives``.
    """
    candidates = find_wizard_tables(memory)
    if not candidates:
        raise GameNotFound("no wizard table found: load a saved game first (and the game needs all five wizards)")
    verified = [(c, check_tables(memory, c.base)) for c in candidates]
    good = [(c, t) for c, t in verified if all(x.ok for x in t)]
    if not good:
        c, t = verified[0]
        raise GameNotFound(f"wizard names found at {c.base:#x}, but the tables around them do not look right: "
                           + "; ".join(f"{x.name}: {x.detail}" for x in t if not x.ok))
    chosen, checks = good[0]
    return Game(chosen.base, chosen.names, checks, [c.base for c, _ in good[1:]])
