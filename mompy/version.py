"""DOSBox Staging version strings, and what we know about each version's memory layout."""

from __future__ import annotations

import re
from typing import NamedTuple, Optional

# Where the wizard table sits in the game's memory (STORY-008 and docs/reference/ram-layout.md).
WIZARD_BASE_0_84 = 0x328BA   # DOSBox Staging 0.84 (DOS STACKS reserves 82 paragraphs before programs load)
WIZARD_BASE_0_83 = 0x3239A   # DOSBox Staging 0.83.x: 0x520 lower, no STACKS


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    tag: str      # "alpha", "rc1" ... or ""
    build: str    # the commit in the brackets, or ""
    text: str     # the string as DOSBox reported it


_PATTERN = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z0-9.]+))?(?:\s*\(([0-9a-fA-F]+)\))?")


def parse(text: str) -> Optional[Version]:
    """``"0.84.0-alpha (5b1f1d)"`` -> ``Version(0, 84, 0, "alpha", "5b1f1d", ...)``, or ``None``."""
    m = _PATTERN.match(text or "")
    if not m:
        return None
    return Version(int(m[1]), int(m[2]), int(m[3]), m[4] or "", m[5] or "", text)


def expected_wizard_base(version: Optional[Version]) -> Optional[int]:
    """Where the wizard table should be for this DOSBox with the default ``stacks`` setting, if we know.

    A ``stacks`` setting other than the default moves it again, and a game release other than the
    GOG 1.31 differs too, so this is an expectation to compare with, never an address to trust.
    """
    if version is None:
        return None
    if (version.major, version.minor) == (0, 83):
        return WIZARD_BASE_0_83
    if (version.major, version.minor) >= (0, 84):
        return WIZARD_BASE_0_84
    return None
