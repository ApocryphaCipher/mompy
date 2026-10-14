import contextlib
import io
import struct

from mompy import layout
from mompy.api import DosboxApi
from mompy.cli import main
from mompy.poke import PokeError, poke, undo
from mompy.summon import make_record, summon, create

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory, put_field
from .test_where import put_city

BASE = layout.REFERENCE_WIZARD_BASE
COUNT_AT = layout.UNIT_COUNT_REFERENCE


def unit_at(slot):
    return layout.UNITS.reference + slot * 32


def live_count(mem):
    return struct.unpack_from("<H", mem, COUNT_AT)[0]


class SummonCase(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.mem = game_memory(cities=0, units=4)
        put_city(self.mem, 0, "Blackstone", 51, 22, 1, 0)
        put_city(self.mem, 1, "Darkmoor", 39, 20, 1, 2)
        put_field(self.mem, BASE, "wizard", 1, "summoning_circle", [51, 22, 1])
        put_field(self.mem, BASE, "wizard", 2, "summoning_circle", [39, 20, 1])
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.api = DosboxApi(self.server.url)

    def differing(self, before):
        return [i for i in range(len(before)) if before[i] != self.mem[i]]

    def fill_tile(self, x, y, plane, owner, n):
        """Write ``n`` live units onto a tile, after the existing four."""
        live = live_count(self.mem)
        for i in range(n):
            at = unit_at(live + i)
            self.mem[at:at + 6] = bytes([x, y, plane, owner, 2, 40])
        struct.pack_into("<H", self.mem, COUNT_AT, live + n)


class SummonTest(SummonCase):
    def test_a_unit_at_the_summoning_circle_changes_only_its_record_and_the_count(self):
        before = bytes(self.mem)
        out = summon(self.api, 1, "war_bears")
        self.assertEqual(out, "War Bears for wizard 1 (Jafar) at Blackstone (Myrror 51, 22), unit slot 4")
        rec = bytes(self.mem[unit_at(4):unit_at(4) + 32])
        self.assertEqual(rec, make_record(summon_type(self, 179), 0, 51, 22, 1))
        self.assertEqual(live_count(self.mem), 5)
        self.assertEqual(sorted(set(self.differing(before)) - set(range(unit_at(4), unit_at(4) + 32)) - {COUNT_AT}), [])

    def test_the_record_follows_the_type_table(self):
        summon(self.api, 1, "war_bears")
        rec = self.mem[unit_at(4):unit_at(4) + 32]
        self.assertEqual((rec[3], rec[5], rec[6]), (0, 179, 0xFF))
        self.assertEqual((rec[4], rec[8]), (2 + 179 % 3, 2 + 179 % 3))     # moves from the type's record
        self.assertEqual((rec[12], rec[22]), (0, 1))                       # fantastic: level 0; sight from the type
        self.assertEqual(rec[23], 0)                                       # creatures carry no weapon grade

    def test_an_ordinary_unit_is_made_by_a_city_for_its_owner_at_maximum_experience(self):
        out = create(self.api, 2, "cavalry")           # city 2 is Darkmoor, wizard 3's
        self.assertIn("for wizard 3", out)
        rec = self.mem[unit_at(4):unit_at(4) + 32]
        self.assertEqual((list(rec[:4]), rec[5], rec[12]), ([39, 20, 1, 2], 60, 3))
        self.assertEqual(struct.unpack_from("<h", rec, 14)[0], 120)         # maximum experience
        self.assertEqual(rec[23] & 3, 3)                                    # adamantium weapons

    def test_summoned_and_ordinary_units_use_their_own_verb(self):
        self.assertRaisesRegex(PokeError, "ordinary unit, not a summoned creature", summon, self.api, 1, "cavalry")
        self.assertRaisesRegex(PokeError, "is a summoned creature: mompy poke wizard", create, self.api, 1, "war_bears")
        self.assertEqual(self.server.writes, [])

    def test_a_neutral_city_cannot_create(self):
        put_city(self.mem, 5, "Wildburg", 5, 5, 0, 5)
        self.assertRaisesRegex(PokeError, "neutral city", create, self.api, 6, "cavalry")

    def test_owner_follows_the_wizard_and_place_at_a_city(self):
        summon(self.api, 3, "sprites", at="darkmoor")
        rec = self.mem[unit_at(4):unit_at(4) + 6]
        self.assertEqual(list(rec[:4]), [39, 20, 1, 2])

    def test_at_coordinates_and_plane_names(self):
        summon(self.api, 1, "sprites", at="10,12,arcanus")
        self.assertEqual(list(self.mem[unit_at(4):unit_at(4) + 3]), [10, 12, 0])

    def test_count_makes_several_units(self):
        out = summon(self.api, 1, "war_bears", count=3)
        self.assertIn("3 War Bears", out)
        self.assertEqual(live_count(self.mem), 7)
        self.assertEqual([self.mem[unit_at(i) + 5] for i in (4, 5, 6)], [179] * 3)

    def test_a_dead_slot_is_reused_and_the_count_stays(self):
        at = unit_at(2)
        self.mem[at:at + 32] = bytes([0xFF, 0xFF, 0xFF, 0xFF]) + bytes(28)
        out = summon(self.api, 1, "war_bears")
        self.assertIn("unit slot 2", out)
        self.assertEqual(live_count(self.mem), 4)
        self.assertEqual(self.mem[unit_at(2) + 5], 179)

    def test_undo_restores_everything(self):
        before = bytes(self.mem)
        summon(self.api, 1, "war_bears", count=2)
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_dry_run_writes_nothing(self):
        before = bytes(self.mem)
        self.assertTrue(summon(self.api, 1, "war_bears", dry_run=True).startswith("(dry run) would put War Bears"))
        self.assertEqual(bytes(self.mem), before)


def summon_type(case, number):
    from mompy.game import connect
    from mompy.summon import read_types

    return read_types(case.api, connect(case.api))[number]


class RefusalTest(SummonCase):
    def refuse(self, pattern, *args, **kw):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, pattern):
            summon(self.api, *args, **kw)
        self.assertEqual(bytes(self.mem), before)
        self.assertEqual(self.server.writes, [])

    def test_a_hero_is_refused(self):
        self.refuse("is a hero", 1, "barbarian")

    def test_an_ambiguous_name_lists_its_types(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, r"Swordsmen exists for several races \(types 40, 58\)"):
            create(self.api, 1, "swordsmen")
        self.assertEqual(bytes(self.mem), before)

    def test_a_type_number_is_accepted_for_those(self):
        create(self.api, 1, "58")
        self.assertEqual(self.mem[unit_at(4) + 5], 58)

    def test_unknown_names_and_numbers(self):
        self.refuse("no unit is called 'dragonfly'", 1, "dragonfly")
        self.refuse("there is no unit type 198", 1, "198")
        self.refuse("which unit", 1, " ")

    def test_wizard_and_count_limits(self):
        self.refuse("there is no wizard 6", 6, "war_bears")
        self.refuse("at most 9", 1, "war_bears", count=10)
        self.refuse("at most 9", 1, "war_bears", count=0)

    def test_bad_places(self):
        self.refuse("is not a place", 1, "war_bears", at="60,1,0")
        self.refuse("is not a place", 1, "war_bears", at="1,1,2")
        self.refuse("no city called 'nowhere'", 1, "war_bears", at="nowhere")

    def test_a_wizard_without_a_circle_needs_at(self):
        put_field(self.mem, BASE, "wizard", 4, "summoning_circle", [-1, 300, 7])
        self.refuse("no summoning circle", 4, "war_bears")

    def test_a_garbled_type_table_is_refused(self):
        dgroup = BASE - 0x9ECA
        self.mem[dgroup + 0x4000:dgroup + 0x4004] = b"\x01\x02\x03\x04"
        self.refuse("type table does not look right", 1, "sprites")

    def test_the_units_table_full(self):
        struct.pack_into("<H", self.mem, COUNT_AT, layout.UNITS.count)
        self.refuse("table is full", 1, "war_bears")


