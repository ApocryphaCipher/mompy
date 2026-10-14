# Backlog

Unsorted ideas, not yet stories.

- ~~**Licence.**~~ MIT, decided 2026-10-14 (STORY-007).
- ~~**Bundle the spell names?**~~ Not needed: the names are read from the running game's own memory (STORY-005, 2026-10-14). Old text:  v1 reads them from the player's own `SPELLDAT.LBX` at run time (STORY-005). A packaged fallback list would work with no game folder; Mirror already ships unit and building names. (Kevin)
- **`mompy watch`**: poll a field and print changes, for finding what a screen reads.
- **Units and cities**: `poke unit 12 level 5`, `poke city Hamburg population 9`, using the same editors' limits as Mirror (`edit_units`, `edit_city`).
- ~~A second DOSBox fork~~: not possible (one fork per owner); done instead as branches on the existing fork (2026-10-13): `main` (upstream plus the small features), `feat/webserver-*` (one concern each, for upstream pull requests) and `apocrypha/research`.
- **Upstream pull requests to DOSBox Staging**: the write gate and the screenshot endpoint. Tracked in the DOSBox fork, not here.
