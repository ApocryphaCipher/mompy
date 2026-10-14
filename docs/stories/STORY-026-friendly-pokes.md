# STORY-026: wizards by name, `relation tauron +20`: friendlier peek and poke (enhancement)

**Parent:** [EPIC-001](../epics/EPIC-001-mompy-core.md)
**Status:** built (2026-10-14), checked on a real game
**Size:** small
**Raised by:** [Kevin](https://github.com/KevinAsbury), 2026-10-14 ("`wizard Freya relation Tauron +/-20`")

## Outcome

```
mompy peek wizard freya relation tauron                # relations.Tauron = 23
mompy poke wizard freya relation tauron +20            # relations.Tauron: 23 -> 43  (and Tauron's view of Freya)
mompy poke wizard freya relation tauron -5             # lower by 5: 43 -> 38
mompy poke wizard freya relation tauron 75             # set it to 75
mompy poke wizard freya relation tauron to -50         # set it to minus 50
```

- **Wizards by name** wherever a wizard number goes (`peek`, `poke`, fortresses): any case, a unique prefix works, an ambiguous or unknown name lists the choices.
- **The element as a separate word**: `relation tauron` for `relations.tauron`, in `peek` and `poke`. The dotted form still works.
- **Field names**: the singular (`relation`, `global`, `retort`) and a unique prefix (`treaty` for `treaty_status`, `exp` for `experience`); an ambiguous one lists the fields.
- **Changes: a sign means "change by".** `+20` raises a number by 20 and `-20` lowers it by 20 (Kevin: "-5 should be decrease by five"; a first try with `-=5` was a trap nobody could remember). A number with **no sign sets it**: `75`. To set a **negative** value say `to -50`; `=-50` and `=75` also work but **zsh treats a word starting with `=` as a command lookup**, so they must be quoted (`'=-50'`), which is why the words are the way to remember. The change is taken from the **current** value in the game, checked against the field's range (out of range is refused with the old and would-be value, never clamped), and goes through the same compare-and-swap, undo and mirrored write as any `poke`: `relations` change on **both** wizards' records.
  Words, whole lists and fields with named values (treaties, spells) refuse a change: name one number. A name or other text that happens to start with a sign stays text.
  **This changed what a bare negative number means:** it used to set the field, so the older tests that used `-1` as an invalid value now use `=-1`.
- Real game (2026-10-14): `poke wizard freya relation tauron +5` took Freya's 23 to 28 and Tauron's view of Freya went 23 to 28 too; `-5` then lowered it again; `undo` put both back.
- Tests: `tests/test_friendly.py`.
