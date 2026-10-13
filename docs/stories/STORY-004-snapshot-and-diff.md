# STORY-004: snapshot and diff

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`momctl snapshot NAME` stores every wizard's record (and later cities and units) from the running game; `momctl diff A B` prints what changed, by field name when the field is in the table and by offset otherwise.
It is the generalised form of the throwaway `snap.py` that found the diplomacy and globals fields in Mirror (2026-10-12): cast, send gold, make a treaty, snapshot, and see exactly which bytes moved.

## Definition of done

Tests with two fabricated snapshots; the Aura of Majesty cast reproduces: global byte 3 0 to 1 and the relations to 20.
