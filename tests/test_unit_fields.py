import contextlib
import io
import json
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.peek import PeekError, peek
from mompy.poke import PokeError, poke, undo

from .test_summon import SummonCase, unit_at


class UnitFieldCase(SummonCase):
    def setUp(self):
        super().setUp()
        at = unit_at(1)
        self.mem[at + 12] = 1                                       # level 1
        struct.pack_into("<h", self.mem, at + 14, 25)               # 25 experience
        self.mem[at + 8] = 2                                        # moves left

    def bytes_of(self, i):
        return bytes(self.mem[unit_at(i):unit_at(i) + 32])


class PeekUnitTest(UnitFieldCase):
    def test_the_whole_record_in_words(self):
        out = peek(self.api, "unit", 1, None)
        self.assertTrue(out.startswith("unit 1 (Swordsmen, Freya)"))
        for line in ("x = 6", "owner = Freya", "type = Swordsmen (40)", "level = 1", "experience = 25", "moves_left = 2",
                     "mutations = normal weapons (0)", "enchantments = none"):
            self.assertIn("  " + line, out)

    def test_one_field_and_json(self):
        self.assertEqual(peek(self.api, "unit", 1, "experience"), "experience = 25")
        data = json.loads(peek(self.api, "unit", 1, None, as_json=True))["fields"]
        self.assertEqual((data["x"], data["type"], data["experience"]), (6, 40, 25))

    def test_weapons_and_enchantments_have_words(self):
        self.mem[unit_at(0) + 23] = 0x21
        struct.pack_into("<I", self.mem, unit_at(0) + 24, 0x20000 | 0x8000)
        self.assertEqual(peek(self.api, "unit", 0, "mutations"), "mutations = magic weapons, undead (33)")
        self.assertEqual(peek(self.api, "unit", 0, "enchantments"), "enchantments = Invisibility, Flight")
        self.mem[unit_at(0) + 23] = 3
        self.assertEqual(peek(self.api, "unit", 0, "mutations"), "mutations = adamantium weapons (3)")

    def test_a_dead_unit_and_numbers_the_game_does_not_have(self):
        self.mem[unit_at(2) + 2] = 0xFF
        self.mem[unit_at(2) + 3] = 0xFF
        self.assertIn("unit 2 (Swordsmen, dead)", peek(self.api, "unit", 2, None))
        self.assertIn("owner = dead", peek(self.api, "unit", 2, "owner"))
        with self.assertRaisesRegex(PeekError, "no unit 4: the game has units 0 to 3"):
            peek(self.api, "unit", 4, None)
        with self.assertRaisesRegex(PeekError, r"no unit 5000 \(0 to 1008\)"):
            peek(self.api, "unit", 5000, None)


class PokeUnitTest(UnitFieldCase):
    def test_a_change_touches_only_its_bytes(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 1, "experience", "120", block_name="unit"), "unit 1 experience: 25 -> 120")
        self.assertEqual(self.differing(before), [unit_at(1) + 14])                     # 25 -> 120 changes only the low byte
        self.assertEqual(struct.unpack_from("<h", self.mem, unit_at(1) + 14)[0], 120)
        poke(self.api, 1, "level", "3", block_name="unit")
        poke(self.api, 1, "moves_left", "127", block_name="unit")
        self.assertEqual((self.mem[unit_at(1) + 12], self.mem[unit_at(1) + 8]), (3, 127))

    def test_undo_and_dry_run(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 1, "level", "3", dry_run=True, block_name="unit"), "(dry run) would write unit 1 level: 1 -> 3")
        self.assertEqual(bytes(self.mem), before)
        poke(self.api, 1, "level", "3", block_name="unit")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_ranges_and_read_only_fields(self):
        before = bytes(self.mem)
        for field, value, pattern in (("level", "9", "whole number from 0 to 8"), ("experience", "=-1", "whole number"),
                                      ("experience", "30001", "whole number"), ("moves_left", "128", "whole number"),
                                      ("owner", "1", "not editable"), ("type", "5", "not editable"),
                                      ("enchantments", "1", "not editable"), ("sight", "3", "not editable")):
            with self.assertRaisesRegex(PokeError, pattern):
                poke(self.api, 1, field, value, block_name="unit")
        self.assertEqual(bytes(self.mem), before)

    def test_guesses_need_force(self):
        with self.assertRaisesRegex(PokeError, "only a guess"):
            poke(self.api, 1, "x", "9", block_name="unit")
        poke(self.api, 1, "x", "9", force=True, block_name="unit")
        poke(self.api, 1, "plane", "myrror", force=True, block_name="unit")
        self.assertEqual((self.mem[unit_at(1)], self.mem[unit_at(1) + 2]), (9, 1))

    def test_a_dead_or_missing_unit_is_refused(self):
        self.mem[unit_at(2) + 2] = 0xFF
        self.mem[unit_at(2) + 3] = 0xFF
        with self.assertRaisesRegex(PokeError, "unit 2 is dead"):
            poke(self.api, 2, "level", "2", block_name="unit")
        with self.assertRaisesRegex(PeekError, "no unit 4"):
            poke(self.api, 4, "level", "2", block_name="unit")
        with self.assertRaisesRegex(PokeError, r"no unit -1 \(0 to 1008\)"):
            poke(self.api, -1, "level", "2", block_name="unit")

    def test_the_commands(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["poke", "unit", "1", "level", "2", "--url", self.server.url]), 0)
            self.assertEqual(main(["peek", "unit", "1", "level", "--url", self.server.url]), 0)
            self.assertEqual(main(["fields", "unit"]), 0)
            self.assertEqual(main(["poke", "unit", "1", "owner", "3", "--url", self.server.url]), 1)
        text = out.getvalue()
        self.assertIn("unit 1 level: 1 -> 2", text)
        self.assertIn("level = 2", text)
        self.assertIn("moves_left", text)
        self.assertIn("not editable", err.getvalue())
