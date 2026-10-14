# STORY-026: wizards by name, `relation tauron +20`: friendlier peek and poke (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), checked on a real game
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("`wizard Freya relation Tauron +/-20`")

## Outcome

```
mompy peek wizard freya relation tauron                # relations.Tauron = 23
mompy poke wizard freya relation tauron +20            # relations.Tauron: 23 -> 43  (and Tauron's view of Freya)
mompy poke wizard freya relation tauron -=5            # lower by 5
mompy poke wizard freya relation tauron -50            # set it to minus 50 (a plain negative number stays a number)
```

- **Wizards by name** wherever a wizard number goes (`peek`, `poke`, fortresses): any case, a unique prefix works, an ambiguous or unknown name lists the choices.
- **The element as a separate word**: `relation tauron` for `relations.tauron`, in `peek` and `poke`. The dotted form still works.
- **Field names**: the singular (`relation`, `global`, `retort`) and a unique prefix (`treaty` for `treaty_status`, `exp` for `experience`); an ambiguous one lists the fields.
- **Changes**: `+20` and `+=20` raise a number by 20, `-=20` lowers it (typed `-=20`; the command line turns it into something the argument parser will take). The change is taken from the **current** value in the game, checked against the field's range (out of range is refused with the old and the would-be value, never clamped), and goes through the same compare-and-swap, undo and mirrored write as any `poke`: `relations` change on **both** wizards' records. A plain `-20` still means the number minus 20, so nothing that worked before changed.
  Words, whole lists and fields with named values (treaties, spells) refuse a change: name one number.
- Real game (2026-10-14): `poke wizard freya relation tauron +5` took Freya's 23 to 28 and Tauron's view of Freya went 23 to 28 too; `undo` put both back.
- Tests: `tests/test_friendly.py`.
