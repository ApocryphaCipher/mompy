<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# mompy: what you can type

Tables of the options of `mompy peek`, `poke` and friends, one page per kind of record. They are generated from the field table, so they match the program.

## Look something up

| I want to know... | Where |
| --- | --- |
| The 24 global enchantments (`globals.<name>`) | [Wizard#elements-of-globals](Wizard.md#elements-of-globals) |
| The 18 retorts (`retorts.<name>`) | [Wizard#elements-of-retorts](Wizard.md#elements-of-retorts) |
| Spellbooks per realm (`books.<realm>`) | [Wizard#elements-of-books](Wizard.md#elements-of-books) |
| Spells: what `spells.<spell name>` takes (known, unknown...) | [Wizard#elements-of-spells](Wizard.md#elements-of-spells) |
| Relations and treaties with each wizard | [Wizard#elements-of-relations](Wizard.md#elements-of-relations) |
| The 32 unit enchantments (`unit cast mass.<name>`) | [Unit-enchantments](Unit-enchantments.md) |
| Weapon grades (`unit weapons <grade>`) | [Unit-enchantments#weapon-grades](Unit-enchantments.md#weapon-grades) |

## All the pages

| Page | Records |
| --- | --- |
| [Wizard](Wizard.md) | 5 |
| [City](City.md) | 100 |
| [Unit](Unit.md) | 1009 |
| [Node](Node.md) | 30 |
| [Lair](Lair.md) | 102 |
| [Fortress](Fortress.md) | 6 |
| [Unit enchantments and weapons](Unit-enchantments.md) | 32 enchantments, 4 weapon grades |

**How to write a value:** a number sets the field (`75`); a sign changes it (`+20`, `-5`); `to -50` sets a negative value; a word picks a named value (`alliance`, `known`, `on`).
A name from the game itself (a spell, a unit) is written where a table says `<spell name>` or `<unit name>`; mompy reads those names from your running game, so they are not listed here.

[Back to the README](https://github.com/ApocryphaCipher/mompy#readme)
