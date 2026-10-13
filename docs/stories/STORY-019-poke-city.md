# STORY-019: `mompy poke city <name> <field> <value>`: change a city by name (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** proposed (2026-10-13). **Priority: nice to have.** After [STORY-011](STORY-011-where-name.md) (`where` already finds a city by name and has the reader).
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13 (`mompy poke city darkmoor population 25`)

## What to do

A third block, `city`, in the field table, next to `wizard` and `fortress`, with the same `poke` safety (compare-and-swap, range checks, `--dry-run`, `undo`).

```
mompy poke city darkmoor population 25
mompy peek city darkmoor
```

- **Naming.** A city is named, not numbered: the same rules as `where` (whole name, else unique prefix, ambiguity refused). The record number is still accepted (`poke city 3 ...`) and printed, for scripts.
- **Population.** The city screen shows `+20` × 1000 + `+24` × 10 (u16, tens), checked by a live RAM write ([Mirror's live-ram-map.md](https://github.com/ApocryphaCipher/Mirror/blob/main/docs/reference/live-ram-map.md)). Take the number the player sees (`25` = 25,000, or `25.4`) and write both fields, one undo entry.
- First fields: `population`, `owner` (by wizard name; **not** a bare byte write: Mirror's `edit_city` also clears the city's enchantments and hands over its units, so this needs a spike or is left out of the first cut), `race`. Later: buildings, enchantments.
- **Limits.** The same ones as Mirror's `edit_city` (a capital cannot be handed away, population range). *To check:* the game's own cap on population per size class, and whether a hand-set population above it is kept or trimmed at End Turn.

## Notes

- `where` shows `+20` only (thousands, "population 7"). That is deliberate: Kevin only needs the rough figure there (2026-10-13).
- A city's record is 114 bytes; the table is found the way `doctor` finds it.

## Definition of done

On the real game: `poke city darkmoor population 25` and the city screen says 25,000; `undo` puts it back; one End Turn shows what the game does with it (written down, whatever it is). Tests with the fake DOSBox.
