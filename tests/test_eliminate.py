import contextlib
import io
import struct

from mompy import layout
from mompy.cli import main
from mompy.eliminate import EMPTY_HERO, eliminate
from mompy.poke import PokeError, undo

from .fake_dosbox import put_field
from .test_summon import BASE, SummonCase, unit_at
from .test_where import put_city

CITY = layout.CITIES.reference
WIZ = layout.WIZARDS.reference
FORT = layout.FORTRESSES.reference


def city_at(slot):
    return CITY + slot * 114


class EliminateCase(SummonCase):
    def setUp(self):
        super().setUp()
        # Darkmoor (city slot 1) belongs to wizard 3 (index 2); add a second city of his and one of wizard 1's
        put_city(self.mem, 2, "Gloomhold", 5, 5, 0, 2)
        self.mem[city_at(2) + 67 + 3] = 3                       # an enchantment he cast on his own city (caster index + 1)
        self.mem[city_at(0) + 67 + 7] = 3                       # ... and one he cast on wizard 1's Blackstone
        self.mem[city_at(0) + 67 + 9] = 1                       # wizard 1's own enchantment there stays
        put_field(self.mem, BASE, "wizard", 3, "gold", 99)
        put_field(self.mem, BASE, "wizard", 3, "mana", 1234)
        put_field(self.mem, BASE, "wizard", 3, "globals", [1 if i in (3, 18) else 0 for i in range(24)])
        hero = WIZ + 2 * layout.WIZARDS.stride + 0x76
        self.mem[hero:hero + 28] = struct.pack("<h", 120) + b"Angus".ljust(14, b"\0") + struct.pack("<3h3h", 1, -1, -1, 1, 5, 6)
        for h in range(1, 6):
            self.mem[hero + 28 * h:hero + 28 * (h + 1)] = EMPTY_HERO
        self.fill_tile(30, 30, 0, 2, 2)                        # two more units of wizard 3 (units 4, 5)
        self.fill_tile(31, 30, 0, 1, 1)                        # one of wizard 2 stays (unit 6)


class EliminateTest(EliminateCase):
    def test_everything_is_taken_and_nothing_else_changes(self):
        before = bytes(self.mem)
        out = eliminate(self.api, 3)
        self.assertEqual(out, "wizard 3 (Sss'ra) is eliminated: 2 cities to neutral, 3 units killed, 1 heroes dropped, "
                              "1 of his city enchantments on others' cities cleared")
        # the fortress, both cities (owner and enchantments), the other city's enchantment, the three units
        self.assertEqual(self.mem[FORT + 2 * 4 + 3], 0)
        for slot in (1, 2):
            self.assertEqual(self.mem[city_at(slot) + 18], 5)
            self.assertEqual(bytes(self.mem[city_at(slot) + 67:city_at(slot) + 93]), bytes(26))
        self.assertEqual(self.mem[city_at(0) + 67 + 7], 0)
        self.assertEqual(self.mem[city_at(0) + 67 + 9], 1)
        for i in (2, 4, 5):
            self.assertEqual(list(self.mem[unit_at(i) + 2:unit_at(i) + 4]), [0xFF, 0xFF])
        self.assertEqual(self.mem[unit_at(6) + 3], 1)                                  # wizard 2's unit lives
        self.assertEqual(self.mem[unit_at(0) + 3], 0)                                  # wizard 1's too
        hero = WIZ + 2 * layout.WIZARDS.stride + 0x76
        self.assertEqual(bytes(self.mem[hero:hero + 28]), EMPTY_HERO)
        rec = WIZ + 2 * layout.WIZARDS.stride
        self.assertEqual(struct.unpack_from("<H", self.mem, rec + 0x356)[0], 0)
        self.assertEqual(struct.unpack_from("<H", self.mem, rec + 0x25C)[0], 0)
        self.assertEqual(bytes(self.mem[rec + 0x482:rec + 0x482 + 24]), bytes(24))
        self.assertEqual(struct.unpack_from("<H", self.mem, layout.UNIT_COUNT_REFERENCE)[0], 7)   # the count stays
        for other in (1, 2, 3):                                                         # the neighbours' wizards are untouched
            r = WIZ + other * layout.WIZARDS.stride
            if other != 2:
                self.assertEqual(bytes(self.mem[r:r + 1224]), before[r:r + 1224])
        self.assertEqual(self.mem[WIZ + 2 * 1224 + 0x5A:WIZ + 2 * 1224 + 0x5A + 10], before[WIZ + 2 * 1224 + 0x5A:WIZ + 2 * 1224 + 0x5A + 10])  # books kept

    def test_one_undo_puts_everything_back(self):
        before = bytes(self.mem)
        eliminate(self.api, 3)
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_dry_run_writes_nothing(self):
        before = bytes(self.mem)
        out = eliminate(self.api, 3, dry_run=True)
        self.assertTrue(out.startswith("(dry run) would eliminate wizard 3 (Sss'ra): 2 cities to neutral, 3 units killed"))
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(self.server.writes, [])

    def test_already_eliminated_writes_nothing(self):
        eliminate(self.api, 3)
        n = len(self.server.writes)
        self.assertIn("already eliminated", eliminate(self.api, 3))
        self.assertEqual(len(self.server.writes), n)

    def test_the_player_needs_force_and_numbers_are_checked(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "is you"):
            eliminate(self.api, 1)
        for n in (0, 6):
            with self.assertRaisesRegex(PokeError, "no wizard"):
                eliminate(self.api, n)
        self.assertEqual(bytes(self.mem), before)
        self.assertIn("is eliminated", eliminate(self.api, 1, force=True))

    def test_a_failed_write_takes_everything_back(self):
        before = bytes(self.mem)
        self.server.fail_write_number = 6
        with self.assertRaises(PokeError):
            eliminate(self.api, 3)
        self.assertEqual(bytes(self.mem), before)

    def test_the_command(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["banish", "wizard", "3", "--dead", "--url", self.server.url]), 0)
            self.assertEqual(main(["banish", "wizard", "1", "--dead", "--url", self.server.url]), 1)
        self.assertIn("wizard 3 (Sss'ra) is eliminated", out.getvalue())
        self.assertIn("is you", err.getvalue())
