<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Lair fields

Fields of a monster place: a Tower of Wizardry, node guardians, cave, dungeon, temple, keep, ruins or lair (102 records; numbered from 0).

```
mompy peek lair <number or name> [field[.element]]
mompy poke lair <number or name> <field>[.<element>] <value>
```

**Element tables on this page:** [items](#elements-of-items)

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `x` | u8 | a whole number from 0 to 59 | read-only | checked | Map column. |
| `y` | u8 | a whole number from 0 to 39 | read-only | checked | Map row. |
| `plane` | u8 | one of: `Arcanus`, `Myrror` (or its number) | read-only | checked | 0 Arcanus, 1 Myrror. A tower stands on both planes, as two records. |
| `intact` | u8 | one of: `cleared`, `not cleared` (or its number) | set it | checked | 1 until the site is cleared. A tower is two records and the game clears both together. |
| `kind` | u8 | one of: `Tower of Wizardry`, `Chaos node guardians`, `Nature node guardians`, `Sorcery node guardians`, `Cave`, `Dungeon`, `Ancient temple`, `Abandoned keep`, `Monster lair`, `Ruins`, `Fallen temple` (or its number) | read-only | checked | What stands here. Node guardians (1 to 3) sit on a node of the matching type. |
| `guard1_type` | u8 | a `<unit name>` or its type number; `none` for no unit | set it | checked | The first kind of monster guarding it: a unit type (its name comes from the game's own table), 0 for none. Edited in the real game 2026-10-12 (a keep given one to six Sprites). |
| `guard1_count` | u8 | `3` (three at full strength), `2/3` (two left of three) or a whole byte | set it | checked | Two nibbles: the low one is the guards left, the high one the starting count (live, 2026-09-23: 0x88 became 0x80 as eight were beaten). Poke 3 for three at full strength (0x33), 2/3 for two left of three, or a whole byte. |
| `guard2_type` | u8 | a `<unit name>` or its type number; `none` for no unit | set it | checked | The second kind of monster, 0 for none. |
| `guard2_count` | u8 | `3` (three at full strength), `2/3` (two left of three) or a whole byte | set it | checked | As guard1_count. |
| `gold` | i16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | The gold reward (a keep set to 777 gold paid exactly that; the largest seen is 620). |
| `mana` | i16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | The mana reward (the largest seen is 330). |
| `spell_code` | u8 | a whole number | read-only | guess | 0 to 6 in every save; kazzmir's SpellSpecial. It does not decide the reward (the reward is rolled when the site is cleared). |
| `flags` | u8 | a whole number | read-only | guess | Who has looked at it (guess): 0x02 seen after Freya came near. |
| `item_count` | u8 | a whole number | read-only | checked | How many item rewards (0 to 3); 0 becomes 1 when an item is made at clearing. |
| `items` | i16 x 3 | a whole number; the elements: [Elements of items](#elements-of-items) | read-only | checked | Indexes into the item block; -1 or 0 for none. |

### Elements of items

3 values: `items.1` to `items.3`, or all of them as `a,b,c`.
