"""``mompy banish wizard N`` and ``unbanish``: take a wizard's fortress, or give it back.

A wizard whose fortress record is inactive is *banished*: the Magic screen draws him as a cracked stone frame, and the game
has him cast Spell of Return (the 1995 editor's manual, section 5.3). He is not dead; he is only eliminated if he has no cities
left. This writes the one byte (``active`` of the fortress table) through ``poke``, so it is a compare-and-swap, it is logged for
``undo``, and it is refused if the fortress table does not look right in this game.
"""

from __future__ import annotations

from . import layout, peek
from .api import DosboxApi
from .poke import PokeError, poke


def _active(api: DosboxApi, base: int, number: int) -> int:
    return api.read(base + layout.FORTRESSES.offset + (number - 1) * layout.FORTRESSES.stride + 3, 1)[0]


def _set(api: DosboxApi, number: int, active: int, force: bool, dry_run: bool) -> str:
    found = peek.find_game(api)
    if not 1 <= number <= 5:
        raise PokeError(f"there is no wizard {number} to banish (1 to 5; the neutral player has none)")
    who = f"wizard {number} ({found.names[number - 1]})"
    if active == 0 and number == 1 and not force:
        raise PokeError(f"{who} is you. Banishing the player takes your own fortress; --force if you mean it")
    banished = _active(api, found.base, number) == 0
    if active == 0 and banished:
        return f"{who} is already banished"
    if active == 1 and not banished:
        return f"{who} is not banished"
    poke(api, number, "active", str(active), dry_run=dry_run, force=force, block_name="fortress")
    if active == 0:
        return f"(dry run) would banish {who}" if dry_run else f"{who} is banished"
    return f"(dry run) would lift the banishment of {who}" if dry_run else f"{who}: banishment lifted"


def banish(api: DosboxApi, number: int, force: bool = False, dry_run: bool = False) -> str:
    """Banish wizard ``number`` (1 is the player, refused without ``force``)."""
    return _set(api, number, 0, force, dry_run)


def unbanish(api: DosboxApi, number: int, dry_run: bool = False) -> str:
    """Give wizard ``number`` his fortress back (the cities of an eliminated wizard are not coming back)."""
    return _set(api, number, 1, False, dry_run)
