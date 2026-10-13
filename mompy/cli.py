"""The ``mompy`` command."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .api import DEFAULT_URL, ApiError, DosboxApi
from . import peek as peeking
from .doctor import diagnose, render


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mompy", description="Read and change a running Master of Magic.")
    parser.add_argument("--version", action="version", version=f"mompy {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--url", default=DEFAULT_URL,
                        help=f"DOSBox's web API (default {DEFAULT_URL}; see DOSBox's webserver_port setting)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", parents=[common], help="check that the game can be read and written safely")
    pk = sub.add_parser("peek", parents=[common], help="read a record's fields from the running game")
    pk.add_argument("block", choices=["wizard"], help="what to read")
    pk.add_argument("number", type=int, help="which one; wizard 1 is the player")
    pk.add_argument("field", nargs="?", help="a field, or field.element (books.sorcery, relations.freya); omit for all")
    pk.add_argument("--json", action="store_true", help="print plain data for scripts")
    fl = sub.add_parser("fields", help="list the fields mompy knows, with their ranges and how sure we are")
    fl.add_argument("block", nargs="?", choices=["wizard"])

    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = diagnose(DosboxApi(args.url))
        print(render(report, args.url))
        return 0 if report.ready else 1
    if args.command == "fields":
        print(peeking.describe_fields(args.block))
        return 0
    if args.command == "peek":
        try:
            print(peeking.peek(DosboxApi(args.url), args.block, args.number, args.field, args.json))
        except (peeking.PeekError, ApiError) as err:
            print(f"mompy: {err}", file=sys.stderr)
            return 1
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
