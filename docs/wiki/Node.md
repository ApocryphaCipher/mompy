<!-- Generated from mompy/fields.toml by scripts/make_wiki.py. Do not edit by hand: change the field table and run the script. -->

# Node fields

Fields of a magic node (30 records; numbered from 0).

```
mompy peek node <number or name> [field[.element]]
mompy poke node <number or name> <field>[.<element>] <value>
```

| Field | Type | Values | Change it | Sure | What it is |
| --- | --- | --- | --- | --- | --- |
| `x` | u8 | a whole number from 0 to 59 | read-only | checked | Map column (a node is also a terrain tile; moving one means editing the terrain too, which mompy does not do). |
| `y` | u8 | a whole number from 0 to 39 | read-only | checked | Map row. |
| `plane` | u8 | one of: `Arcanus`, `Myrror` (or its number) | read-only | checked | 0 Arcanus, 1 Myrror. |
| `owner` | i8 | a wizard's name, `nobody`, or 0 to 4 | set it | checked | -1 nobody, else the wizard (0 is wizard 1) who melded it. A meld changes only this byte (live, 2026-09-23); a node given an owner kept it through End Turn (2026-10-12). Its guardians are a separate encounter: see `peek node N`. |
| `power` | u8 | a whole number | read-only | checked | The number of aura tiles it uses (5 to 20). |
| `type` | u8 | one of: `Sorcery`, `Nature`, `Chaos` (or its number) | read-only | checked | Type 0, 1 and 2 nodes stand on terrain tiles 168, 169 and 170. |
| `flags` | u8 | a whole number from 0 to 255 | set it (`75`), or change it by a sign (`+20`, `-5`) (a guess: needs `--force`) | guess | Bit 0x01 warped (checked 2026-10-12: a node given the flag loaded with it and its tile showed a distortion animation); 0x02 melded by a Guardian Spirit (seen on 2 owned nodes; its meaning is kazzmir's). |
