"""The ``mompy`` command."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .api import DEFAULT_URL, DosboxApi
from .doctor import diagnose, render


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="mompy", description="Read and change a running Master of Magic.")
    parser.add_argument("--version", action="version", version=f"mompy {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--url", default=DEFAULT_URL,
                        help=f"DOSBox's web API (default {DEFAULT_URL}; see DOSBox's webserver_port setting)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", parents=[common], help="check that the game can be read and written safely")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = diagnose(DosboxApi(args.url))
        print(render(report, args.url))
        return 0 if report.ready else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
