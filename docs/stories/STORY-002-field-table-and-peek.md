# STORY-002: The field table and peek

**Parent:** [EPIC-001](../epics/EPIC-001-momctl-core.md)
**Status:** proposed (2026-10-13)
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-13

## What to do

A **field table** (a data file: TOML or JSON) lists every field: block, record size, offset in the record, type (u8, u16, i8, i16, text), range, a note and a **confidence mark**
(`checked` or `guess`). Start with the wizard fields in [ram-layout.md](../reference/ram-layout.md).

`momctl fields` lists them. `momctl peek wizard 1 gold` reads one value; `peek wizard 1 books` reads the group; with no field it prints the record's known fields.
The wizard number is the human one (1 is the player), as on Mirror's `/wizard/:id` page.

## Definition of done

Unit tests on the table's decoding (every type, a record in the middle of the table, a bad name); one run against the real game, compared with the game's own screen.
