import contextlib
import io
import unittest

from mompy import fields as F
from mompy import layout, poke as poking
from mompy.api import DosboxApi
from mompy.cast import UNAVAILABLE, cast, dispel
from mompy.cli import main
from mompy.poke import PokeError, undo

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory, put_field

BASE = layout.REFERENCE_WIZARD_BASE
GLOBALS = F.find("wizard", "globals")


def global_at(number, index):
    """Where byte ``index`` (0-based) of wizard ``number``'s global enchantments sits in the fake game."""
    return BASE + (number - 1) * layout.WIZARD_STRIDE + GLOBALS.offset + index


class CastCase(HomeTestCase):
    def setUp(self):
        super().setUp()
        self.mem = game_memory()
        self.server = FakeDosbox(self.mem)
        self.server.__enter__()
        self.addCleanup(self.server.__exit__)
        self.api = DosboxApi(self.server.url)

    def differing(self, before):
        return [i for i in range(len(before)) if before[i] != self.mem[i]]


class CastTest(CastCase):
    def test_cast_sets_one_byte_and_names_the_caster(self):
        before = bytes(self.mem)
        self.assertEqual(cast(self.api, 1, "aura_of_majesty"), "Aura of Majesty cast on wizard 1 (Jafar)")
        self.assertEqual(self.differing(before), [global_at(1, 3)])           # byte 3 of wizard 1's twenty-four
        self.assertEqual(self.mem[global_at(1, 3)], 1)

    def test_any_spelling_of_the_name(self):
        for spelling, index in (("Aura of Majesty", 3), ("globals.aura_of_majesty", 3), ("aura-of-majesty", 3), ("aura", 3),
                                ("natures_wrath", 8), ("just", 18), ("5", 4)):            # a number is the 1-based element: 5 is Wind Mastery
            mem = game_memory()
            with FakeDosbox(mem) as fake:
                cast(DosboxApi(fake.url), 2, spelling)
            self.assertEqual(mem[global_at(2, index)], 1, spelling)

    def test_an_ambiguous_or_unknown_name_is_refused(self):
        before = bytes(self.mem)
        with self.assertRaisesRegex(PokeError, "could be Nature Awareness, Nature's Wrath"):
            cast(self.api, 1, "nature")
        with self.assertRaisesRegex(PokeError, "no element"):
            cast(self.api, 1, "fireball")
        with self.assertRaisesRegex(PokeError, "which enchantment"):
            cast(self.api, 1, "  ")
        with self.assertRaisesRegex(PokeError, "which enchantment"):
            cast(self.api, 1, "globals.")
        self.assertEqual(bytes(self.mem), before)

    def test_the_caster_is_whichever_wizard_you_name(self):
        cast(self.api, 3, "just_cause")
        self.assertEqual(self.mem[global_at(3, 18)], 1)
        self.assertEqual(self.mem[global_at(1, 18)], 0)
        with self.assertRaisesRegex(PokeError, "no wizard 6"):
            cast(self.api, 6, "just_cause")

    def test_two_wizards_may_hold_the_same_one(self):
        cast(self.api, 1, "aura_of_majesty")
        self.assertEqual(cast(self.api, 2, "aura_of_majesty"), "Aura of Majesty cast on wizard 2 (Freya)")
        self.assertEqual((self.mem[global_at(1, 3)], self.mem[global_at(2, 3)]), (1, 1))

    def test_already_cast_writes_nothing_and_logs_nothing(self):
        cast(self.api, 1, "aura_of_majesty")
        writes, log = len(self.server.writes), len(poking.read_log()[0])
        self.assertEqual(cast(self.api, 1, "aura_of_majesty"), "wizard 1 (Jafar) already has Aura of Majesty")
        self.assertEqual((len(self.server.writes), len(poking.read_log()[0])), (writes, log))

    def test_dry_run_writes_and_logs_nothing(self):
        before = bytes(self.mem)
        self.assertEqual(cast(self.api, 1, "aura_of_majesty", dry_run=True), "(dry run) would cast Aura of Majesty on wizard 1 (Jafar)")
        self.assertTrue(bytes(self.mem) == before)
        self.assertEqual((self.server.writes, poking.read_log()), ([], ([], 0)))


