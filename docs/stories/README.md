# Stories

| Story | Title | State |
| --- | --- | --- |
| [STORY-008](STORY-008-stock-dosbox.md) | Works with released DOSBox Staging | macOS done; Windows and Linux to do |
| [STORY-001](STORY-001-doctor.md) | `doctor` | done |
| [STORY-002](STORY-002-field-table-and-peek.md) | The field table and `peek` | done |
| [STORY-003](STORY-003-poke.md) | `poke`, safely | done |
| [STORY-004](STORY-004-snapshot-and-diff.md) | `snapshot` and `diff` | built; real game: a mana change found by name |
| [STORY-005](STORY-005-spell-names.md) | Spell names, read from the running game | built; real game: names found in memory, nothing shipped |
| [STORY-006](STORY-006-more-fields.md) | Relations, globals, banished; find the missing blocks | proposed |
| [STORY-007](STORY-007-packaging.md) | Install, README, licence | proposed |
| [STORY-009](STORY-009-dosbox-memory-map-endpoint.md) | Ask DOSBox where the game was loaded | proposed (nice to have) |
| [STORY-010](STORY-010-where.md) | `mompy where`: the tile under the mouse | built; the game keeps the pointer in its own memory |
| [STORY-011](STORY-011-where-name.md) | `mompy where <name>`: find a city or wizard by name | built (2026-10-13), PR open; checked on a real game |
| [STORY-012](STORY-012-cast.md) | `poke ... cast <global>`: a global enchantment straight on the wizard | built; real game: shows in the Magic screen and acts at End Turn |
| [STORY-013](STORY-013-spike-globals-by-hand.md) | Spike: what does the game do with a global set by hand? | partly: 10 of 24 tried; Kevin: no need for the rest |
| [STORY-014](STORY-014-spike-wonky-globals.md) | Spike: the wonky globals (Spell of Mastery, Planar Seal...) | done for five: Time Stop is refused (the game scripts it), the other four cast plainly |
| [STORY-015](STORY-015-cast-unit.md) | `poke ... cast unit.<name>`: summon any unit, no fuss | built; real game: shows, walks, survives End Turn |
| [STORY-016](STORY-016-spike-summon-a-unit.md) | Spike: what the game writes when a unit is summoned | proposed (nice to have) |
| [STORY-017](STORY-017-banish.md) | `banish wizard N`: banish a wizard (`--dead` to finish them) | `banish`, `unbanish` and `--dead` done; a banished wizard who keeps his cities across a turn: not run |
| [STORY-018](STORY-018-pew.md) | `pew`: kill the units on a tile (pointer, a city, x,y,plane) | built; real game: units die, a ghost shows until the view is nudged; undo works |
| [STORY-019](STORY-019-poke-city.md) | `poke city <name> <field> <value>`: change a city by name (population first) | `population` built; real game: written, see the story |
| [STORY-020](STORY-020-poke-city-build.md) | `poke city <name> build`: finish the current production next turn | built; real game: the building stands after one End Turn |
| [STORY-021](STORY-021-mercury.md) | `unit mercury`: give a stack all the movement it needs | built; real game: 63.5 moves, crossed a continent |
| [STORY-022](STORY-022-spike-weapon-quality.md) | Spike: where does a unit's weapon quality (adamantine) live? | done: byte found in the vault, seen on the unit screen |
| [STORY-023](STORY-023-mass-spells.md) | `cast mass.<spell>`: a unit enchantment on a whole stack (by city name or `pointer`) | built; real game: Flight showed and worked; no mana: summoned creatures disbanded and unit spells dissipated |
| [STORY-024](STORY-024-unit-fields.md) | `peek unit N` / `poke unit N FIELD VALUE`: the unit record in the field table | built; real game: the record reads in words |
| [STORY-025](STORY-025-nodes-and-lairs.md) | `peek`/`poke` for magic nodes and lairs, with the monsters guarding them | built; real game: read, one write and undo; edits rest on Mirror's checks |
| [STORY-026](STORY-026-friendly-pokes.md) | wizards by name, `relation tauron +20`: friendlier peek and poke | built; real game: a relation raised on both wizards and undone |

Epic: [EPIC-001](../epics/EPIC-001-mompy-core.md).
