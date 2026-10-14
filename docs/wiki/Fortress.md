<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Fortress fields

Fields of a wizard's fortress (6 records; numbered 1 to 6 like the wizards (6 is the neutral player)).

```
mompy peek fortress <number or name> [field[.element]]
mompy poke fortress <number or name> <field>[.<element>] <value>
```

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `x` | u8 | a whole number from 0 to 59 | read-only | checked | Map column of the wizard's fortress (the tower, his capital). Same as the summoning circle's until that is moved. |
| `y` | u8 | a whole number from 0 to 39 | read-only | checked | Map row of the fortress. |
| `plane` | u8 | one of: `Arcanus`, `Myrror` (or its number) | read-only | checked | 0 Arcanus, 1 Myrror. |
| `active` | u8 | one of: `banished`, `in place` (or its number) | set it | checked | 0 means the wizard has lost his fortress: banished (he casts Spell of Return). The Magic screen draws him as a cracked stone frame: seen by changing this byte in a save and, live, in memory (2026-10-13; the first of the two copies is the one the game reads). |
