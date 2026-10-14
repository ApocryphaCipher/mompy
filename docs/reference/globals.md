# The 24 global enchantments, set by hand

`mompy poke wizard N cast NAME` writes one byte of the wizard's `globals` array. This table records what the game does with each one when it was set that way. Order and names: MMOMS.TXT A.3 (the manual) as in `mompy/fields.toml`. Work in progress: STORY-013 (the harmless ones) and STORY-014 (the five that change how turns or the map work).

**Batch 1, 2026-10-13/14 (Kevin's game, fork 0.84.0-alpha, writes on, mana 30000):** Wind Mastery, Nature's Wrath, Herb Mastery and Tranquility cast together, one End Turn. All four appeared in the Magic screen's "Overland Enchantments" box under their names at once, and were still there after the turn. Mana went 30000 to 29982. The **sidebar's mana per turn read -18 with the four on and -1 after dispelling them**: the four cost **17 mana a turn together**, charged by the game for flags set by hand, shown the moment the flag changes (no End Turn needed to see it). Effects were not looked at (nothing was diffed that could be told apart from the AIs' own turn); *per-spell costs are not separated yet.*

| # | Enchantment | Shows in the Magic screen | Survives End Turn | Effect seen | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Eternal Night | not tried | | | |
| 2 | Evil Omens | not tried | | | |
| 3 | Zombie Mastery | not tried | | | |
| 4 | Aura of Majesty | yes | yes | relations rose each turn (Freya 0 to 2, Sharee and Tauron -20 to -16); 9 mana a turn is probably this one (STORY-012) | seen |
| 5 | Wind Mastery | yes | yes | not looked for | in the 17 mana batch |
| 6 | Suppress Magic | not tried | | | |
| 7 | Time Stop | not tried | | | |
| 8 | Nature Awareness | not tried | | | |
| 9 | Nature's Wrath | yes | yes | not looked for | in the 17 mana batch |
| 10 | Herb Mastery | yes | yes | not looked for | in the 17 mana batch |
| 11 | Chaos Surge | not tried | | | |
| 12 | Doom Mastery | not tried | | | |
| 13 | Great Wasting | not tried | | | |
| 14 | Meteor Storm | not tried | | | |
| 15 | Armageddon | not tried | | | |
| 16 | Tranquility | yes | yes | not looked for | in the 17 mana batch |
| 17 | Life Force | not tried | | | |
| 18 | Crusade | not tried | | | |
| 19 | Just Cause | yes | yes | not looked for | seen |
| 20 | Holy Arms | not tried | | | |
| 21 | Planar Seal | not tried | | | |
| 22 | Charm of Life | not tried | | | |
| 23 | Detect Magic | not tried | | | |
| 24 | Awareness | not tried | | | |

**Not tested:** what the game does with an unaffordable *global* upkeep (for *unit* enchantments it dissipates all of them and disbands the wizard's summoned creatures, STORY-023); a value other than 1 in the byte; what happens when two wizards hold the same global.
