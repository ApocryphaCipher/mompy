"""Magic nodes and the places monsters live: towers, node guardians, caves, dungeons, temples, keeps, ruins and lairs.

Both are tables in the game's memory (``nodes``: 30 records of 48 bytes; ``encounters``: 102 records of 24 bytes), laid out in Mirror's
kazzmir-save-layouts.md and checked in the real game. A node's defenders are not in the node's record: they are an encounter of kind 1
to 3 at the same tile. A guard is a unit type and a count byte of two nibbles (low: guards left, high: the starting count).
"""

from __future__ import annotations

import struct
from typing import Dict, List, Optional, Tuple

from . import layout, locate
from .api import DosboxApi

KINDS = {0: "Tower of Wizardry", 1: "Chaos node guardians", 2: "Nature node guardians", 3: "Sorcery node guardians", 4: "Cave",
         5: "Dungeon", 6: "Ancient temple", 7: "Abandoned keep", 8: "Monster lair", 9: "Ruins", 10: "Fallen temple"}
NODE_TYPES = {0: "Sorcery", 1: "Nature", 2: "Chaos"}
PLANES = ("Arcanus", "Myrror")
Guard = Tuple[int, int, int]                   # (unit type, left, started)


def read_lairs(api: DosboxApi, game: locate.Game) -> List[Dict]:
    """Every non-empty encounter record: index, tile, intact, kind, guards, rewards."""
    table = layout.ENCOUNTERS
    raw = api.read(game.base + table.offset, table.stride * table.count)
    lairs = []
    for i in range(table.count):
        r = raw[i * 24:(i + 1) * 24]
        if r == bytes(24) or r[0] >= 60 or r[1] >= 40 or r[2] > 1:
            continue
        guards = [(t, c & 15, c >> 4) for t, c in ((r[5], r[6]), (r[7], r[8])) if t]
        gold, mana = struct.unpack_from("<hh", r, 10)
        lairs.append({"index": i, "x": r[0], "y": r[1], "plane": r[2], "intact": r[3], "kind": r[4], "guards": guards,
                      "gold": gold, "mana": mana})
    return lairs


def read_nodes(api: DosboxApi, game: locate.Game) -> List[Dict]:
    table = layout.NODES
    raw = api.read(game.base + table.offset, table.stride * table.count)
    nodes = []
    for i in range(table.count):
        r = raw[i * 48:(i + 1) * 48]
        if r[0] >= 60 or r[1] >= 40 or r[2] > 1:
            continue
        nodes.append({"index": i, "x": r[0], "y": r[1], "plane": r[2], "owner": struct.unpack("<b", r[3:4])[0], "power": r[4],
                      "type": r[45]})
    return nodes


def guards_text(guards: List[Guard], type_names: List[str]) -> str:
    """``Sprites 3 of 3, Ghouls 0 of 6`` (left of started), or ``none``."""
    parts = [f"{type_names[t] if t < len(type_names) else t} {left} of {start}" for t, left, start in guards]
    return ", ".join(parts) if parts else "none"


def guardians_of(nodes_record: Dict, lairs: List[Dict]) -> Optional[Dict]:
    """The encounter that defends a node: kind 1 to 3 at its tile."""
    for lair in lairs:
        if lair["kind"] in (1, 2, 3) and (lair["x"], lair["y"], lair["plane"]) == (nodes_record["x"], nodes_record["y"], nodes_record["plane"]):
            return lair
    return None
