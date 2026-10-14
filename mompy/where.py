"""``mompy where NAME``: find a city or a wizard by name and say where it is.

Read-only. City names and positions are in the running game's memory (nothing from a game file). The coordinates are the
ones Mirror's editors take: tile x, tile y, and the plane (Arcanus is 0, Myrror is 1).
"""

from __future__ import annotations

import difflib
import json
import struct
from dataclasses import dataclass
from typing import List, Optional

from . import layout, locate
from .api import DosboxApi
from .peek import PeekError, find_game

PLANES = ("Arcanus", "Myrror")
SIZE_NAMES = {0: "Outpost", 1: "Hamlet", 2: "Village"}      # higher classes have not been seen in the game yet
NEUTRAL = 5


@dataclass(frozen=True)
class City:
    name: str
    x: int
    y: int
    plane: int
    owner: int          # wizard record 0 to 4, or 5 for neutral
    size: int
    population: int     # thousands
    slot: int = 0       # position in the city table: city number is slot + 1


def read_cities(api: DosboxApi, game: locate.Game) -> List[City]:
    """Every plausible city record; empty and stale slots are skipped the way ``doctor`` skips them."""
    table = layout.CITIES
    raw = api.read(game.base + table.offset, table.stride * table.count)
    cities = []
    for i in range(table.count):
        rec = raw[i * table.stride:(i + 1) * table.stride]
        if locate._valid_city(rec):
            cities.append(City(rec[:14].split(b"\0", 1)[0].decode("latin-1"),
                               rec[15], rec[16], rec[17], rec[18], rec[19], rec[20], i))
    return cities


def _owner(city: City, names: List[str]) -> str:
    return "neutral" if city.owner >= len(names) else names[city.owner]


def _place(plane: int, x: int, y: int) -> str:
    return f"{PLANES[plane] if 0 <= plane < 2 else f'plane {plane}'} ({x}, {y})"


def _city_data(city: City, names: List[str]) -> dict:
    return {"kind": "city", "name": city.name, "plane": PLANES[city.plane], "x": city.x, "y": city.y,
            "owner": _owner(city, names), "size": SIZE_NAMES.get(city.size, f"size {city.size}"),
            "population": city.population * 1000}


def _city_line(city: City, names: List[str]) -> str:
    size = SIZE_NAMES.get(city.size, f"size {city.size}")
    return (f"{city.name}: {_place(city.plane, city.x, city.y)}, owner {_owner(city, names)}, "
            f"a {size} of population {city.population}")


def _circle(api: DosboxApi, game: locate.Game, index: int) -> Optional[tuple]:
    at = game.base + layout.WIZARDS.offset + index * layout.WIZARDS.stride + 0x2E
    x, y, plane = struct.unpack("<3h", api.read(at, 6))
    return (x, y, plane) if 0 <= x < 60 and 0 <= y < 40 and plane in (0, 1) else None


def _wizard(api: DosboxApi, game: locate.Game, index: int, cities: List[City]) -> tuple:
    names = list(game.names)
    circle = _circle(api, game, index)
    data = {"kind": "wizard", "number": index + 1, "name": names[index], "summoning_circle": None}
    if circle is None:
        return data, f"{names[index]} (wizard {index + 1}): no summoning circle position that makes sense"
    x, y, plane = circle
    data["summoning_circle"] = {"plane": PLANES[plane], "x": x, "y": y}
    line = f"{names[index]} (wizard {index + 1}): summoning circle {_place(plane, x, y)}"
    here = next((c for c in cities if (c.x, c.y, c.plane) == circle), None)
    if here is not None:
        data["summoning_circle"]["city"] = here.name
        line += f", the city {here.name}"
    return data, line


def find_city(api: DosboxApi, text: str) -> int:
    """The number (1 to 100) of the one city that ``text`` names: a number, a whole name, or a unique prefix."""
    text = text.strip()
    if text.isdigit():
        return int(text)
    game = find_game(api)
    cities = read_cities(api, game)
    exact = [c for c in cities if c.name.lower() == text.lower()]
    found = exact or [c for c in cities if c.name.lower().startswith(text.lower())]
    if not found:
        raise PeekError(f"there is no city called {text!r}")
    if len(found) > 1:
        raise PeekError(f"{text!r} could be " + ", ".join(c.name for c in found) + ": give more of the name")
    return found[0].slot + 1


def where(api: DosboxApi, query: str, as_json: bool = False) -> str:
    """Find ``query`` among the city and wizard names: whole name first, else a unique prefix; several matches are listed."""
    text = query.strip().lower()
    if not text:
        raise PeekError("say a name: mompy where Blackstone")
    game = find_game(api)
    names = list(game.names)
    cities = read_cities(api, game)
    if text == "pointer":
        return _under_pointer(api, game, cities, names, as_json)
    candidates = [("city", c.name, c) for c in cities] + [("wizard", n, i) for i, n in enumerate(names)]
    exact = [c for c in candidates if c[1].lower() == text]
    found = exact or [c for c in candidates if c[1].lower().startswith(text)]
    if not found:
        close = difflib.get_close_matches(text, [c[1].lower() for c in candidates], n=3, cutoff=0.5)
        shown = [c[1] for c in candidates if c[1].lower() in close]
        raise PeekError(f"nothing is called {query!r}" + (f"; did you mean {', '.join(shown)}?" if shown else ""))
    results = [(_city_data(obj, names), _city_line(obj, names)) if kind == "city" else _wizard(api, game, obj, cities)
               for kind, _, obj in found]
    if len(results) > 1 and not as_json:
        return f"{len(results)} names start with {query!r}:\n" + "\n".join("  " + line for _, line in results)
    if as_json:
        return json.dumps([d for d, _ in results], indent=1)
    return results[0][1]


def _under_pointer(api: DosboxApi, game: locate.Game, cities: List[City], names: List[str], as_json: bool) -> str:
    """What is on the map tile under the mouse: the tile, its city and its units."""
    from .pointer import tile_under_pointer
    from .poke import PokeError
    from .summon import DEAD, read_types

    try:
        x, y, plane = tile_under_pointer(api, game)
    except PokeError as err:
        raise PeekError(str(err)) from None
    table = layout.UNITS
    live = struct.unpack("<H", api.read(game.base + (layout.UNIT_COUNT_REFERENCE - layout.REFERENCE_WIZARD_BASE), 2))[0]
    raw = api.read(game.base + table.offset, table.stride * min(live, table.count))
    types = read_types(api, game)
    units = [(types[raw[i * 32 + 5]].name, i, raw[i * 32 + 3]) for i in range(len(raw) // 32)
             if tuple(raw[i * 32:i * 32 + 3]) == (x, y, plane) and raw[i * 32 + 3] != DEAD]
    city = next((c for c in cities if (c.x, c.y, c.plane) == (x, y, plane)), None)
    owner = lambda o: names[o] if o < len(names) else "neutral"
    if as_json:
        return json.dumps({"plane": PLANES[plane], "x": x, "y": y, "city": _city_data(city, names) if city else None,
                           "units": [{"unit": n, "type": t, "owner": owner(o)} for t, n, o in units]}, indent=1)
    line = _place(plane, x, y)
    if city:
        line += f"  city {city.name}, owner {_owner(city, names)}"
    if units:
        line += f"  {len(units)} unit{'s' if len(units) != 1 else ''}: " + ", ".join(f"{t} #{n} ({owner(o)})" for t, n, o in units)
    return line
