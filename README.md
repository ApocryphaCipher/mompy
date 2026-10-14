# mompy

Change a running game of *Master of Magic* from the command line:

```
mompy peek wizard 1 gold
mompy poke wizard 1 gold 30000
```

mompy talks to **DOSBox Staging's built-in web API** (`webserver_enabled = true`), which can read
and write the emulated machine's memory. It needs no game files of its own and ships none: only
offsets, ranges and what we have checked about them.

**Status: just started.** `mompy doctor` exists (below); `peek`, `fields`, `poke`, `undo`, `banish`, `unbanish`, and `cast`/`dispel` (a global enchantment), `where`, `poke city` (population, build, create) `cast unit`, `unit mercury`, `where pointer`, `pew` and mass enchantments exist too (see `docs/stories/`).
Nothing here has been tried on anyone's machine but Kevin's.

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
(the effect, the upkeep, a dispel it cannot afford) happen at End Turn. The name can be spelled loosely (`aura`, `natures-wrath`, `globals.aura_of_majesty`). Five enchantments that change how turns or the whole map work
(Time Stop, Planar Seal, Armageddon, Meteor Storm, Great Wasting) need `--force` to cast; they have not been tried by hand yet. `mompy undo` takes the last one off.

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

Puts one of the 32 unit enchantments (Flight, Wind Walking, Water Walking, Invisibility, Heroism, Bless...) on every unit on a tile, with no mana and no checks; `dispel` takes it off. The units' owner pays the upkeep at End Turn:
four Flying Nagas cost about 16 mana. Heroes on the tile are included. The map may need a nudge to redraw.

## `mompy doctor`

```
python -m mompy doctor            # or: mompy doctor, once installed;  --url http://127.0.0.1:8086 is the default
```

It checks, without changing the game, that DOSBox's web API answers (and which version), that the memory can be read, that the game's tables are
found and look right (their address depends on the DOSBox build, so they are *found*, not assumed), and that a write is accepted (by writing back the byte that is already there).
It ends with `READY`, `READ-ONLY` or `NOT READY`, and exits 0 only for `READY`.

## What it will need

- DOSBox Staging with its web API on (`webserver_enabled = true`) running *Master of Magic* 1.31. Developed against **0.84-alpha** (Kevin's research fork);
  the 0.83.0 release works too (checked), and `doctor` recognises both. A fork build also needs `webserver_allow_writes = true` before it accepts a write; stock DOSBox Staging does not.
- Python 3.12 or newer. No other packages.

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