class StackTest(SummonCase):
    def test_a_full_tile_pushes_the_unit_next_door(self):
        self.fill_tile(51, 22, 1, 0, 9)
        out = summon(self.api, 1, "war_bears")
        self.assertIn("had no room", out)
        x, y = self.mem[unit_at(13)], self.mem[unit_at(13) + 1]
        self.assertNotEqual((x, y), (51, 22))
        self.assertLessEqual(max(abs(x - 51), abs(y - 22)), 1)

    def test_a_tile_with_foreign_units_is_not_shared(self):
        self.fill_tile(51, 22, 1, 3, 1)
        summon(self.api, 1, "war_bears")
        x, y = self.mem[unit_at(5)], self.mem[unit_at(5) + 1]
        self.assertNotEqual((x, y), (51, 22))

    def test_a_foreign_city_tile_is_not_used(self):
        out = summon(self.api, 1, "war_bears", at="darkmoor")        # Darkmoor belongs to wizard 3
        self.assertNotIn("Darkmoor (Myrror 39, 20),", out.split("at ")[1].split(",")[0] + ",")
        x, y = self.mem[unit_at(4)], self.mem[unit_at(4) + 1]
        self.assertNotEqual((x, y), (39, 20))

    def test_no_room_anywhere_is_refused(self):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.fill_tile(51 + dx, 22 + dy, 1, 3, 1)
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "no room"):
            summon(self.api, 1, "war_bears")
        self.assertEqual(bytes(self.mem), before)

    def test_a_failed_count_write_takes_the_records_back(self):
        before = bytes(self.mem)
        self.server.fail_write_number = 2                          # the record is write 1, the count is write 2
        with self.assertRaises(PokeError):
            summon(self.api, 1, "war_bears")
        self.assertEqual(bytes(self.mem), before)


class CommandTest(SummonCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([*args, "--url", self.server.url])
        return code, out.getvalue(), err.getvalue()

    def test_create_by_city_name(self):
        code, out, _ = self.run_cli("poke", "city", "blackstone", "create", "unit.cavalry", "--count", "2")
        self.assertEqual(code, 0)
        self.assertIn("2 Cavalry for wizard 1 (Jafar) at Blackstone", out)

    def test_the_command(self):
        code, out, _ = self.run_cli("poke", "wizard", "1", "cast", "unit.war_bears", "--count", "2", "--at", "darkmoor")
        self.assertEqual(code, 0)
        self.assertIn("2 War Bears for wizard 1 (Jafar)", out)
        self.assertEqual(live_count(self.mem), 6)

    def test_a_refusal_exits_1(self):
        code, _, err = self.run_cli("poke", "wizard", "1", "cast", "unit.barbarian")
        self.assertEqual(code, 1)
        self.assertIn("mompy: Barbarian is a hero", err)

    def test_globals_still_work(self):
        code, out, _ = self.run_cli("poke", "wizard", "1", "cast", "aura_of_majesty")
        self.assertEqual(code, 0)
        self.assertIn("Aura of Majesty", out)
