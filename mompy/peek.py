"""``mompy peek``: read a record's fields from the running game, in words.

Read-only. The game is *found* the same way ``doctor`` finds it (the address moves with the DOSBox build),
and refused if its tables do not look right.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from . import fields as F
from . import layout, locate
from .api import DosboxApi
from .game import connect


class PeekError(Exception):
    pass


def find_game(api: DosboxApi) -> locate.Game:
    try:
        return connect(api)
    except locate.GameNotFound as err:
        raise PeekError(f"{err}\nRun 'mompy doctor' to see what is wrong.") from None


def read_record(api: DosboxApi, game: locate.Game, block: str, number: int) -> bytes:
    """The raw bytes of record ``number`` (human numbering: wizard 1 is the player)."""
    b = F.blocks()[block]
    last = b.first_number + b.count - 1
    if not b.first_number <= number <= last:
        raise PeekError(f"there is no {b.describe} {number} (1 to {last})")
    start = game.base + layout.table(b.table).offset + (number - b.first_number) * b.stride
    return api.read(start, b.stride)


def _slice(field: F.Field, record: bytes) -> bytes:
    return record[field.offset:field.offset + field.size]


def _enum(field: F.Field, value: int) -> str:
    text = field.enum.get(str(value))
    return f"{value} ({text})" if text else str(value)


def _plain(field: F.Field, value: int) -> str:
    """One number in words: its meaning if the field has an enum, else the number."""
    return field.enum.get(str(value), str(value)) if field.enum else str(value)


PLANES = ("Arcanus", "Myrror")


def _position(values: List[int], cities: Dict[Tuple[int, int, int], str]) -> str:
    x, y, plane = values
    where = f"x {x}, y {y}, plane {plane}"
    if plane in (0, 1):
        where += f" ({PLANES[plane]})"
    city = cities.get((x, y, plane))
    return where + (f", the city {city}" if city else "")


def _others(field: F.Field, values: List[int], own: Optional[int]) -> List[Tuple[int, int]]:
    """(index, value) for each element, leaving out the wizard's own slot in a per-wizard list:
    a wizard has no relation or treaty with himself."""
    return [(i, v) for i, v in enumerate(values) if not (field.labels == "wizards" and i == own)]


def render(field: F.Field, record: bytes, names: List[str], element: Optional[str] = None,
           own: Optional[int] = None, cities: Optional[Dict[Tuple[int, int, int], str]] = None) -> str:
    """One field (or one element of it) as ``name = ...``. ``own`` is the 0-based index of the record's
    own wizard, whose slot is left out of lists about other wizards."""
    value = field.decode(_slice(field, record))
    if field.format == "map_position" and element is None:
        return f"{field.name} = {_position(value, cities or {})}"                 # type: ignore[arg-type]
    if element is not None:
        i = field.element(element, names)
        label = field.label_for(i, names)
        return f"{field.name}.{label} = {_enum(field, value[i])}"          # type: ignore[index]
    if field.type == "text" or not field.is_array:
        return f"{field.name} = {value if field.type == 'text' else _enum(field, value)}"   # type: ignore[arg-type]
    values: List[int] = value                                                # type: ignore[assignment]
    if field.max == 1 and field.min == 0 and field.labels:                  # flags: list the ones that are set
        on = [field.label_for(i, names) for i, v in enumerate(values) if v]
        return f"{field.name} = {', '.join(on) if on else 'none'}"
    if field.count > 24 and field.enum:                                      # the 214 spells: a summary
        tally = {}
        for v in values:
            tally[v] = tally.get(v, 0) + 1
        parts = [f"{tally[v]} {field.enum.get(str(v), v)}" for v in sorted(tally, reverse=True)]
        return f"{field.name} = {', '.join(parts)}  (ask for one with {field.name}.N)"
    if field.labels:
        return f"{field.name} = " + ", ".join(f"{field.label_for(i, names)} {_plain(field, v)}"
                                              for i, v in _others(field, values, own))
    return f"{field.name} = " + ", ".join(_plain(field, v) for v in values)


def as_data(field: F.Field, record: bytes, names: List[str], own: Optional[int] = None) -> object:
    """One field as plain data for ``--json``: numbers raw, arrays keyed by label when there are labels
    (without the wizard's own slot in a per-wizard list)."""
    value = field.decode(_slice(field, record))
    if field.is_array and field.labels:
        return {field.label_for(i, names): v for i, v in _others(field, value, own)}   # type: ignore[arg-type]
    return value


def read_cities(api: DosboxApi, game: locate.Game) -> Dict[Tuple[int, int, int], str]:
    """(x, y, plane) -> name for each city in memory, to name a position."""
    table = layout.CITIES
    start = game.base + table.offset
    raw = api.read(start, table.stride * table.count)
    cities: Dict[Tuple[int, int, int], str] = {}
    for i in range(table.count):
        rec = raw[i * table.stride:(i + 1) * table.stride]
        if locate._valid_city(rec):
            cities[(rec[15], rec[16], rec[17])] = rec[:14].split(b"\0", 1)[0].decode("latin-1")
    return cities


def peek(api: DosboxApi, block: str, number: int, spec: Optional[str], as_json: bool = False) -> str:
    game = find_game(api)
    record = read_record(api, game, block, number)
    names = list(game.names)
    own = number - 1 if block == "wizard" else None
    title = f"{F.blocks()[block].describe} {number}"
    if block in ("wizard", "fortress") and number <= len(names):
        title += f" ({names[number - 1]})"
    try:
        if spec is None:
            chosen: List[Tuple[F.Field, Optional[str]]] = [(f, None) for f in F.all_fields(block)]
        else:
            name, _, element = spec.partition(".")
            chosen = [(F.find(block, name), element or None)]
        if as_json:
            if len(chosen) == 1 and chosen[0][1] is not None:
                f, el = chosen[0]
                i = f.element(el, names)                                         # type: ignore[arg-type]
                return json.dumps({f.name: f.decode(_slice(f, record))[i]})      # type: ignore[index]
            return json.dumps({"block": block, "number": number,
                               "fields": {f.name: as_data(f, record, names, own) for f, _ in chosen}}, indent=1)
        # the city table is read only to name a position (the summoning circle): not for `peek wizard 1 gold`
        cities = read_cities(api, game) if any(f.format == "map_position" and el is None for f, el in chosen) else {}
        lines = [render(f, record, names, el, own, cities) for f, el in chosen]
    except F.FieldError as err:
        raise PeekError(str(err)) from None
    return "\n".join(([title] if spec is None else []) + [("  " if spec is None else "") + ln for ln in lines])


def describe_fields(block: Optional[str] = None) -> str:
    """The table of known fields, for ``mompy fields``."""
    rows = [("BLOCK", "FIELD", "TYPE", "RANGE", "EDITABLE", "SURE", "NOTE")]
    for f in F.all_fields(block):
        kind = f"text[{f.length}]" if f.type == "text" else (f"{f.type}[{f.count}]" if f.is_array else f.type)
        rng = f"{f.min}..{f.max}" if f.min is not None and f.max is not None else ""
        write = "no (derived)" if f.derived else ("yes" if f.writable else "no")
        rows.append((f.block, f.name, kind, rng, write, f.confidence, f.note.split(". ")[0].rstrip(".")))
    widths = [max(len(r[i]) for r in rows) for i in range(6)]
    return "\n".join("  ".join(c.ljust(widths[i]) for i, c in enumerate(r[:6])) + "  " + r[6] for r in rows)
