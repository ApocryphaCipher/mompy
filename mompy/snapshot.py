"""``mompy snapshot NAME`` and ``mompy diff A B``: see exactly which bytes of the game moved between two moments.

A snapshot keeps the tables mompy knows (wizards, cities, units and their count, nodes, lairs, fortresses) and the game's data segment
(where the pointer, the map view and many counters live), and the two map layers (terrain and its flags), as one JSON file under ``$MOMPY_HOME/snapshots``. A diff names a changed field
when the field table knows it (``wizard 1 (Jafar) gold: 100 -> 200``) and shows raw offsets otherwise.

The game changes a few hundred bytes on its own between two reads (timers and the like). Take a second snapshot of the *same* moment
and pass it as ``--ignore``: every byte that differs between the two is left out of the diff. This is the throwaway script that found
the diplomacy and global-enchantment fields (2026-10-12), the pointer and the plane (2026-10-13), made permanent.
"""

from __future__ import annotations

import base64
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import fields as F
from . import layout
from . import peek
from .api import DosboxApi
from .game import home

DGROUP_SIZE = 0x10000
VERSION = 1
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

# The unit record, by ReMoM's s_UNIT (offsets and sizes), so a diff can say what moved.
UNIT_FIELDS: List[Tuple[int, int, str]] = [
    (0, 1, "x"), (1, 1, "y"), (2, 1, "plane"), (3, 1, "owner"), (4, 1, "max_moves"), (5, 1, "type"), (6, 1, "hero_slot"),
    (7, 1, "finished"), (8, 1, "moves_left"), (9, 1, "dest_x"), (10, 1, "dest_y"), (11, 1, "status"), (12, 1, "level"),
    (14, 2, "experience"), (16, 1, "move_failed"), (17, 1, "damage"), (18, 1, "draw_priority"), (20, 2, "in_tower"),
    (22, 1, "sight"), (23, 1, "mutations"), (24, 4, "enchantments"), (28, 1, "road_left"), (29, 1, "road_from_x"), (30, 1, "road_from_y"),
]
# the tables: region name -> (layout table, field-table block or None)
TABLES = {"wizards": (layout.WIZARDS, "wizard"), "cities": (layout.CITIES, "city"), "units": (layout.UNITS, None),
          "nodes": (layout.NODES, None), "lairs": (layout.ENCOUNTERS, None), "fortresses": (layout.FORTRESSES, "fortress")}


# The map layers, as offsets from the wizard table (0x72630 and 0x773A0 in the research setup): the terrain type (u16 a tile) and the
# per-tile flags (a byte: 0x20 is corrupted), two planes of 60 x 40 each. Their addresses move with the DOSBox build like the tables.
MAP_LAYERS = {"terrain": (0x72630, 2), "terrain_flags": (0x773A0, 1)}
PLANE_TILES = 60 * 40


class SnapshotError(Exception):
    pass


def _dir() -> Path:
    return home() / "snapshots"


def _path(name: str) -> Path:
    if not _NAME.match(name):
        raise SnapshotError(f"{name!r} is not a snapshot name: letters, digits, '.', '_' and '-', starting with a letter or digit")
    return _dir() / f"{name}.json"


def take(api: DosboxApi, name: str, replace: bool = False) -> str:
    path = _path(name)
    if path.exists() and not replace:
        raise SnapshotError(f"a snapshot called {name!r} already exists; pick another name or --replace")
    game = peek.find_game(api)
    regions: Dict[str, dict] = {}
    for region, (table, _) in TABLES.items():
        regions[region] = _grab(api, game.base + table.offset, table.stride * table.count)
    count_at = game.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE)
    regions["unit_count"] = _grab(api, count_at, 2)
    for layer, (reference, width) in MAP_LAYERS.items():
        regions[layer] = _grab(api, reference + (game.base - layout.REFERENCE_WIZARD_BASE), 2 * PLANE_TILES * width)
    regions["dgroup"] = _grab(api, game.base - layout.DGROUP_BELOW_WIZARDS, DGROUP_SIZE)
    doc = {"version": VERSION, "name": name, "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "url": api.url,
           "base": game.base, "wizards": list(game.names), "regions": regions}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    kib = sum(len(base64.b64decode(r["data"])) for r in regions.values()) // 1024
    return f"snapshot {name}: {len(regions)} regions, {kib} KiB, saved to {path}"


def _grab(api: DosboxApi, address: int, length: int) -> dict:
    return {"address": address, "data": base64.b64encode(api.read(address, length)).decode("ascii")}


def list_snapshots() -> str:
    paths = sorted(_dir().glob("*.json")) if _dir().exists() else []
    rows = []
    for p in paths:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            rows.append(f"{doc.get('name', p.stem)}  {doc.get('time', '')}")
        except (OSError, ValueError):
            rows.append(f"{p.stem}  (unreadable)")
    return "\n".join(rows) if rows else "no snapshots yet: mompy snapshot NAME"


def load(name: str) -> dict:
    path = _path(name)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        regions = {k: base64.b64decode(v["data"], validate=True) for k, v in doc["regions"].items()}
        addresses = {k: int(v["address"]) for k, v in doc["regions"].items()}
    except OSError:
        raise SnapshotError(f"no snapshot called {name!r} (mompy snapshot --list)") from None
    except (ValueError, KeyError, TypeError):
        raise SnapshotError(f"the snapshot {name!r} is damaged: take it again") from None
    return {"name": name, "wizards": doc.get("wizards", []), "regions": regions, "addresses": addresses}


