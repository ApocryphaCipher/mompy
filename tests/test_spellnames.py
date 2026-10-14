import contextlib
import io
import json

from mompy import layout, spellnames
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.game import connect
from mompy.peek import peek
from mompy.poke import PokeError, poke

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory, put_field

BASE = layout.REFERENCE_WIZARD_BASE
SPELLS = {1: "Earth to Mud", 10: "Earth Lore", 11: "Earthquake", 53: "Vertigo", 59: "Aura of Majesty", 80: "Time Stop", 207: "Enchant Item"}


def put_spell_table(mem, at=None):
    """215 records of 36 bytes: the name, and a realm byte at +23 (0 to 5), as the game keeps SPELLDAT.LBX in memory."""
    at = BASE + spellnames.EXPECTED_FROM_WIZARDS if at is None else at
    for i in range(spellnames.COUNT):
        name = "None" if i == 0 else SPELLS.get(i, f"Spell {i}")
        rec = name.encode().ljust(18, b"\0") + bytes(18)
        mem[at + i * 36:at + i * 36 + 36] = rec[:23] + bytes([i % 6]) + rec[24:]


class SpellCase(HomeTestCase):
    def serve(self, mem):
        server = FakeDosbox(mem)
        server.__enter__()
        self.addCleanup(server.__exit__)
        self.server = server
        self.api = DosboxApi(server.url)


class ReadTest(SpellCase):
    def test_the_names_are_read_from_where_the_table_should_be(self):
        mem = game_memory()
        put_spell_table(mem)
        self.serve(mem)
        names = connect(self.api).names
        self.assertEqual(names.spells[10], "Earth Lore")
        self.assertEqual(len(names.spells), 215)
        self.assertEqual(list(names), ["Jafar", "Freya", "Sss'ra", "Sharee", "Tauron"])   # still the wizards' names

    def test_a_table_somewhere_else_is_found_by_searching(self):
        mem = game_memory()
        put_spell_table(mem, at=0xA00000)
        self.serve(mem)
        self.assertEqual(connect(self.api).names.spells[80], "Time Stop")

    def test_no_table_means_numbers_and_no_error(self):
        self.serve(game_memory())
        self.assertIsNone(connect(self.api).names.spells)

    def test_a_table_that_does_not_look_right_is_ignored(self):
        mem = game_memory()
        put_spell_table(mem)
        at = BASE + spellnames.EXPECTED_FROM_WIZARDS
        mem[at + 100 * 36:at + 100 * 36 + 4] = b"\x01\x02\x03\x04"                    # an unprintable name
        self.serve(mem)
        self.assertIsNone(connect(self.api).names.spells)

    def test_the_search_is_done_once_and_remembered(self):
        for mem in (game_memory(), None):
            if mem is None:                                                           # a game that does have a table, somewhere else
                mem = game_memory()
                put_spell_table(mem, at=0xA00000)
            self.serve(mem)
            connect(self.api)
            full = lambda: [r for r in self.server.requests if r[0] == "GET" and r[1].endswith(f"/{16 * 1024 * 1024}")]
            first = len(full())
            self.assertGreaterEqual(first, 1)                                         # the first command scans (the wizards, and the spells)
            connect(self.api)
            connect(self.api)
            self.assertEqual(len(full()), first, "a later command scanned all of memory again")
            self.server.__exit__()

    def test_find_by_name(self):
        names = ["None"] + [SPELLS.get(i, f"Spell {i}") for i in range(1, 215)]
        self.assertEqual(spellnames.find(names, "time_stop"), 80)
        self.assertEqual(spellnames.find(names, "Aura of Majesty"), 59)
        self.assertEqual(spellnames.find(names, "vert"), 53)
        with self.assertRaisesRegex(ValueError, "could be Earth to Mud, Earth Lore, Earthquake"):
            spellnames.find(names, "earth")
        with self.assertRaisesRegex(ValueError, "no spell is called 'zzz'"):
            spellnames.find(names, "zzz")
        with self.assertRaises(ValueError):
            spellnames.find(names, "none")                                              # record 0 is not a spell


class UseTest(SpellCase):
    def setUp(self):
        super().setUp()
        self.mem = game_memory()
        put_spell_table(self.mem)
        put_field(self.mem, BASE, "wizard", 1, "researching", 207)
        put_field(self.mem, BASE, "wizard", 1, "research_candidates", [207, 53, 0, 0, 0, 0, 0, 0])
        spells = [0] * 214
        spells[79] = 2                                                                  # Time Stop known
        put_field(self.mem, BASE, "wizard", 1, "spells", spells)
        self.serve(self.mem)

    def test_peek_shows_spell_names(self):
        self.assertEqual(peek(self.api, "wizard", 1, "researching"), "researching = Enchant Item (207)")
        self.assertEqual(peek(self.api, "wizard", 1, "research_candidates"),
                         "research_candidates = Enchant Item (207), Vertigo (53), none, none, none, none, none, none")
        self.assertEqual(peek(self.api, "wizard", 1, "spells.time_stop"), "spells.Time Stop = 2 (known)")
        self.assertEqual(peek(self.api, "wizard", 1, "spells.80"), "spells.Time Stop = 2 (known)")

    def test_poke_by_name(self):
        self.assertEqual(poke(self.api, 1, "spells.earth_lore", "known"), "spells.Earth Lore: unknown -> known")
        self.assertEqual(self.mem[BASE + 0x264 + 9], 2)
        self.assertEqual(poke(self.api, 1, "researching", "vertigo"), "researching: Enchant Item (207) -> Vertigo (53)")
        self.assertEqual(poke(self.api, 1, "researching", "none"), "researching: Vertigo (53) -> none")
        self.assertEqual(poke(self.api, 1, "researching", "12"), "researching: none -> Spell 12 (12)")      # numbers still work

    def test_bad_names_write_nothing(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "could be Earth to Mud"):
            poke(self.api, 1, "spells.earth", "known")
        with self.assertRaisesRegex(PokeError, "no spell is called 'zzz'"):
            poke(self.api, 1, "researching", "zzz")
        self.assertEqual(bytes(self.mem), before)

    def test_json_keys_use_the_names(self):
        data = json.loads(peek(self.api, "wizard", 1, None, as_json=True))["fields"]["spells"]
        self.assertEqual(data["Time Stop"], 2)

    def test_the_command(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["peek", "wizard", "1", "spells.time_stop", "--url", self.server.url]), 0)
            self.assertEqual(main(["peek", "wizard", "1", "spells.zzz", "--url", self.server.url]), 1)
        self.assertIn("spells.Time Stop = 2 (known)", out.getvalue())


class WithoutTheTableTest(SpellCase):
    def test_everything_still_works_with_numbers(self):
        mem = game_memory()
        put_field(mem, BASE, "wizard", 1, "researching", 207)
        self.serve(mem)
        self.assertEqual(peek(self.api, "wizard", 1, "researching"), "researching = 207")
        self.assertEqual(poke(self.api, 1, "researching", "53"), "researching: 207 -> 53")
        self.assertEqual(peek(self.api, "wizard", 1, "spells.80"), "spells.80 = 0 (unknown)")
        with self.assertRaisesRegex(PokeError, "whole number"):
            poke(self.api, 1, "researching", "vertigo")                                # no names known: the old message
