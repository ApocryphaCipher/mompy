<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Wizard fields

Fields of a wizard (5 records; wizard 1 is you; a name works too: `wizard freya`).

```
mompy peek wizard <number or name> [field[.element]]
mompy poke wizard <number or name> <field>[.<element>] <value>
```

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `name` | text[20] | text, up to 19 characters | set it | checked | Printable ASCII, 1 to 19 characters, NUL-padded to 20 bytes. |
| `banner` | u8 | one of: `blue`, `green`, `purple`, `red`, `yellow` (or its number) | read-only | checked | The wizard's flag colour. |
| `fame` | u16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | The base value. The Info screen shows it plus a bonus (77 shown as 90, 30000 as 30013). |
| `power_base` | u16 | a whole number | read-only (the game works it out again) | checked | Worked out again by the game; a write would be overwritten. |
| `ratios` | u8 x 3 | a whole number | read-only | guess | Percent split of the power base; they sum to 100. Only the skill slot's position was checked. |
| `summoning_circle` | i16 x 3 | a whole number | read-only | checked | Map position of the wizard's summoning circle; plane 0 Arcanus, 1 Myrror. |
| `research_candidates` | u16 x 8 | a `<spell name>` or its number; `none` for no spell | read-only | checked | Spell numbers the game offers to research next (0 = empty slot). |
| `skill_left` | u16 | a whole number | read-only (the game works it out again) | checked | Casting skill left this turn. |
| `casting_skill` | u16 | a whole number | read-only (the game works it out again) | checked | The nominal casting skill, 'Casting Skill: N(N)' on the Magic screen. |
| `tax_rate` | u16 | a whole number from 0 to 6 | read-only | checked | Index into the tax list: 0 is no tax, 6 is 3 gold per citizen. |
| `books` | i16 x 5 | a whole number from 0 to 13 | set an element (`75`), or change it by a sign (`+20`, `-5`); a whole array as `a,b,c` | checked | Spellbooks per realm. 13 in every realm was loaded and survived a turn. |
| `retorts` | u8 x 18 | `on` / `off` | set an element by its name | checked | 1 if the wizard has the retort. The save does not enforce the new-game rules. |
| `relations` | i8 x 6 | a whole number from -100 to 100 | set an element (`75`), or change it by a sign (`+20`, `-5`); a whole array as `a,b,c` | checked | How this wizard sees each other wizard (the Diplomacy screen's figure); the neutral player is last. The game keeps each pair on both wizards, so a write must change both. |
| `treaty_status` | u8 x 6 | one of: `none (peace)`, `wizard pact`, `alliance`, `war` (or its number) | set an element by its name | checked | Toward each other wizard; kept on both. Peace is just 0. |
| `research_left` | u16 | a whole number from 0 to 65535 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Research points left on the spell being researched. |
| `mana` | u16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Magic reserve. 30000 is the game's own cap. |
| `researching` | u16 | a `<spell name>` or its number; `none` for no spell | set it | checked | Spell number being researched, 0 for none. Set it only to one of research_candidates, or the Research page shows nothing. |
| `spells` | u8 x 214 | one of: `unknown`, `knowable`, `known`, `on the research list` (or its number) | one element at a time | checked | Spell n is byte n-1. Spells are learned without the matching books. |
| `gold` | u16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Treasury. 30000 is the game's own cap. |
| `globals` | u8 x 24 | `on` / `off` | set an element by its name | checked | 1 when this wizard has that global enchantment active. Real casts seen: bytes 3 (Aura of Majesty) and 18 (Just Cause). Set by hand and watched through an End Turn: Aura of Majesty, Wind Mastery, Nature's Wrath, Herb Mastery, Tranquility, Planar Seal, Meteor Storm, Great Wasting, Armageddon, Time Stop (docs/reference/globals.md). |

### `ratios.<element>`

`ratios.<name>` or `ratios.<number 1 to 3>`; a unique start of the name works.

| # | Name |
| --- | --- |
| 1 | research |
| 2 | mana |
| 3 | skill |

### `summoning_circle.<element>`

`summoning_circle.<name>` or `summoning_circle.<number 1 to 3>`; a unique start of the name works.

| # | Name |
| --- | --- |
| 1 | x |
| 2 | y |
| 3 | plane |

### `research_candidates.<element>`

8 values: `research_candidates.1` to `research_candidates.8`, or all of them as `a,b,c`.

### `books.<element>`

`books.<name>` or `books.<number 1 to 5>`; a unique start of the name works.

| # | Name |
| --- | --- |
| 1 | nature |
| 2 | sorcery |
| 3 | chaos |
| 4 | life |
| 5 | death |

Each takes a whole number from 0 to 13.

### `retorts.<element>`

`retorts.<name>` or `retorts.<number 1 to 18>`; a unique start of the name works.

| # | Name |
| --- | --- |
| 1 | Alchemy |
| 2 | Warlord |
| 3 | Chaos Mastery |
| 4 | Nature Mastery |
| 5 | Sorcery Mastery |
| 6 | Infernal Power |
| 7 | Divine Power |
| 8 | Sage Master |
| 9 | Channeler |
| 10 | Myrran |
| 11 | Archmage |
| 12 | Mana Focusing |
| 13 | Node Mastery |
| 14 | Famous |
| 15 | Runemaster |
| 16 | Conjurer |
| 17 | Charismatic |
| 18 | Artificer |

Each takes `on` / `off`.

### `relations.<element>`

One element per wizard: `relations.<wizard name>` (`mompy peek wizard 2 relations.tauron`), and the neutral player last. A wizard has none for himself.
A change is written on both wizards' records.

### `treaty_status.<element>`

One element per wizard: `treaty_status.<wizard name>` (`mompy peek wizard 2 treaty_status.tauron`), and the neutral player last. A wizard has none for himself.
A change is written on both wizards' records.

### `spells.<element>`

One element per spell: `spells.<spell name>` or `spells.<number 1 to 214>`. The name is the game's own, so it is not listed here: `mompy peek wizard 1 spells.<unique start of the name>` finds it, and an ambiguous start lists the matches.

| Value | Meaning |
| --- | --- |
| `0` | unknown |
| `1` | knowable |
| `2` | known |
| `3` | on the research list |

### `globals.<element>`

`globals.<name>` or `globals.<number 1 to 24>`; a unique start of the name works.

| # | Name |
| --- | --- |
| 1 | Eternal Night |
| 2 | Evil Omens |
| 3 | Zombie Mastery |
| 4 | Aura of Majesty |
| 5 | Wind Mastery |
| 6 | Suppress Magic |
| 7 | Time Stop |
| 8 | Nature Awareness |
| 9 | Nature's Wrath |
| 10 | Herb Mastery |
| 11 | Chaos Surge |
| 12 | Doom Mastery |
| 13 | Great Wasting |
| 14 | Meteor Storm |
| 15 | Armageddon |
| 16 | Tranquility |
| 17 | Life Force |
| 18 | Crusade |
| 19 | Just Cause |
| 20 | Holy Arms |
| 21 | Planar Seal |
| 22 | Charm of Life |
| 23 | Detect Magic |
| 24 | Awareness |

Each takes `on` / `off`.
