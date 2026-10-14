<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# City fields

Fields of a city (100 records; by name (`darkmoor`) or number from 1).

```
mompy peek city <number or name> [field[.element]]
mompy poke city <number or name> <field>[.<element>] <value>
```

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `name` | text[14] | text, up to 13 characters | read-only | checked | The city's name, NUL-padded; the game's own city list shows it. |
| `x` | u8 | a whole number from 0 to 59 | read-only | checked | Map column. |
| `y` | u8 | a whole number from 0 to 39 | read-only | checked | Map row. |
| `plane` | u8 | one of: `Arcanus`, `Myrror` (or its number) | read-only | checked | 0 Arcanus, 1 Myrror. |
| `owner` | u8 | a whole number from 0 to 5 | read-only | checked | Wizard record 0 to 4 (wizard 1 is 0), or 5 for neutral. Not editable: handing a city over also clears its enchantments and moves its units (Mirror's edit_city does all three). |
| `population` | u8 | a whole number from 1 to 25 | set it (`75`), or change it by a sign (`+20`, `-5`) | checked | Population in thousands: the city screen shows this times 1000 plus the tens at +24 (a live RAM write showed it). Only the thousands are written; the tens stay. 25 as the top is Mirror's guess at the game's cap. |
| `production` | u16 | a whole number | read-only | checked | The item in production, by the same ids as the buildings: 1 Trade Goods, 2 Housing, 3 to 35 buildings (29 Granary, 35 City Walls); larger numbers are units; 0xFFFC on cities that build nothing. Seen while the city screen said Producing Housing, Granary, then back (Mirror's live-ram-map.md). |
| `production_per_turn` | u8 | a whole number | read-only | checked | Hammers per turn; the city screen showed the same number. |
| `production_stored` | u16 | a whole number from 0 to 30000 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Production stored toward the item. The game itself set it to the full cost when a building was bought (0 -> 40, Granary) and to 0 when built; a hand-written value is not yet seen to complete the building. 30000 as the top is mompy's own safe limit (the field is a u16). |