class DispelTest(CastCase):
    def test_dispel_clears_it(self):
        put_field(self.mem, BASE, "wizard", 1, "globals", [1 if i == 18 else 0 for i in range(24)])
        before = bytes(self.mem)
        self.assertEqual(dispel(self.api, 1, "just_cause"), "Just Cause dispelled from wizard 1 (Jafar)")
        self.assertEqual(self.differing(before), [global_at(1, 18)])

    def test_dispel_of_what_is_not_there(self):
        before = bytes(self.mem)
        self.assertEqual(dispel(self.api, 1, "just_cause"), "wizard 1 (Jafar) does not have Just Cause")
        self.assertTrue(bytes(self.mem) == before)
        self.assertEqual(poking.read_log(), ([], 0))

    def test_dry_run(self):
        put_field(self.mem, BASE, "wizard", 1, "globals", [1 if i == 18 else 0 for i in range(24)])
        self.assertEqual(dispel(self.api, 1, "just_cause", dry_run=True), "(dry run) would dispel Just Cause from wizard 1 (Jafar)")
        self.assertEqual(self.mem[global_at(1, 18)], 1)


class QuestionableTest(CastCase):
    def test_time_stop_is_not_available_even_with_force(self):
        self.assertEqual(UNAVAILABLE, ("Time Stop",))
        before, logged = bytes(self.mem), len(poking.read_log()[0])
        for force in (False, True):
            with self.assertRaisesRegex(PokeError, "not available in mompy"):
                cast(self.api, 1, "Time Stop", force=force)
        self.assertTrue(bytes(self.mem) == before)                                       # not assertEqual: 16 MiB diffs
        self.assertEqual(len(poking.read_log()[0]), logged)

    def test_a_stray_time_stop_flag_can_still_be_dispelled(self):
        put_field(self.mem, BASE, "wizard", 1, "globals", [1 if i == GLOBALS.element("Time Stop") else 0 for i in range(24)])
        self.assertEqual(dispel(self.api, 1, "time_stop"), "Time Stop dispelled from wizard 1 (Jafar)")
        self.assertEqual(self.mem[global_at(1, 6)], 0)

    def test_the_four_map_globals_cast_like_any_other(self):
        for spell in ("Planar Seal", "Armageddon", "Meteor Storm", "Great Wasting"):
            cast(self.api, 1, spell)
            self.assertEqual(self.mem[global_at(1, GLOBALS.element(spell))], 1, spell)

    def test_the_rest_do_not(self):
        asks = set(UNAVAILABLE)
        for i in range(24):
            spell = GLOBALS.label_for(i)
            if spell in asks:
                continue
            mem = game_memory()
            with FakeDosbox(mem) as fake:
                cast(DosboxApi(fake.url), 1, spell)
            self.assertEqual(mem[global_at(1, i)], 1, spell)

    def test_taking_one_off_never_needs_force(self):
        put_field(self.mem, BASE, "wizard", 1, "globals", [1 if i == 18 else 0 for i in range(24)])
        self.assertEqual(dispel(self.api, 1, "just_cause"), "Just Cause dispelled from wizard 1 (Jafar)")
        self.assertEqual(self.mem[global_at(1, 18)], 0)


class ServerTest(CastCase):
    def test_undo_takes_it_off_again(self):
        cast(self.api, 1, "aura_of_majesty")
        self.assertEqual(undo(self.api), "undid: globals.Aura of Majesty 1 -> 0")
        self.assertEqual(self.mem[global_at(1, 3)], 0)

    def test_writes_disabled_names_the_setting(self):
        self.server.allow_writes = False
        with self.assertRaisesRegex(PokeError, "webserver_allow_writes"):
            cast(self.api, 1, "aura_of_majesty")

    def test_the_game_changing_under_us_is_refused(self):
        self.server.race_on_write = True
        with self.assertRaisesRegex(PokeError, "changed globals.Aura of Majesty while mompy was working"):
            cast(self.api, 1, "aura_of_majesty")


class CliTest(CastCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv) + ["--url", self.server.url])
        return code, out.getvalue().strip(), err.getvalue().strip()

    def test_the_command_line(self):
        self.assertEqual(self.run_cli("poke", "wizard", "1", "cast", "aura_of_majesty"), (0, "Aura of Majesty cast on wizard 1 (Jafar)", ""))
        self.assertEqual(self.run_cli("peek", "wizard", "1", "globals")[1], "globals = Aura of Majesty")
        self.assertEqual(self.run_cli("poke", "wizard", "1", "dispel", "globals.aura_of_majesty"),
                         (0, "Aura of Majesty dispelled from wizard 1 (Jafar)", ""))
        code, out, err = self.run_cli("poke", "wizard", "1", "cast", "time_stop", "--force")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("not available in mompy", err)
        code, _, err = self.run_cli("poke", "fortress", "1", "cast", "aura")
        self.assertEqual(code, 1)
        self.assertIn("cast is for wizards", err)


if __name__ == "__main__":
    unittest.main()
