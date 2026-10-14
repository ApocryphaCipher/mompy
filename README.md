# mompy

Read and change a **running game of *Master of Magic*** from the command line.

```
mompy peek wizard freya relation tauron         # relations.Tauron = 23
mompy poke wizard 1 gold 30000                  # gold: 8293 -> 30000
mompy poke wizard freya relation tauron +20     # raise a relation by 20 (both wizards' records change)
mompy unit experience max --at pointer          # the stack under the mouse becomes Elite
mompy undo                                      # put the last change back
```

mompy talks to **DOSBox Staging's built-in web API**, which can read and write the emulated machine's memory while the game runs. It is a single Python package with **no dependencies**,
needs none of the game's files and ships none: only offsets, ranges and what has been checked about them. It is **alpha** software and it **writes into a running game**: try it on a spare save.

## Install

You need **Python 3.12 or newer**.

```
pipx install git+https://github.com/ApocryphaCipher/mompy        # or: pip install git+https://github.com/ApocryphaCipher/mompy
mompy --version
```

No installation is needed to try it from a checkout: `python -m mompy ...` in the repository folder does the same. In the examples below, `python -m mompy` and `mompy` are the same thing.

## Which DOSBox?

mompy needs **DOSBox Staging, version 0.83.0 or newer**: the ordinary release from the project's [releases page](https://github.com/dosbox-staging/dosbox-staging/releases).

