import contextlib
import io
import struct

from mompy import layout
from mompy.cli import main
from mompy.poke import PokeError, undo
from mompy.stack import experience, heal, weapons

from . import test_pew
from .test_summon import BASE, SummonCase, unit_at

DGROUP = BASE - layout.DGROUP_BELOW_WIZARDS
TABLE = (0, 20, 60, 120, 200, 300, 450, 600, 1000)
SWORDSMEN, HERO, CREATURE = 40, 5, 179


class StackCase(SummonCase):
    stack = test_pew.PewTest.stack

    def setUp(self):
        super().setUp()
        struct.pack_into("<9h", self.mem, DGROUP + 0x1D74, *TABLE)
        # Blackstone (51, 22, Myrror): two Swordsmen, a hero, a summoned creature
        self.ids = self.stack(51, 22, 1, 0, 2, kind=SWORDSMEN) + self.stack(51, 22, 1, 0, 1, kind=HERO) + self.stack(51, 22, 1, 0, 1, kind=CREATURE)
        self.sword_a, self.sword_b, self.hero, self.creature = self.ids

    def field(self, unit, offset, size=1):
        return int.from_bytes(self.mem[unit_at(unit) + offset:unit_at(unit) + offset + size], "little")


class HealTest(StackCase):
    def test_everyone_on_the_tile_is_healed_heroes_and_creatures_too(self):
        for u in self.ids:
            self.mem[unit_at(u) + 17] = 3
        self.mem[unit_at(self.sword_b) + 17] = 0                                         # one is unhurt already
        before = bytes(self.mem)
        out = heal(self.api, "blackstone")
        self.assertEqual(out, "healed 3 of 4 units at Blackstone (Myrror 51, 22) (already so: 1)")
        self.assertEqual([self.field(u, 17) for u in self.ids], [0, 0, 0, 0])
        self.assertEqual(sorted(set(self.differing(before)) - {unit_at(u) + 17 for u in self.ids}), [])

    def test_skip_heroes_leaves_the_hero_hurt(self):
        self.mem[unit_at(self.hero) + 17] = 4
        self.mem[unit_at(self.sword_a) + 17] = 1
        out = heal(self.api, "blackstone", skip_heroes=True)
        self.assertIn("heroes skipped: 1", out)
        self.assertEqual((self.field(self.hero, 17), self.field(self.sword_a, 17)), (4, 0))

    def test_undo_dry_run_and_nothing_to_do(self):
        self.mem[unit_at(self.sword_a) + 17] = 2
        before = bytes(self.mem)
        self.assertTrue(heal(self.api, "blackstone", dry_run=True).startswith("(dry run) would heal 1 of 4"))
        self.assertEqual(bytes(self.mem), before)
        heal(self.api, "blackstone")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)
        heal(self.api, "blackstone")
        self.assertTrue(heal(self.api, "blackstone").startswith("nothing to do: healed 0 of 4"))


class WeaponsTest(StackCase):
    def test_only_ordinary_units_get_the_grade_and_flags_are_kept(self):
        self.mem[unit_at(self.sword_a) + 23] = 0x21                                      # magic weapons and undead
        before = bytes(self.mem)
        out = weapons(self.api, "blackstone", "adamantium")
        self.assertEqual(out, "gave adamantium weapons to 2 of 4 units at Blackstone (Myrror 51, 22) (heroes left alone: 1, summoned creatures carry no weapons: 1)")
        self.assertEqual((self.field(self.sword_a, 23), self.field(self.sword_b, 23)), (0x23, 3))
        self.assertEqual((self.field(self.hero, 23), self.field(self.creature, 23)), (0, 0))
        self.assertEqual(sorted(set(self.differing(before)) - {unit_at(self.sword_a) + 23, unit_at(self.sword_b) + 23}), [])

    def test_grade_names_numbers_and_downgrades(self):
        weapons(self.api, "blackstone", "Mithril")
        self.assertEqual(self.field(self.sword_a, 23), 2)
        weapons(self.api, "blackstone", "0")
        self.assertEqual(self.field(self.sword_a, 23), 0)

    def test_a_bad_grade_writes_nothing(self):
        before = bytes(self.mem)
        for bad in ("steel", "4", "", None):
            with self.assertRaisesRegex(PokeError, "weapons are normal, magic, mithril, adamantium"):
                weapons(self.api, "blackstone", bad)
        self.assertEqual(bytes(self.mem), before)

    def test_undo(self):
        before = bytes(self.mem)
        weapons(self.api, "blackstone", "adamantium")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)


