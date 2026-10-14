"""Finding the game, and remembering where it was between commands.

``doctor`` reads all 16 MiB and scans for the wizard table every time: it is the check. The other commands should not:
a script that runs ten ``poke`` commands would read 160 MiB. So the base address found is kept in ``$MOMPY_HOME/cache.json``
(default ``~/.mompy``), keyed by the DOSBox URL, and trusted only after a small read confirms it: the five wizard names
are still there and a city table is still there. A stale or damaged cache is never an error; it is a rescan.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from . import layout, locate, spellnames
from .api import MEMORY_SIZE, ApiError, DosboxApi


def home() -> Path:
    """mompy's own folder: the undo log and this cache."""
    return Path(os.environ.get("MOMPY_HOME") or Path.home() / ".mompy")


def _cache_path() -> Path:
    return home() / "cache.json"


def _load_cache() -> dict:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _remember(url: str, base: int, spells=None) -> None:
    """Remember where the wizard table is and, with ``spells``, where the spell table is (an address, or False for none)."""
    cache = _load_cache()
    old = cache.get(url) if isinstance(cache.get(url), dict) else {}
    entry = dict(old) if old.get("base") == base else {}
    entry["base"] = base
    if spells is not None:
        entry["spells"] = spells
    cache[url] = entry
    try:
        home().mkdir(parents=True, exist_ok=True)
        _cache_path().write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass                                    # a cache that cannot be written is only slower


def _confirm(api: DosboxApi, base: int) -> Optional[locate.Game]:
    """The game at ``base``, if five wizard names and a plausible city are still there."""
    try:
        if base < 0:
            return None
        table = api.read(base, layout.WIZARD_STRIDE * layout.WIZARD_COUNT)
        names = [locate._name_at(table, i * layout.WIZARD_STRIDE) for i in range(layout.WIZARD_COUNT)]
        if not all(names):
            return None
        cities = layout.CITIES
        raw = api.read(base + cities.offset, cities.stride * cities.count)
        if not any(locate._valid_city(raw[i * cities.stride:(i + 1) * cities.stride]) for i in range(cities.count)):
            return None
        return locate.Game(base, names, [], [])
    except ApiError:
        return None


def connect(api: DosboxApi) -> locate.Game:
    """The game in this DOSBox: from the remembered address if it still holds, else by scanning.

    Raises ``locate.GameNotFound`` (with the reason) when there is no usable game.
    """
    game = _find(api)
    entry = _load_cache().get(api.url)
    hint = entry.get("spells") if isinstance(entry, dict) and entry.get("base") == game.base else None
    if not isinstance(hint, (int, bool)):
        hint = None
    names, where = spellnames.read(api, game.base, hint)
    if where is not None and where != hint:
        _remember(api.url, game.base, where)
    return game._replace(names=locate.Names(game.names, names))


def _find(api: DosboxApi) -> locate.Game:
    entry = _load_cache().get(api.url)
    base = entry.get("base") if isinstance(entry, dict) else None
    if isinstance(base, int):
        game = _confirm(api, base)
        if game is not None:
            return game
    game = locate.find_game(api.read(0, MEMORY_SIZE))
    _remember(api.url, game.base)
    return game
