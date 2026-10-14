# Where Master of Magic keeps its tables in DOSBox's memory

**Source:** `gama`'s `layout.py` (the addresses), which found them with the memory API; Mirror's
`docs/reference/live-ram-map.md` and `save-to-ram-map.md` (how each was checked). The game is **Master of Magic 1.31, GOG release**, run in DOSBox
Staging with the usual config. The game's data segment is `0x289F0` (SS = `0x289F`).

**Caveat:** the addresses held across two launches with the same DOSBox setup. They belong to **one game executable *and one DOSBox setup*:** in the released DOSBox Staging 0.83.0 with its default config the same game's tables were all **`0x520` lower** (the wizard table at `0x3239A`; checked 2026-10-13, see [dosbox-api.md](dosbox-api.md)). **The cause is the DOSBox version, found 2026-10-13:** the stock 0.83.0 build puts the table at `0x3239A` both with defaults and with Kevin's config file, and Kevin's research fork (a 0.84-alpha snapshot) puts it at `0x328BA` both with defaults and with that config. DOSBox Staging's `main` added **DOS `STACKS`** support (`src/dos/dos_stacks.cpp`, commit `ba118457b`, 2026-04-28; the `stacks = auto` setting, absent from the v0.83.0 tag) which allocates a block when DOS starts: two interrupt wrappers (2 × 0x20), a 9-entry table (9 × 8) and 9 stacks of 128 bytes = 1288 bytes, rounded up to **81 paragraphs, plus the one paragraph of memory-block header** DOS puts before any allocation = **82 paragraphs = 0x520 bytes**, exactly the measured shift. Everything the game loads afterwards sits that much higher. In a 0.84-or-later DOSBox a different `stacks` setting changes the shift again. Another game release will
differ too. The tables below are therefore the **research setup's**; `doctor` finds the wizard table by scanning and applies the same shift to the rest, then checks that each table *looks right* (names printable at the record stride, counts in range) before anything is written (STORY-001).

## Tables (linear addresses, one record after another)

| Table | Address | Record size | Count |
| --- | --- | --- | --- |
| wizards | `0x328BA` | `0x4C8` | 5 (the neutral player's sixth record is not at this address) |
| cities | `0x6F980` | 114 | 100 |
| units | `0x7E060` | 32 | 1009 (the live count is a u16 at `0x34782`) |
| magic nodes | `0x85FE0` | 48 | 30 |
| lairs / encounters | `0x86660` | 24 | 102 |
| fortresses | `0x865C0` | 4 | 6 (the five wizards, then the neutral player) |
| terrain | `0x72630` | u16 per tile | 2 planes × 60 × 40 |
| terrain flags / landmass / minerals / explored | `0x773A0` / `0x74DC0` / `0x760B0` / `0x78690` | 1 byte per tile | 2 planes × 2400 |

**Located 2026-10-13:** the fortress table (see below). **Not located in RAM yet:** the fortress block's neighbours, the item block and the lair block. *Old note:* the fortress block (whose "active" byte is the *banished* flag; it is at save offset `0x65F8`), the item block and the lair block. STORY-006 finds them.

## The screen: the pointer, the map view, the plane (found 2026-10-13, STORY-010)

All in the game's data segment (DGROUP, the wizard table's address minus `0x9ECA`; `0x289F0` in the research setup).

| What | DGROUP + | Type | How it was checked |
| --- | --- | --- | --- |
| the pointer's position on the 320 x 200 screen | `0x78C2` | u16 x, u16 y | one candidate in the whole 64 KiB: (0, 0) with the pointer in the top-left corner and (319, 199) in the bottom-right, (150, 100) near the middle |
| the world tile at the map view's top-left | `0x6FFE` | u16 x, u16 y | pointer on Blackstone gave origin (45, 17); after scrolling the map, every copy of (45, 17) became (42, 18) together; Mirror's live-ram-map.md had the same address independently |
| the plane being viewed | `0xBD86` | u16, 0 Arcanus, 1 Myrror | 0 and 1 followed the Plane button in four flips; four byte candidates survived and Mirror's live-ram-map.md names RAM `0x34776`, which is this one |

