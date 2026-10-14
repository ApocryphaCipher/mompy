"""Where Master of Magic keeps its tables, relative to the wizard table.

The addresses are the research setup's (``docs/reference/ram-layout.md``: GOG 1.31 in DOSBox Staging
0.84-alpha, wizard table at ``0x328BA``). Another DOSBox build moves the whole game by a fixed number of bytes
(0.83.0 sat ``0x520`` lower), so every table is stored as an offset from the wizard table and a
located game adds its own base. Nothing here is trusted without the plausibility checks in ``locate``.
"""

from __future__ import annotations

from typing import NamedTuple

REFERENCE_WIZARD_BASE = 0x328BA

WIZARD_STRIDE = 0x4C8
WIZARD_COUNT = 5
WIZARD_NAME_AT = 1       # +0x01, 20 bytes NUL-padded
WIZARD_NAME_LEN = 20


class Table(NamedTuple):
    name: str
    reference: int       # address in the research setup
    stride: int
    count: int

    @property
    def offset(self) -> int:
        """Bytes from the wizard table to this table."""
        return self.reference - REFERENCE_WIZARD_BASE


WIZARDS = Table("wizards", REFERENCE_WIZARD_BASE, WIZARD_STRIDE, WIZARD_COUNT)
CITIES = Table("cities", 0x6F980, 114, 100)
UNITS = Table("units", 0x7E060, 32, 1009)
NODES = Table("nodes", 0x85FE0, 48, 30)
ENCOUNTERS = Table("lairs", 0x86660, 24, 102)
# x, y, plane, active for each wizard and then the neutral player. Found 2026-10-13 by searching memory for the five
# summoning-circle positions. The game keeps a second copy 0x1030 later (0x875F0), as it does for the node table.
FORTRESSES = Table("fortresses", 0x865C0, 4, 6)

# The game's data segment starts this far below the wizard table (0x289F0 vs 0x328BA), whatever the DOSBox build.
DGROUP_BELOW_WIZARDS = 0x9ECA
# In the data segment: where the pointer is on the 320 x 200 screen (u16 x, u16 y), the world tile at the map view's top-left
# (u16 x, u16 y), and the plane being viewed (u16). Found 2026-10-13 (STORY-010): see docs/reference/ram-layout.md.
POINTER_IN_DGROUP, VIEW_ORIGIN_IN_DGROUP, VIEW_PLANE_IN_DGROUP = 0x78C2, 0x6FFE, 0xBD86
UNIT_COUNT_REFERENCE = 0x34782   # a u16: how many unit records are live

TABLES = (WIZARDS, CITIES, UNITS, NODES, ENCOUNTERS, FORTRESSES)


def table(name: str) -> Table:
    """A table by name (the field table's blocks refer to these)."""
    for t in TABLES:
        if t.name == name:
            return t
    raise KeyError(name)
