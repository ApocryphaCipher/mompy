# STORY-002: The field table and peek

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-13), PR open; the run against Kevin's real game is still to do
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

A **field table** (a data file: TOML or JSON) lists every field: block, record size, offset in the record, type (u8, u16, i8, i16, text), range, a note and a **confidence mark**
(`checked` or `guess`). Start with the wizard fields in [ram-layout.md](../reference/ram-layout.md).

`mompy fields` lists them. `mompy peek wizard 1 gold` reads one value; `peek wizard 1 books` reads the group; with no field it prints the record's known fields.
The wizard number is the human one (1 is the player), as on Mirror's `/wizard/:id` page.

## Definition of done

Unit tests on the table's decoding (every type, a record in the middle of the table, a bad name); one run against the real game, compared with the game's own screen.

## Outcome (2026-10-13)

Built: the field table `mompy/fields.toml` (TOML, since the Python floor became 3.12; comments allowed) with 20 wizard fields, each with offset, type, count, labels, range, whether the game accepts changes (`writable`), whether the game recomputes it (`derived`), a **confidence mark** and a note;
`mompy/fields.py` (loading, `decode` and its reverse `encode`, element lookup by label or number); `mompy/peek.py`; and the commands `mompy fields` and `mompy peek wizard N [field[.element]] [--json]`.
`locate.find_game` is now shared by `doctor` and `peek` (same scan, same plausibility checks, refuses with a pointer to `doctor`).

- `peek wizard 1 gold` -> `gold = 30000`; `peek wizard 1 books` -> `books = nature 0, sorcery 12, ...`; `books.sorcery` or `books.2` picks one; `relations` is labelled with the wizards' **own names** read from memory (`relations.freya`); retorts and globals list only what is set; the 214 spells are summarised (`50 known, 6 on the research list, ...`) and `spells.10` asks for one.
- Wizard numbering is the human one (1 is the player), as on Mirror's page; 0 and 6 are refused with the range.
- Read-only by construction: a test checks that no write is sent and that memory is unchanged.
- 43 tests (23 new): the table is consistent (no overlaps, labels match counts, ranges fit their types, derived fields are not editable, the documented offsets are the ones in the table), every type decodes and encodes back, and `peek` is tested against the fake server for each field kind, JSON, errors, another game address (`0x3239A`) and no game.
- *Not yet done:* compare with the game's own screens on a real game (the story's definition of done).