**Tile under the pointer:** column = pointer x / 20, row = (pointer y - 20) / 18, then tile = (origin x + column, origin y + row), x wrapping at 60. The visible map is 12 x 10 tiles from screen row 20. **Checked:** the pointer on Hellgate's tile gave (50, 18) from memory alone and the game's city list has Hellgate there (Kevin confirmed it was Hellgate).
The pointer is meaningful only over the map: x < 240 and y from 20 to 199.

**The unit's stack picture:** the game draws stacks from a picture it builds earlier, not from the unit records, so a record marked dead (`pew`) keeps being drawn as a *ghost* (the unit's icon with no banner, clickable) until the map view is nudged, the plane flipped, or End Turn. Checked live.

## In a wizard record (offsets from the start of the record; all **checked** in the real game, see Mirror's `docs/reference/wizard-record-and-exploration.md`)

| Field | Offset | Type | Range we have seen the game accept |
| --- | --- | --- | --- |
| name | `+0x01` | 20 bytes, NUL-padded | printable ASCII, 1 to 19 characters |
| fame | `+0x24` | u16 | to 30000 (the Info screen shows it plus a bonus: 77 shows as 90) |
| books (Nature, Sorcery, Chaos, Life, Death) | `+0x5A` | 5 × i16 | 0 to 13 each |
| retorts | `+0x64` | 18 × u8 | 0 or 1 |
| research points left | `+0x25A` | u16 | |
| mana | `+0x25C` | u16 | to 30000 |
| spell being researched | `+0x262` | u16 | only one of the eight candidates at `+0x34`, or the Research page shows nothing |
| spell library | `+0x264` | 214 × u8 | 0 unknown, 1 knowable, 2 known, 3 on the research list |
| gold | `+0x356` | u16 | to 30000 |
| visible relations | `+0x128 + 42 + other` | i8 | −100 to 100 (written on **both** wizards) |
| treaty status | `+0x128 + 48 + other` | u8 | 0 none (peace), 1 wizard pact, 2 alliance, 3 war |
| global enchantments | `+0x482` | 24 × u8 | 1 when active; byte 3 Aura of Majesty and 18 Just Cause seen set |

## What a write does not do

- **Derived values** (power base, casting skill, a unit's level) are worked out again by the game, at a load or at End Turn.
- **A spell is cast at End Turn**, not when it is chosen; setting a global by hand may skip the cost and the upkeep (STORY-006 tests it).
- A unit moved by writing its position vanished from the map until the turn ended (research fork notes, 2026-09-23).
- Saving the running game writes what is in memory, so a write is kept only if the player then saves.

## The fortress table (found 2026-10-13, STORY-017)

Six records of `x, y, plane, active` at `0x865C0` in the research setup (`+0x53D06` from the wizard table). Found by searching all of memory for the five wizards' summoning-circle positions followed by an unknown byte: it matched the sequence
`(51,22,1,1) (23,25,0,1) (39,20,1,1) (33,9,0,1) (43,26,0,1) (49,8,0,1)` (the last is the neutral player's). The game keeps **two copies**, `0x865C0` and `0x875F0` (`0x1030` apart, the same gap as the node table's two copies);
**the first is the one the game reads**: clearing its `active` byte for Freya made the Magic screen draw her as a cracked stone frame at once, and `unbanish` made it normal again (Kevin looked, both times).
`active` 0 is *banished*: a wizard who has lost his fortress, who then casts Spell of Return (`MMOMS.TXT` section 5.3), not necessarily dead. The relative offset is assumed to hold on other DOSBox builds as the other tables' did (checked for the 0.83 shift, not for this table).
