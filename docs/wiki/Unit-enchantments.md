<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Unit enchantments and weapons

For `mompy unit cast mass.<name> --at <place>` and `unit dispel mass.<name>`: one of these on every unit on a tile. A unique start of the name works.

| Name | Bit |
| --- | --- |
| Immolation | `0x00000001` |
| Guardian Wind | `0x00000002` |
| Berserk | `0x00000004` |
| Cloak of Fear | `0x00000008` |
| Black Channels | `0x00000010` |
| Wraith Form | `0x00000020` |
| Regeneration | `0x00000040` |
| Path Finding | `0x00000080` |
| Water Walking | `0x00000100` |
| Resist Elements | `0x00000200` |
| Elemental Armor | `0x00000400` |
| Stone Skin | `0x00000800` |
| Iron Skin | `0x00001000` |
| Endurance | `0x00002000` |
| Spell Lock | `0x00004000` |
| Invisibility | `0x00008000` |
| Wind Walking | `0x00010000` |
| Flight | `0x00020000` |
| Resist Magic | `0x00040000` |
| Magic Immunity | `0x00080000` |
| Flame Blade | `0x00100000` |
| Eldritch Weapon | `0x00200000` |
| True Sight | `0x00400000` |
| Holy Weapon | `0x00800000` |
| Heroism | `0x01000000` |
| Bless | `0x02000000` |
| Lionheart | `0x04000000` |
| Giant Strength | `0x08000000` |
| Planar Travel | `0x10000000` |
| Holy Armor | `0x20000000` |
| Righteousness | `0x40000000` |
| Invulnerability | `0x80000000` |

## Weapon grades

For `mompy unit weapons <grade> --at <place>` (ordinary units only): `normal`, `magic`, `mithril`, `adamantium` (or 0 to 3).