def _runs(changed: List[bool]) -> List[Tuple[int, int]]:
    """(start, end) of each stretch of changed bytes."""
    runs, start = [], None
    for i, flag in enumerate(changed + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    return runs


def _hex(b: bytes) -> str:
    return b.hex(" ")


def diff(a_name: str, b_name: str, ignore_name: Optional[str] = None, show_all: bool = False, limit: int = 200) -> str:
    a, b = load(a_name), load(b_name)
    noise = load(ignore_name)["regions"] if ignore_name else {}
    names = b["wizards"] or a["wizards"]
    lines: List[str] = []
    for region in list(TABLES) + ["unit_count", *MAP_LAYERS, "dgroup"]:
        ra, rb = a["regions"].get(region), b["regions"].get(region)
        if ra is None or rb is None or len(ra) != len(rb):
            continue
        rn = noise.get(region)
        changed = [x != y and (rn is None or len(rn) != len(ra) or x == rn[i]) for i, (x, y) in enumerate(zip(ra, rb))]
        if region == "dgroup":                          # the window also holds tables that are reported by name above: not twice
            start = b["addresses"]["dgroup"]
            for other, address in b["addresses"].items():
                if other != "dgroup" and other in b["regions"]:
                    for i in range(max(address - start, 0), min(address - start + len(b["regions"][other]), len(changed))):
                        changed[i] = False
        if not any(changed):
            continue
        if region == "unit_count":
            lines.append(f"unit count: {struct.unpack('<H', ra)[0]} -> {struct.unpack('<H', rb)[0]}")
        elif region in MAP_LAYERS:
            lines += _map_lines(region, ra, rb, changed)
        elif region == "dgroup":
            lines += [f"data segment +0x{s:04x}: {_hex(ra[s:e])} -> {_hex(rb[s:e])}" for s, e in _runs(changed)]
        else:
            lines += _table_lines(region, ra, rb, changed, names)
    if not lines:
        return "no differences" + (" (after ignoring the noise)" if ignore_name else "")
    total = len(lines)
    if not show_all and total > limit:
        lines = lines[:limit] + [f"... {total - limit} more lines (--all shows them)"]
    return "\n".join(lines)


def _map_lines(layer: str, ra: bytes, rb: bytes, changed: List[bool]) -> List[str]:
    """One line per changed tile: ``terrain Myrror (12, 7): 0x00a1 -> 0x0140``."""
    width = MAP_LAYERS[layer][1]
    out = []
    for tile in sorted({i // width for i, c in enumerate(changed) if c}):
        plane, rest = divmod(tile, PLANE_TILES)
        before = int.from_bytes(ra[tile * width:(tile + 1) * width], "little")
        after = int.from_bytes(rb[tile * width:(tile + 1) * width], "little")
        out.append(f"{layer} {'Myrror' if plane else 'Arcanus'} ({rest % 60}, {rest // 60}): 0x{before:0{width * 2}x} -> 0x{after:0{width * 2}x}")
    return out


def _table_lines(region: str, ra: bytes, rb: bytes, changed: List[bool], names: List[str]) -> List[str]:
    table, block = TABLES[region]
    stride = table.stride
    out: List[str] = []
    for index in sorted({s // stride for s, _ in _runs(changed)} | {(e - 1) // stride for _, e in _runs(changed)}):
        lo, hi = index * stride, (index + 1) * stride
        rec_a, rec_b, flags = ra[lo:hi], rb[lo:hi], changed[lo:hi]
        title = _title(region, index, rec_b, names)
        covered = [False] * stride
        for offset, size, name, extra in _named(region, block):
            if not any(flags[offset:offset + size]):
                continue
            for i in range(offset, offset + size):
                covered[i] = True
            out += _field_lines(title, name, extra, rec_a[offset:offset + size], rec_b[offset:offset + size], offset, names)
        rest = [flags[i] and not covered[i] for i in range(stride)]
        out += [f"{title} +0x{s:02x}: {_hex(rec_a[s:e])} -> {_hex(rec_b[s:e])}" for s, e in _runs(rest)]
    return out


def _title(region: str, index: int, record: bytes, names: List[str]) -> str:
    if region == "wizards":
        return f"wizard {index + 1}" + (f" ({names[index]})" if index < len(names) else "")
    if region == "cities":
        return f"city {index + 1} ({record[:14].split(bytes(1), 1)[0].decode('latin-1')})"
    if region == "units":
        return f"unit {index} (type {record[5]})"
    if region == "fortresses":
        return f"fortress {index + 1}" + (f" ({names[index]})" if index < len(names) else "")
    return f"{region[:-1] if region.endswith('s') else region} {index}"


def _named(region: str, block: Optional[str]):
    """(offset, size, name, field-or-None) for the parts of a record that have a name."""
    if region == "units":
        return [(o, s, n, None) for o, s, n in UNIT_FIELDS]
    if block is None:
        return []
    return [(f.offset, f.size, f.name, f) for f in F.all_fields(block)]


def _field_lines(title: str, name: str, field: Optional[F.Field], old: bytes, new: bytes, offset: int, names: List[str]) -> List[str]:
    if field is None:                                   # a unit field: unsigned number, little-endian
        return [f"{title} {name}: {int.from_bytes(old, 'little')} -> {int.from_bytes(new, 'little')}"]
    try:
        before, after = field.decode(old), field.decode(new)
    except (ValueError, struct.error):
        return [f"{title} +0x{offset:02x}: {_hex(old)} -> {_hex(new)}"]
    if not field.is_array:
        return [f"{title} {name}: {before} -> {after}"]
    return [f"{title} {name}.{field.label_for(i, names)}: {x} -> {y}" for i, (x, y) in enumerate(zip(before, after)) if x != y]
