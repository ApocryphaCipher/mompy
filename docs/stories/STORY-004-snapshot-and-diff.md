# STORY-004: snapshot and diff

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), checked on a real game
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`mompy snapshot NAME` stores every wizard's record (and later cities and units) from the running game; `mompy diff A B` prints what changed, by field name when the field is in the table and by offset otherwise.
It is the generalised form of the throwaway `snap.py` that found the diplomacy and globals fields in Mirror (2026-10-12): cast, send gold, make a treaty, snapshot, and see exactly which bytes moved.

## Definition of done

Tests with two fabricated snapshots; the Aura of Majesty cast reproduces: global byte 3 0 to 1 and the relations to 20.

## Outcome

`mompy snapshot NAME [--replace] [--list]` and `mompy diff A B [--ignore C] [--all]` (`mompy/snapshot.py`, `tests/test_snapshot.py`).

- A snapshot keeps all six tables (wizards, cities, units, nodes, lairs, fortresses), the unit count and the game's 64 KiB **data segment** (where the pointer, the map view and many counters live): 8 regions, 116 KiB, one JSON file in `$MOMPY_HOME/snapshots`. Names are letters, digits, `.`, `_`, `-`; an existing name is refused unless `--replace`. Nothing is written to the game.
- A diff names a changed field by the field table (`wizard 1 (Jafar) globals.Aura of Majesty: 0 -> 1`, `city 3 (Darkmoor) population: 4 -> 25`) and by ReMoM's unit record (`unit 160 (type 179) moves_left: 4 -> 0`); anything else is a raw offset. The data-segment window also covers the wizard table and the unit count, so those bytes are not shown twice.
- **Noise:** two reads of the same game differ by a few hundred bytes (timers). `--ignore C` takes a second snapshot of the same moment as A and leaves out every byte that differs between A and C. Only the bytes that actually ticked between those two reads are removed, so a handful of timer bytes can still appear.
- Output stops at 200 lines unless `--all`. A missing or damaged snapshot is an error message, never a crash.
- Real game (2026-10-14): two snapshots of one moment, `poke wizard 1 mana 100`, a third snapshot: `diff --ignore` named `wizard 1 (Jafar) mana: 0 -> 100` and showed nine data-segment runs. `undo` put it back.
- Not done: the Aura of Majesty cast of the Definition of done was reproduced with fabricated snapshots (globals byte 3 and the relations), not replayed on a real game; a `--region` filter; snapshots of the whole 16 MiB.
