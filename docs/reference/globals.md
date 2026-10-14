# The 24 global enchantments, set by hand

`mompy poke wizard N cast NAME` writes one byte of the wizard's `globals` array. This table records what the game does with each one when it was set that way. Order and names: MMOMS.TXT A.3 (the manual) as in `mompy/fields.toml`. Work in progress: STORY-013 (the harmless ones) and STORY-014 (the five that change how turns or the map work).

**Batch 1, 2026-10-13/14 (Kevin's game, fork 0.84.0-alpha, writes on, mana 30000):** Wind Mastery, Nature's Wrath, Herb Mastery and Tranquility cast together, one End Turn. All four appeared in the Magic screen's "Overland Enchantments" box under their names at once, and were still there after the turn. Mana went 30000 to 29982. The **sidebar's mana per turn read -18 with the four on and -1 after dispelling them**: the four cost **17 mana a turn together**, charged by the game for flags set by hand, shown the moment the flag changes (no End Turn needed to see it). Effects were not looked at (nothing was diffed that could be told apart from the AIs' own turn); *per-spell costs are not separated yet.*

| # | Enchantment | Shows in the Magic screen | Survives End Turn | Effect seen | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Eternal Night | not tried | | | |
| 2 | Evil Omens | not tried | | | |
| 3 | Zombie Mastery | not tried | | | |
| 4 | Aura of Majesty | yes | yes | relations rose each turn (Freya 0 to 2, Sharee and Tauron -20 to -16); *guess:* the 9 mana a turn seen then is its upkeep (STORY-012) | seen |
| 5 | Wind Mastery | yes | yes | not looked for | in the 17 mana batch |
| 6 | Suppress Magic | not tried | | | |
| 7 | Time Stop | yes | yes | **none, over three End Turns: the other wizards, the cities and the units all moved as usual** | charged: mana fell about 104 more than usual in the turn. Needs `--force` in `cast` |
| 8 | Nature Awareness | not tried | | | |
| 9 | Nature's Wrath | yes | yes | not looked for | in the 17 mana batch |
| 10 | Herb Mastery | yes | yes | not looked for | in the 17 mana batch |
| 11 | Chaos Surge | not tried | | | |
| 12 | Doom Mastery | not tried | | | |
| 13 | Great Wasting | yes | yes | **four tiles got the corrupted flag `0x20`** in the turn's diff | batch 2 |
| 14 | Meteor Storm | yes | yes | **a volcano rose** (Kevin saw it; terrain type `0xB3` on several tiles in the diff) | batch 2 |
| 15 | Armageddon | yes | yes | no effect told apart from the other three | batch 2 |
| 16 | Tranquility | yes | yes | not looked for | in the 17 mana batch |
| 17 | Life Force | not tried | | | |
| 18 | Crusade | not tried | | | |
| 19 | Just Cause | not tried by hand | | | a real cast was seen (STORY-012) |
| 20 | Holy Arms | not tried | | | |
| 21 | Planar Seal | yes | yes | not looked for | sidebar mana -1 to -3: **2 mana a turn** |
| 22 | Charm of Life | not tried | | | |
| 23 | Detect Magic | not tried | | | |
| 24 | Awareness | not tried | | | |

**Batch 2, 2026-10-14 (the "wonky" ones, STORY-014; Kevin: "I know how the game handles them", so only the question that matters for mompy was asked: does the game survive it):**
Planar Seal, Meteor Storm, Great Wasting and Armageddon cast together, one End Turn: **no crash, no hang, nothing unexpected.** The map changed (nine tiles: a volcano, four corrupted tiles); the other wizards' relations with Jafar fell a little (Freya 0 to -4, Sharee -20 to -21: "concerned").
Time Stop then cast alone (the four dispelled first), one End Turn: **it showed and was charged, but did nothing:** all four other wizards, the cities and the units moved as normal. *Guess:* the game's turn logic reads a variable of its own (who holds time) that the flag alone does not set. Unexplored; not worth more unless someone wants the real effect.
Kevin's thought: it might only start at the next turn. **Tried again, flag on through two more End Turns:** the AI wizards still took both turns (117 diff lines on wizards 2 to 5: research, gold, treaties moved), and mana fell 318 over the two turns, so it is charged every turn and still does nothing.
`mompy cast` now asks for `--force` only for Time Stop.

**The real Time Stop (2026-10-14).** Kevin cast the real spell (Jafar already had it: spell 80, Sorcery, casting cost 1500; Mirror's spell numbering, from `SPELLDAT.LBX`). It sets the **same** global byte (index 7) as `mompy cast`, and yet behaves differently:
- the sidebar showed **-200 mana** at once, against about -106 for the hand-set flag; **gold and food income read 0**;
- **Next Turn did not end the turn**: "turns are working for me and not wizards" (Kevin): each press costs the caster 200 mana (28976 to 28776 in one press) and the turn comes straight back;
- the AI wizards' own records did not move (5 changed lines, all a per-turn history byte at `+0x386`) and the cities changed 4 lines, against about 120 and 100 on a normal turn; **but many units of every owner moved or changed orders** (57 neutral, about 27 of the AIs', 15 of Jafar's): not understood; Kevin knows the game better here.
- The wizard record holds nothing that tells a hand-set flag from a real cast (the bytes that differed are a per-turn history and the usual turn changes), so the game keeps the "time is stopped" state somewhere else: *guess:* a variable in the data segment naming whose time it is. Not found.
- A mistake caught on the way: a first comparison used `--ignore` with a snapshot from several turns earlier, which hides every change since as "noise" and made the freeze look total (4 AI lines). `diff --ignore` now refuses a snapshot taken more than 60 seconds from the first.

**Not tested:** what the game does with an unaffordable *global* upkeep (for *unit* enchantments it dissipates all of them and disbands the wizard's summoned creatures, STORY-023); a value other than 1 in the byte; what happens when two wizards hold the same global; **Spell of Mastery** (not one of the 24: probably the wizard record's `+0x22`, and winning the game is not something to try on a game anyone cares about).
