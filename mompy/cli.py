"""The ``mompy`` command."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .api import DEFAULT_URL, ApiError, DosboxApi
from . import banish as banishing
from . import cast as casting
from . import city as cities
from . import peek as peeking
from . import pew as pewing
from . import poke as poking
from . import summon
from . import unit as units
from . import where as whereis
from .doctor import diagnose, render


def _number(api: DosboxApi, block: str, text: str) -> int:
    """The record number for what the player typed: a city may be named; everything else is a number."""
    if block == "city":
        return whereis.find_city(api, text)
    try:
        return int(text)
    except ValueError:
        raise peeking.PeekError(f"{text!r} is not a {block} number") from None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mompy", description="Read and change a running Master of Magic.")
    parser.add_argument("--version", action="version", version=f"mompy {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--url", default=DEFAULT_URL,
                        help=f"DOSBox's web API (default {DEFAULT_URL}; see DOSBox's webserver_port setting)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", parents=[common], help="check that the game can be read and written safely")
    pk = sub.add_parser("peek", parents=[common], help="read a record's fields from the running game")
    pk.add_argument("block", choices=["wizard", "fortress", "city"], help="what to read")
    pk.add_argument("number", help="which one; wizard 1 is the player; a city by name (darkmoor) or number")
    pk.add_argument("field", nargs="?", help="a field, or field.element (books.sorcery, relations.freya); omit for all")
    pk.add_argument("--json", action="store_true", help="print plain data for scripts")
    pk2 = sub.add_parser("poke", parents=[common], help="change a field of the running game (checked, undoable)")
    pk2.add_argument("block", choices=["wizard", "fortress", "city"], help="what to change")
    pk2.add_argument("number", help="which one; wizard 1 is the player; a city by name (darkmoor) or number")
    pk2.add_argument("field", help="a field, or field.element (books.sorcery, relations.freya); or cast / dispel a global enchantment")
    pk2.add_argument("value", nargs="?", help="a number, an enum word (alliance), on/off for flags, or a,b,c for a whole array; for cast/dispel, the enchantment")
    pk2.add_argument("--dry-run", action="store_true", help="say what would change; write and log nothing")
    pk2.add_argument("--force", action="store_true", help="also write a field that is only a guess, or cast one of the questionable globals")
    pk2.add_argument("--count", type=int, default=1, help="cast unit.NAME or city create NAME: how many units (1 to 9)")
    pk2.add_argument("--at", help="cast unit.NAME: where, a city or x,y,plane; default the wizard's summoning circle")
    sub.add_parser("undo", parents=[common], help="put the last poke back")
    bn = sub.add_parser("banish", parents=[common], help="banish a wizard: take his fortress (he is not dead; he casts Spell of Return)")
    bn.add_argument("block", choices=["wizard"])
    bn.add_argument("number", type=int, help="which wizard; 1 is the player and needs --force")
    bn.add_argument("--force", action="store_true", help="allow banishing the player")
    bn.add_argument("--dry-run", action="store_true", help="say what would change; write nothing")
    ub = sub.add_parser("unbanish", parents=[common], help="give a banished wizard his fortress back")
    ub.add_argument("block", choices=["wizard"])
    ub.add_argument("number", type=int)
    ub.add_argument("--dry-run", action="store_true", help="say what would change; write nothing")
    wh = sub.add_parser("where", parents=[common], help="find a city or a wizard by name (a unique prefix works)")
    wh.add_argument("name", help="a city or wizard name, any case")
    wh.add_argument("--json", action="store_true", help="print plain data for scripts; several matches are all listed")
    un = sub.add_parser("unit", parents=[common], help="act on units in the running game")
    un.add_argument("action", choices=["mercury"], help="mercury: give units all the movement they can hold, for this turn")
    un.add_argument("--at", help="the stack on a city or x,y,plane")
    un.add_argument("--wizard", type=int, help="every unit of this wizard (1 is the player)")
    un.add_argument("--dry-run", action="store_true", help="say what would change; write nothing")
    pw = sub.add_parser("pew", parents=[common], help="kill the units on a tile (not the city): pointer, a city name, or x,y,plane")
    pw.add_argument("place", help="pointer (the tile under the mouse), a city's name, or x,y,plane")
    pw.add_argument("--dry-run", action="store_true", help="say what would die; write nothing")
    fl = sub.add_parser("fields", help="list the fields mompy knows, with their ranges and how sure we are")
    fl.add_argument("block", nargs="?", choices=["wizard", "fortress", "city"])

    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = diagnose(DosboxApi(args.url))
        print(render(report, args.url))
        return 0 if report.ready else 1
    if args.command in ("banish", "unbanish"):
        try:
            api = DosboxApi(args.url)
            if args.command == "banish":
                print(banishing.banish(api, args.number, args.force, args.dry_run))
            else:
                print(banishing.unbanish(api, args.number, args.dry_run))
        except (poking.PokeError, peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    if args.command in ("poke", "undo"):
        try:
            api = DosboxApi(args.url)
            if args.command == "undo":
                print(poking.undo(api))
            else:
                args.number = _number(api, args.block, args.number)
                if args.block == "city" and args.field == "build":
                    print(cities.build(api, args.number, args.dry_run, args.force))
                    return 0
                if args.value is None:
                    raise poking.PokeError(f"say what to change {args.field} to: mompy poke {args.block} N {args.field} VALUE")
                if args.block == "city" and args.field == "create":
                    print(summon.create(api, args.number, args.value.removeprefix("unit."), args.count, args.dry_run))
                    return 0
                if args.field in ("cast", "dispel"):
                    if args.block != "wizard":
                        raise poking.PokeError(f"{args.field} is for wizards: mompy poke wizard N {args.field} aura_of_majesty")
                    if args.field == "cast" and args.value.lower().startswith("unit."):
                        print(summon.summon(api, args.number, args.value[5:], args.count, args.at, args.dry_run))
                    elif args.field == "cast":
                        print(casting.cast(api, args.number, args.value, args.dry_run, args.force))
                    else:
                        print(casting.dispel(api, args.number, args.value, args.dry_run))
                else:
                    print(poking.poke(api, args.number, args.field, args.value, args.dry_run, args.force, block_name=args.block))
        except (poking.PokeError, peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    if args.command == "where":
        try:
            print(whereis.where(DosboxApi(args.url), args.name, args.json))
        except (peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    if args.command == "pew":
        try:
            print(pewing.pew(DosboxApi(args.url), args.place, args.dry_run))
        except (poking.PokeError, peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    if args.command == "unit":
        try:
            print(units.mercury(DosboxApi(args.url), args.at, args.wizard, args.dry_run))
        except (poking.PokeError, peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    if args.command == "fields":
        print(peeking.describe_fields(args.block))
        return 0
    if args.command == "peek":
        try:
            api = DosboxApi(args.url)
            print(peeking.peek(api, args.block, _number(api, args.block, args.number), args.field, args.json))
        except (peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