- **Nothing to build, and no fork.** The web API is part of the released program; it is only switched off by default. This was checked with the released macOS build of 0.83.0 running the real game (and with the author's development build).
- **Other DOSBoxes do not work:** as far as we know the original DOSBox, DOSBox-X and the other variants have no such API. Older DOSBox Staging releases (before 0.83.0) were not checked; `mompy doctor` tells you the version it found and says `NOT READY` if there is no API to talk to.
- **The author's research fork** (`ApocryphaCipher/dosbox-staging`, branch `apocrypha/research`) is a development tool, not something you need: it adds screenshots, pausing and a write switch. If you do use it, it also needs `webserver_allow_writes = true` before it accepts a write; the released program has no such switch.
- Set DOSBox up for *Master of Magic* the way you always do (the game's folder mounted, the game run from it). mompy changes nothing about that.

## Quick start

1. **Start DOSBox Staging with its web API on**, and run the game from it as usual:

   ```
   dosbox --set webserver_enabled=true
   ```

   or put `webserver_enabled = true` in DOSBox's config file. The API listens on `127.0.0.1:8086` (`webserver_port` changes that; give mompy `--url http://127.0.0.1:PORT` to match).
2. **Load a saved game** in *Master of Magic* (1.31, the GOG release was used). mompy finds the game by looking for the five wizards' names, so a game must be loaded.
3. **Check it:**

   ```
   mompy doctor
   ```

   It reports whether the API answers, the memory can be read, the game's tables are found and look right, and a write is accepted (by writing back the byte that is already there). It ends with `READY`, `READ-ONLY` or `NOT READY`.
4. **Look, then change:** `mompy peek wizard 1`, `mompy fields`, `mompy poke wizard 1 gold 30000 --dry-run`.

**Safety:** every write is checked against the field's legal range, goes through a compare-and-swap (it is refused if the game changed the byte meanwhile), and is recorded so `mompy undo` can put it back. `--dry-run` says what would change and writes nothing.
mompy never saves your game for you: the changes live in the running game until *you* save from it. A hand edit can leave the game in a state it does not expect (a unit moved by hand is drawn in its old place until the map is nudged, for example), so **keep a copy of a save you care about before you save over it.**

**Platforms:** developed and checked on **macOS** with DOSBox Staging 0.84-alpha (a fork build) and the **0.83.0 release**. Windows and Linux builds of DOSBox Staging should behave the same, but they have **not been tried** (STORY-008). Python 3.14 was used for the tests; 3.12 is the stated minimum.

## The commands

`mompy --help` lists them. Every command that takes a place accepts the tile under the mouse (`pointer`), a city's name, or `x,y,plane`.

## `mompy peek` and `mompy fields`

```
python -m mompy peek wizard 1 gold          # gold = 30000
python -m mompy peek wizard 1 books         # books = nature 0, sorcery 12, chaos 0, life 3, death 0
python -m mompy peek wizard 1 relations.freya
python -m mompy peek wizard 2               # every field of wizard 2
python -m mompy fields                      # what mompy knows, the ranges, and how sure we are
```

`--json` prints plain data for scripts. Wizard 1 is the player. Read-only.

## `mompy poke` and `mompy undo`

```
python -m mompy poke wizard 1 gold 30000          # gold: 8293 -> 30000
python -m mompy poke wizard 1 books.sorcery 13
python -m mompy poke wizard 1 retorts.alchemy on
python -m mompy poke wizard 1 relations.freya 70  # a relation lives on both wizards: both are written, or neither
python -m mompy poke wizard 1 treaty_status.sharee alliance
python -m mompy poke wizard 1 gold 30000 --dry-run  # say what would change, write nothing
python -m mompy undo                              # put the last poke back
```

Every write is a compare-and-swap, every value is range-checked against the field table (`mompy fields`), and nothing is clamped silently. A field the game works out again
(power base...) or that mompy has not seen the game accept is refused. Needs the research fork's `webserver_allow_writes = true`; stock DOSBox Staging does not need it.
The undo log and the remembered game address live in `~/.mompy` (`MOMPY_HOME` to change it).

## `mompy poke ... cast`: a global enchantment, straight on a wizard

```
python -m mompy poke wizard 1 cast aura_of_majesty     # Aura of Majesty cast on wizard 1 (Jafar)
python -m mompy poke wizard 1 dispel aura_of_majesty   # ... dispelled
python -m mompy poke wizard 2 cast just_cause          # any wizard can be the caster; two wizards can hold the same one
python -m mompy peek wizard 1 globals                  # which ones are on
```

It sets the one byte the game keeps for that enchantment (the wizard is the caster). **No mana, no spell book, none of the game's casting checks**, and no waiting for End Turn: it is active now, and the game's own sums
(the effect, the upkeep, a dispel it cannot afford) happen at End Turn. The name can be spelled loosely (`aura`, `natures-wrath`, `globals.aura_of_majesty`). Planar Seal, Armageddon, Meteor Storm and Great Wasting were tried through a real End Turn and cast like any other. **Time Stop is not available**: the game does it with its own scripting when the real spell is cast, so cast it from your spell book. If the owner has no mana at End Turn the game disbands his summoned creatures and dissipates every unit enchantment. `mompy undo` takes the last one off.

## `mompy banish` and `mompy unbanish`

```
python -m mompy banish wizard 3        # wizard 3 (Sss'ra) is banished
python -m mompy unbanish wizard 3      # wizard 3 (Sss'ra): banishment lifted
python -m mompy banish wizard 1 --force   # the player: refused without --force
python -m mompy peek fortress 3        # the fortress record: where, and whether it is in place
python -m mompy banish wizard 3 --dead   # and finish him: cities to neutral, units and heroes gone, gold and mana 0
```

A banished wizard has lost his fortress: the Magic screen draws him as a cracked stone frame and, in the game's rules, he casts Spell of Return. He is **not dead**: he is only
eliminated if he has no cities left. `--dead` finishes the job the way the game leaves an eliminated wizard (one `undo`; the Magic screen then says "Shattered Gem": eliminated or banished). Plain `banish` is one byte (`active` of the fortress table), written like any `poke` (a compare-and-swap, logged for `mompy undo`).

## `mompy where`

```
python -m mompy where Blackstone    # Blackstone: Myrror (51, 22), owner Jafar, a size 3 of population 15
python -m mompy where freya         # Freya (wizard 2): summoning circle Arcanus (23, 25), the city Dover
python -m mompy where black         # several matches are listed, never guessed
python -m mompy where dover --json
```

Finds a city or a wizard by name, any case. A whole name wins; otherwise a unique prefix. Read-only. The coordinates are the ones Mirror's editors take
(tile x, tile y, plane). Population is in thousands, as the game keeps it; size classes above Village have not been named yet, so they print as `size N`.

## Cities: `peek city` and `poke city`

```
python -m mompy peek city darkmoor                    # name, position, plane, owner, population
python -m mompy poke city darkmoor population 25      # city Darkmoor population: 4 -> 25
python -m mompy undo
```

A city is named the way `where` names it (whole name, else a unique prefix; an ambiguous one is refused), or given by its number. Only `population` can be changed so far, in
thousands (1 to 25). The game also keeps the tens, which are left alone. Same safety as every `poke`: compare-and-swap, range checks, `--dry-run`, `undo`.

```
python -m mompy poke city blackstone build       # the building in production completes at End Turn
```

`build` fills the city's production store (`production_stored`) so that the building in production is finished at the next End Turn. It refuses a city making Housing or
Trade Goods (nothing to finish), and an item that is not a building unless `--force`. It does not know the cost, so it writes more than any building costs; `undo` puts the store back.

## Units: `cast unit`

```
python -m mompy poke wizard 1 cast unit.war_bears              # one War Bears at the wizard's summoning circle
python -m mompy poke wizard 1 cast unit.sprites --count 3 --at darkmoor
python -m mompy poke wizard 1 cast unit.58                     # a unit by type number
python -m mompy poke city blackstone create 60               # an ordinary unit (type 60), maxed out, made in a city
python -m mompy undo
```

Puts a unit straight into the game, owned by the wizard: no mana, no spell book, none of the game's checks. Unit names are read from the running game. A name several races share
(Swordsmen) lists its type numbers; use one. `cast` is for summoned creatures (Sprites, War Bears...); `poke city NAME create UNIT` is for ordinary units and boats: it makes them in that city for the city's owner, at maximum experience (120, Elite) and with adamantium weapons.
Heroes are refused (they also need a place in the wizard's hero list). A tile holds nine units of one owner, so a full or foreign tile
sends the unit to a free neighbouring tile, and it says so. `--at` takes a city name or `x,y,plane`. One `undo` takes the whole summon back.

## `mompy unit mercury`

```
python -m mompy unit mercury --at blackstone      # the stack on a city (or --at x,y,plane)
python -m mompy unit mercury --wizard 1           # every unit of wizard 1
python -m mompy undo
```

Gives the units 63.5 moves for this turn (the most the game's byte holds; a Cavalry set this way crossed most of a continent). Max moves is unchanged, so the next turn is normal again. `--dry-run` says what would change.

## The pointer, and `mompy pew`

```
python -m mompy where pointer             # Myrror (50, 18)  city Hellgate, owner Jafar  2 units: ...
python -m mompy pew pointer               # kill the units on the tile under the mouse (the city stays)
python -m mompy pew blackstone            # or by city name, or x,y,plane
python -m mompy unit mercury --at pointer
python -m mompy undo                      # brings them back, until End Turn sweeps them
```

`pointer` works anywhere a place does. The game keeps the pointer's position in its own memory, so nothing needs changing in DOSBox. It only means something over the overland map.
`pew` spares heroes (and says so). The map keeps drawing killed units as ghosts until you nudge the map view, flip the plane, or end the turn: do not give a ghost orders.

## Mass enchantments

```
python -m mompy poke city hellgate cast mass.flight      # every unit on Hellgate's tile
python -m mompy unit cast mass.flight --at pointer       # the stack under the mouse (or --at x,y,plane)
python -m mompy unit dispel mass.flight --at hellgate
python -m mompy undo
```

Puts one of the 32 unit enchantments (Flight, Wind Walking, Water Walking, Invisibility, Heroism, Bless...) on every unit on a tile, with no mana and no checks; `dispel` takes it off. The units' owner pays the upkeep at End Turn; if the wizard cannot, the game **disbands his summoned creatures** and dissipates the unit spells (below). Heroes on the tile are included. The map may need a nudge to redraw.

## `mompy snapshot` and `mompy diff`: what moved?

```
python -m mompy snapshot before
python -m mompy snapshot before2          # the same moment again: its differences from "before" are the game's own noise
# ... cast something, send gold, end the turn ...
python -m mompy snapshot after
python -m mompy diff before after --ignore before2
#   wizard 1 (Jafar) gold: 30000 -> 29950
#   wizard 1 (Jafar) globals.Aura of Majesty: 0 -> 1
#   unit 160 (type 179) moves_left: 4 -> 0
#   data segment +0x78c2: ...
```

A snapshot keeps the wizards, cities, units (and their count), nodes, lairs and fortresses, and the game's 64 KiB data segment, in `~/.mompy/snapshots/NAME.json` (116 KiB each). A diff names the field when it knows it and shows the raw offset when it does not.
It is how the pointer, the plane and the unit record were found. `mompy snapshot --list` lists them; they are never deleted for you.

## Spell names

```
python -m mompy peek wizard 1 researching               # researching = Enchant Item (207)
python -m mompy peek wizard 1 spells.time_stop          # spells.Time Stop = 2 (known)
python -m mompy poke wizard 1 spells.earth_lore known
python -m mompy poke wizard 1 researching vertigo       # or a number; "none" for nothing
```

The names come from the running game itself (it keeps the spell table in memory), so no game folder is needed and nothing is shipped. A partial name works when it is unique
(`vert`); an ambiguous one lists its matches. If the table cannot be found, everything works with numbers as before.

## Units: `peek unit` and `poke unit`

```
python -m mompy peek unit 158             # unit 158 (Halberdiers, neutral): x, y, owner, type, moves, level, experience, weapons, enchantments
python -m mompy poke unit 158 experience 120
python -m mompy poke unit 158 moves_left 127
python -m mompy fields unit               # what can be read and what can be changed
```

Units are numbered from 0, the way `where pointer` and `pew` print them (`Cavalry #158`). Position and a few other fields are guesses and need `--force`; owner and type are read-only.

## Nodes, lairs and their monsters

```
python -m mompy peek lair 12              # a cave: kind, where, the guards (Sprites 1 left of 2), gold and mana rewards
python -m mompy peek node 3               # a magic node, owner, and "guardians (lair 7, not cleared): War Bears 3 of 3, Sprites 2 of 2"
python -m mompy where pointer             # a tile in words: city, units, node, and the monsters that live there
python -m mompy where 8,30,myrror
python -m mompy poke lair 12 gold 300
python -m mompy poke lair 12 guard1_type sprites
python -m mompy poke lair 12 guard1_count 3     # three at full strength; 2/3 is two left of three
python -m mompy poke node 3 owner freya         # or nobody
```

"Lair" is any monster place: Towers of Wizardry, node guardians, caves, dungeons, temples, keeps and ruins (`peek lair N` says which). Numbers start at 0, the game's own.

## Friendlier forms: names and changes

```
python -m mompy peek wizard freya relation tauron        # wizards by name; the element as a separate word
python -m mompy poke wizard freya relation tauron +20    # raise by 20 (both wizards' records change)
python -m mompy poke wizard freya relation tauron -5     # lower by 5
python -m mompy poke wizard freya relation tauron 75     # set it to 75
python -m mompy poke wizard freya relation tauron to -50 # set it to minus 50
python -m mompy poke wizard jafar gold +1000
```

A sign means "change by"; no sign means "set it"; `to -50` sets a negative value (the shell zsh reads a word starting with `=` as a command, so `=-50` needs quotes). A change is worked out from the value in the game and refused if the result would leave the field's range. Field names may be singular or a unique prefix (`treaty`).

## Stacks: heal, weapons, maximum experience

```
python -m mompy unit heal --at pointer                     # damage to 0, heroes included
python -m mompy unit weapons adamantium --at blackstone    # ordinary units only (not creatures, not heroes)
python -m mompy unit experience max --at pointer           # Elite (120; Ultra Elite for a Warlord's units) or, for heroes, Demi-God (1000): the game's own table
python -m mompy unit heal --at pointer --skip-heroes
```

The place is the tile under the mouse, a city's name, or `x,y,plane`. Each says how many units it changed and why it left the others. One `mompy undo` puts the stack back.

## `mompy doctor`

```
python -m mompy doctor            # or: mompy doctor, once installed;  --url http://127.0.0.1:8086 is the default
```

It checks, without changing the game, that DOSBox's web API answers (and which version), that the memory can be read, that the game's tables are
found and look right (their address depends on the DOSBox build, so they are *found*, not assumed), and that a write is accepted (by writing back the byte that is already there).
It ends with `READY`, `READ-ONLY` or `NOT READY`, and exits 0 only for `READY`.

## Layout

```
mompy/              this repository
  mompy/            the Python package (standard library only)
  tests/
  docs/             epics, stories, notes, reference, backlog (the project's tickets)
```

The game's own files stay in the player's install folder; the repository never contains them. To read DOSBox Staging's
source, clone [dosbox-staging/dosbox-staging](https://github.com/dosbox-staging/dosbox-staging) anywhere outside this folder.

Related: [Mirror](https://github.com/ApocryphaCipher/Mirror) edits *save files* (and holds the verified
research on the formats), and `gama` turns memory dumps into data.

## Licence

MIT: see [LICENSE](LICENSE). *Master of Magic* and its files belong to their owners; mompy contains none of them.
