"""``mompy poke wizard N cast <global>`` and ``dispel``: put a global enchantment straight on a wizard's list.

A global enchantment is one byte of the caster's 24 (``globals`` in the field table): 1 when active. ``cast`` sets it and the wizard
is the caster; it skips the spell's cost, the spell book and every check the game makes when you cast, and a real cast only takes
effect at End Turn, so this makes it active *now*. What the game then does with it (the effect, the upkeep, a dispel it cannot
afford) is the game's own business at End Turn. It is a ``poke`` underneath: a compare-and-swap, logged for ``undo``.

Time Stop is the one *questionable* global (STORY-014, tried 2026-10-14): set by hand it showed in the Magic screen and was charged
(about 100 mana a turn), but the other wizards still took their turns, so it does nothing useful; it needs ``--force``. The other four
that change the map or the turns (Planar Seal, Armageddon, Meteor Storm, Great Wasting) went through a real End Turn without a hitch
and cast like any other. Taking one off (``dispel``) never needs ``--force``.
"""

from __future__ import annotations

from . import fields as F
from . import peek
from .api import DosboxApi
from .poke import PokeError, poke, resolve

QUESTIONABLE = ("Time Stop",)


def _change(api: DosboxApi, number: int, text: str, on: bool, dry_run: bool, force: bool) -> str:
    found = peek.find_game(api)
    block = F.blocks()["wizard"]
    last = block.first_number + block.count - 1
    if not block.first_number <= number <= last:
        raise PokeError(f"there is no wizard {number} (1 to {last})")
    names = list(found.names)
    field = F.find("wizard", "globals")
    name = text.strip()
    if name.lower().startswith("globals."):
        name = name[len("globals."):]
    if not name:
        raise PokeError("which enchantment? e.g. aura_of_majesty (see: mompy peek wizard 1 globals)")
    try:
        index = field.element(name, names)
    except F.FieldError as err:
        raise PokeError(str(err)) from None
    spell = field.label_for(index)
    who = f"wizard {number} ({names[number - 1]})"
    if on and spell in QUESTIONABLE and not force:
        raise PokeError(f"{spell} does nothing when set by hand (the other wizards still take their turns) but costs about 100 mana a turn; --force to cast it anyway")
    target = resolve(found, field, number, str(index + 1), names)
    active = api.read(target.address, 1)[0] != 0
    if on and active:
        return f"{who} already has {spell}"
    if not on and not active:
        return f"{who} does not have {spell}"
    if dry_run:
        return f"(dry run) would cast {spell} on {who}" if on else f"(dry run) would dispel {spell} from {who}"
    poke(api, number, f"globals.{index + 1}", "1" if on else "0")
    return f"{spell} cast on {who}" if on else f"{spell} dispelled from {who}"


def cast(api: DosboxApi, number: int, text: str, dry_run: bool = False, force: bool = False) -> str:
    """Put global enchantment ``text`` on wizard ``number`` (he is the caster)."""
    return _change(api, number, text, True, dry_run, force)


def dispel(api: DosboxApi, number: int, text: str, dry_run: bool = False) -> str:
    """Take global enchantment ``text`` off wizard ``number``."""
    return _change(api, number, text, False, dry_run, False)
