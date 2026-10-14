<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Unit fields

Fields of a unit (1009 records; numbered from 0, as `where pointer` and `pew` print them (`Cavalry #158`)).

```
mompy peek unit <number or name> [field[.element]]
mompy poke unit <number or name> <field>[.<element>] <value>
```

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `x` | u8 | a whole number from 0 to 59 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Map column. Writing it moves the unit, but the map draws from a picture built earlier: nudge the map view (or end the turn) to see it, and until then the unit may seem to vanish. |
| `y` | u8 | a whole number from 0 to 39 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Map row. See x. |
| `plane` | u8 | one of: `Arcanus`, `Myrror` (or its number) | set it (a guess: needs `--force`) | guess | 0 Arcanus, 1 Myrror. 255 marks a dead unit (with owner 255); `pew` writes that. See x. |
| `owner` | u8 | a wizard (read-only) | read-only | checked | Wizard record 0 to 4 (wizard 1 is 0), 5 neutral, 255 dead. Not editable: a unit also belongs to a stack and a banner. |
| `max_moves` | i8 | a whole number from 0 to 127 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Moves per turn, in half-moves; from the unit type's record (type byte +9) when the unit is made. The game fills moves_left from it each turn. |
| `type` | u8 | a `<unit name>` or its type number; `none` for no unit | read-only | checked | Index into the game's unit type table (names come from the game's memory). 0 to 34 heroes, 35 to 153 ordinary units and boats, 154 to 197 summoned creatures. |
| `hero_slot` | i8 | a whole number from -1 to 5 | read-only | checked | Index into the wizard's hero list for a hero, -1 for any other unit. |
| `moves_left` | i8 | a whole number from 0 to 127 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Half-moves left this turn: a signed byte, 127 is the top (63.5 moves; `mompy unit mercury`). Checked live: 20 showed 10 moves, 127 showed 63.5. |
| `status` | u8 | a whole number | read-only | guess | What the unit is doing. Seen: 1 and 3 (on its way somewhere); the rest is not decoded. |
| `level` | u8 | a whole number from 0 to 8 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Experience level: 0 Recruit, 1 Regular, 2 Veteran, 3 Elite (units 0 to 5, heroes 0 to 8). The game shows it as written, then works it out again from experience at End Turn: set experience too if it must stay. |
| `experience` | i16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Experience points. A normal unit is capped at 120 (Elite) at End Turn; `create` writes 120 and the unit screen showed Elite 120ep. |
| `damage` | u8 | a whole number from 0 to 255 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Damage taken (hits); 0 is unhurt. Nature's Cures sets this and only this to 0 (ReMoM). |
| `sight` | u8 | a whole number | read-only | checked | Sight range, from the unit type's record (type byte +19); 160 of 160 units agreed. |
| `mutations` | u8 | a whole number from 0 to 255 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | The low two bits are the weapon grade (0 normal, 1 magic, 2 mithril, 3 adamantium: seen on a unit screen, 2026-10-13); the high bits are mutation flags (undead 0x20, demon wings, ...). `create` writes 3. |
| `enchantments` | u32 | a whole number | read-only | checked | The unit's enchantments as bits (Flight 0x20000...). Not editable here: `mompy unit cast mass.NAME` does it for a stack. |
