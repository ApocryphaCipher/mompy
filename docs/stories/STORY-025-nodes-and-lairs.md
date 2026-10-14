# STORY-025: `peek` and `poke` for magic nodes and lairs, with their monsters (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), read on a real game; one write-and-undo round trip made live; **whether the game honours each edit is not re-checked here** (it rests on Mirror's checks, below)
**Size:** medium
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("units first, then nodes and lairs. note on nodes, lairs and other monster inhabited places: we should def get the monster table when peeking at them")

## Outcome

Two blocks in the field table, numbered from 0 as the game does:

- `node` (30 records of 48 bytes): x, y, plane, **owner** (-1 nobody; editable), power (aura tiles), type (Sorcery, Nature, Chaos), flags (guess, `--force`). `peek node N` also prints the node's **guardians**: they are not in the node's record but in the encounter of kind 1 to 3 at the same tile, so mompy finds it by position.
- `lair` (the 102 encounter records of 24 bytes: Towers of Wizardry, node guardians, caves, dungeons, ancient temples, abandoned keeps, monster lairs, ruins and fallen temples): x, y, plane, **intact** (cleared or not), kind, **two guard slots** (a unit type and a count byte), **gold** and **mana** rewards, spell code, flags, item count and the three item ids.

The **monster table**: a guard is a unit type (named from the game's own unit type table, `Sprites (180)`) and a count byte of two nibbles, the low one the guards **left**, the high one the number it **started** with (checked live, 2026-09-23: `0x88` became `0x80` as eight were beaten). `peek` prints them as `guard1_count = 1 left of 2 (0x21)`.

```
mompy peek lair 12                       # Cave, Myrror (8, 30), not cleared: guards, gold, mana
mompy peek node 3                        # the node, and "guardians (lair 7, not cleared): War Bears 3 of 3, Sprites 2 of 2"
mompy poke lair 12 gold 300
mompy poke lair 12 guard1_type sprites   # a unit type by name (ambiguous names list their types)
mompy poke lair 12 guard1_count 3        # 3 guards at full strength (0x33); 2/3 is two left of three; or a whole byte
mompy poke node 3 owner freya            # or nobody
mompy where 8,30,myrror                  # everything on a tile: city, units, node, and the monsters that live there
mompy where pointer                      # the same for the tile under the mouse
```

- Editable: lair `intact`, `guard1_type`, `guard1_count`, `guard2_type`, `guard2_count`, `gold` (0 to 30000), `mana`; node `owner`. These are the edits Mirror's panels make; Mirror checked them in the real game on 2026-10-12 (a keep set to 777 gold paid exactly that, a keep given one to six Sprites, a node given an owner kept it through End Turn). Everything else (position, kind, type, power, spell code, items) is read-only; node `flags` is a guess.
- A tower is two records (an Arcanus and a Myrror side) that the game clears together: clearing one by hand leaves the other; edit both.
- Cleared records keep their guard slots (a cleared lair still lists what it held).
- Read on the real game (fork 0.84.0-alpha): `peek lair 5` (a cleared tower: Night Stalker 0 of 3, Zombies 0 of 6, 140 mana), `peek lair 19` (Chaos node guardians: Efreet, Hell Hounds), `peek node 3` and `where 47,28,myrror` (a Sorcery node with Storm Giant 2 of 2, Phantom Beast 3 of 3 as guardians). Dry runs of the pokes, and one real write: `poke lair 13 gold 7` read back 7, `undo` put 0 back (the byte only: no reward was claimed).
- Tests: `tests/test_sites.py` (fake DOSBox). `where` now also takes `x,y,plane`.
- Not done: moving a node or lair (it is also a terrain tile: Mirror's `move_node` edits both); the rewards' items; the Towers of Wizardry block (6 towers x 4 bytes), whose address in memory was not looked for.
