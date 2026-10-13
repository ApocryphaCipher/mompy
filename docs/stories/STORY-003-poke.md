# STORY-003: poke, safely

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

`momctl poke wizard 1 gold 30000`:

- range-check against the field table (refuse and say why; never clamp silently); refuse a `guess` field without `--force`;
- read the current bytes, write with **`If-Match` set to them**, and stop on a 412 (`someone or the game changed it`);
- print `gold: 8293 -> 30000`; `--dry-run` prints it without writing;
- keep a log of old bytes (`~/.mompy/undo.jsonl`) and `momctl undo` puts the last write back (again with a compare-and-swap);
- fields that are written on **both** wizards (a relation or a treaty) write both, or neither.

## Definition of done

Tests against the fake server (a 412 changes nothing; undo restores; a refused value writes nothing); the real game shows 30000 on its main screen and survives one End Turn.