class ExperienceTest(StackCase):
    def test_each_kind_gets_its_own_maximum(self):
        before = bytes(self.mem)
        out = experience(self.api, "blackstone", "max")
        self.assertEqual(out, "set maximum experience on 3 of 4 units at Blackstone (Myrror 51, 22) (summoned creatures do not level: 1)")
        self.assertEqual((self.field(self.sword_a, 12), self.field(self.sword_a, 14, 2)), (3, 120))
        self.assertEqual((self.field(self.hero, 12), self.field(self.hero, 14, 2)), (8, 1000))
        self.assertEqual((self.field(self.creature, 12), self.field(self.creature, 14, 2)), (0, 0))
        touched = {unit_at(u) + k for u in (self.sword_a, self.sword_b, self.hero) for k in range(12, 16)}
        self.assertEqual(sorted(set(self.differing(before)) - touched), [])

    def test_a_warlords_ordinary_units_reach_ultra_elite(self):
        retorts = [0] * 18
        retorts[1] = 1                                                                  # Warlord
        from .fake_dosbox import put_field
        put_field(self.mem, BASE, "wizard", 1, "retorts", retorts)
        experience(self.api, "blackstone", "max")
        self.assertEqual((self.field(self.sword_a, 12), self.field(self.sword_a, 14, 2)), (4, 120))     # Ultra Elite
        self.assertEqual((self.field(self.hero, 12), self.field(self.hero, 14, 2)), (8, 1000))         # heroes are not raised past Demi-God
        self.assertEqual(self.field(self.creature, 12), 0)

    def test_without_warlord_elite_is_the_top(self):
        experience(self.api, "blackstone", "max")
        self.assertEqual(self.field(self.sword_a, 12), 3)

    def test_nothing_is_ever_lowered(self):
        at = unit_at(self.sword_a)
        self.mem[at + 12] = 4                                                          # level 4 with 120 experience (a level a retort gave it)
        struct.pack_into("<h", self.mem, at + 14, 120)
        struct.pack_into("<h", self.mem, unit_at(self.sword_b) + 14, 500)              # more experience than the Elite entry
        self.mem[unit_at(self.sword_b) + 12] = 3
        experience(self.api, "blackstone", "max")
        self.assertEqual((self.field(self.sword_a, 12), self.field(self.sword_a, 14, 2)), (4, 120))
        self.assertEqual((self.field(self.sword_b, 12), self.field(self.sword_b, 14, 2)), (3, 500))
        self.assertEqual((self.field(self.hero, 12), self.field(self.hero, 14, 2)), (8, 1000))

    def test_skip_heroes(self):
        out = experience(self.api, "blackstone", "max", skip_heroes=True)
        self.assertIn("heroes skipped: 1", out)
        self.assertEqual(self.field(self.hero, 14, 2), 0)

    def test_the_numbers_come_from_the_games_own_table(self):
        struct.pack_into("<9h", self.mem, DGROUP + 0x1D74, 0, 10, 30, 70, 100, 150, 220, 300, 500)
        experience(self.api, "blackstone", "max")
        self.assertEqual((self.field(self.sword_a, 14, 2), self.field(self.hero, 14, 2)), (70, 500))

    def test_a_table_that_does_not_look_right_is_refused(self):
        struct.pack_into("<9h", self.mem, DGROUP + 0x1D74, 5, 20, 60, 120, 200, 300, 450, 600, 1000)
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "experience table does not look right"):
            experience(self.api, "blackstone", "max")
        struct.pack_into("<9h", self.mem, DGROUP + 0x1D74, 0, 20, 60, 60, 200, 300, 450, 600, 1000)
        with self.assertRaisesRegex(PokeError, "experience table does not look right"):
            experience(self.api, "blackstone", "max")
        self.assertEqual(self.field(self.sword_a, 14, 2), 0)

    def test_only_max_is_understood(self):
        with self.assertRaisesRegex(PokeError, "experience takes 'max'"):
            experience(self.api, "blackstone", "lots")

    def test_undo(self):
        before = bytes(self.mem)
        experience(self.api, "blackstone", "max")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)


class CommandTest(StackCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([*args, "--url", self.server.url])
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_the_three_commands_and_the_pointer(self):
        self.mem[unit_at(self.hero) + 17] = 2
        test_pew.put_view(self.mem)
        code, out, _ = self.run_cli("unit", "heal", "--at", "pointer", "--skip-heroes")
        self.assertEqual(code, 0)
        self.assertIn("heroes skipped: 1", out)
        self.assertEqual(self.field(self.hero, 17), 2)
        self.assertEqual(self.run_cli("unit", "heal", "--at", "blackstone", "--skip-heroes", "--dry-run")[0], 0)
        self.assertIn("gave magic weapons to 2 of 4", self.run_cli("unit", "weapons", "magic", "--at", "51,22,myrror")[1])
        self.assertIn("set maximum experience on 3 of 4", self.run_cli("unit", "experience", "max", "--at", "blackstone")[1])

    def test_missing_pieces_are_explained(self):
        code, _, err = self.run_cli("unit", "heal")
        self.assertEqual(code, 1)
        self.assertIn("say where: mompy unit heal --at PLACE", err)
        code, _, err = self.run_cli("unit", "weapons", "--at", "blackstone")
        self.assertEqual(code, 1)
        self.assertIn("weapons are normal, magic, mithril, adamantium", err)
        self.assertEqual(self.run_cli("unit", "heal", "--at", "30,30,0")[0], 1)
