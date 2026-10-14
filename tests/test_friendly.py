import contextlib
import io
import struct

from mompy import fields as F
from mompy import layout
from mompy.cli import main
from mompy.poke import PokeError, poke, undo

from .fake_dosbox import put_field
from .test_summon import BASE, SummonCase


def relation(mem, wizard, other):
    """Wizard ``wizard``'s (1 to 5) view of wizard ``other`` (1 to 5), straight from memory."""
    f = F.find("wizard", "relations")
    at = BASE + (wizard - 1) * layout.WIZARD_STRIDE + f.offset + (other - 1)
    return struct.unpack("<b", mem[at:at + 1])[0]


class FriendlyCase(SummonCase):
    def setUp(self):
        super().setUp()
        put_field(self.mem, BASE, "wizard", 2, "relations", [10, 0, 0, 0, 23, 0])        # Freya: Jafar 10, Tauron 23
        put_field(self.mem, BASE, "wizard", 5, "relations", [0, 23, 0, 0, 0, 0])         # Tauron's view of Freya
        put_field(self.mem, BASE, "wizard", 1, "gold", 500)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([*args, "--url", self.server.url])
        return code, out.getvalue().strip(), err.getvalue().strip()


class DeltaTest(FriendlyCase):
    def test_plus_and_minus_change_the_number_and_both_wizards_records(self):
        self.assertEqual(poke(self.api, 2, "relations.tauron", "+20"), "relations.Tauron: 23 -> 43  (and Tauron's view of Freya)")
        self.assertEqual((relation(self.mem, 2, 5), relation(self.mem, 5, 2)), (43, 43))
        poke(self.api, 2, "relations.tauron", "+=7")
        poke(self.api, 2, "relations.tauron", "delta:-10")
        self.assertEqual((relation(self.mem, 2, 5), relation(self.mem, 5, 2)), (40, 40))

    def test_a_plain_negative_number_is_still_the_number_itself(self):
        poke(self.api, 2, "relations.tauron", "-50")
        self.assertEqual(relation(self.mem, 2, 5), -50)

    def test_a_change_that_leaves_the_range_is_refused_and_nothing_is_written(self):
        before = bytes(self.mem)
        for text in ("+80", "+=78", "delta:-124"):
            with self.assertRaisesRegex(PokeError, r"relations.Tauron is 23: .* would make -?\d+, outside -100 to 100"):
                poke(self.api, 2, "relations.tauron", text)
        with self.assertRaisesRegex(PokeError, "gold is 500: .* outside 0 to 30000"):
            poke(self.api, 1, "gold", "delta:-501")
        self.assertEqual(bytes(self.mem), before)

    def test_it_works_on_any_number_but_not_on_words_or_lists(self):
        poke(self.api, 1, "gold", "+250")
        self.assertEqual(struct.unpack_from("<H", self.mem, BASE + 0x356)[0], 750)
        for field, text in (("name", "+5"), ("books", "+1"), ("treaty_status.tauron", "+1")):
            with self.assertRaisesRegex(PokeError, "changes a number by an amount"):
                poke(self.api, 2 if "treaty" in field else 1, field, text)

    def test_dry_run_and_undo(self):
        before = bytes(self.mem)
        self.assertEqual(poke(self.api, 2, "relations.tauron", "+20", dry_run=True),
                         "(dry run) would write relations.Tauron: 23 -> 43  (and Tauron's view of Freya)")
        self.assertEqual(bytes(self.mem), before)
        poke(self.api, 2, "relations.tauron", "+20")
        undo(self.api)
        self.assertEqual(bytes(self.mem), before)

    def test_no_change_when_the_delta_is_zero(self):
        self.assertIn("already 23", poke(self.api, 2, "relations.tauron", "+0"))


class CommandTest(FriendlyCase):
    def test_wizards_by_name_and_the_element_as_a_separate_word(self):
        code, out, _ = self.run_cli("peek", "wizard", "freya", "relation", "tauron")
        self.assertEqual((code, out), (0, "relations.Tauron = 23"))
        code, out, _ = self.run_cli("poke", "wizard", "Freya", "relation", "Tauron", "+20")
        self.assertEqual((code, out), (0, "relations.Tauron: 23 -> 43  (and Tauron's view of Freya)"))
        code, out, _ = self.run_cli("poke", "wizard", "freya", "relation", "tauron", "-=3")
        self.assertEqual((code, out), (0, "relations.Tauron: 43 -> 40  (and Tauron's view of Freya)"))
        self.assertEqual(relation(self.mem, 5, 2), 40)

    def test_a_dotted_element_and_a_number_still_work(self):
        self.assertEqual(self.run_cli("poke", "wizard", "2", "relations.tauron", "5")[1],
                         "relations.Tauron: 23 -> 5  (and Tauron's view of Freya)")

    def test_a_name_that_is_not_one_or_is_ambiguous(self):
        code, _, err = self.run_cli("peek", "wizard", "zed", "gold")
        self.assertEqual(code, 1)
        self.assertIn("'zed' is not a wizard here: Jafar, Freya, Sss'ra, Sharee, Tauron", err)
        code, _, err = self.run_cli("peek", "wizard", "s", "gold")
        self.assertIn("'s' could be Sss'ra, Sharee", err)
        self.assertEqual(self.run_cli("peek", "wizard", "ta", "gold")[0], 0)                     # a unique prefix

    def test_too_many_words_and_the_other_commands_are_unchanged(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            main(["poke", "wizard", "1", "gold", "1", "2", "3", "--url", self.server.url])
        self.assertIn("too many values", err.getvalue())
        self.assertEqual(self.run_cli("poke", "wizard", "1", "cast", "aura_of_majesty")[1], "Aura of Majesty cast on wizard 1 (Jafar)")
        self.assertEqual(self.run_cli("poke", "wizard", "1", "dispel", "aura_of_majesty")[1], "Aura of Majesty dispelled from wizard 1 (Jafar)")


class FieldNameTest(FriendlyCase):
    def test_singular_and_unique_prefix(self):
        self.assertEqual(F.find("wizard", "relation").name, "relations")
        self.assertEqual(F.find("wizard", "treaty").name, "treaty_status")
        self.assertEqual(F.find("wizard", "global").name, "globals")
        self.assertEqual(F.find("unit", "exp").name, "experience")
        with self.assertRaises(F.FieldError):
            F.find("wizard", "re")                                                              # relations, research_*: ambiguous
        with self.assertRaises(F.FieldError):
            F.find("wizard", "xyzzy")
