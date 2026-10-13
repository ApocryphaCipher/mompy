import io
import contextlib
import unittest

from mompy import layout, locate, version
from mompy.api import ApiError, DosboxApi, Mismatch, WritesDisabled
from mompy.cli import main
from mompy.doctor import FAIL, OK, WARN, diagnose, render

from .fake_dosbox import FakeDosbox, HomeTestCase, game_memory


def statuses(report):
    return {c.name.strip(): c.status for c in report.checks}


class VersionTest(unittest.TestCase):
    def test_parse(self):
        v = version.parse("0.84.0-alpha (5b1f1d)")
        self.assertEqual((v.major, v.minor, v.patch, v.tag, v.build), (0, 84, 0, "alpha", "5b1f1d"))
        v = version.parse("0.83.0 (7b400)")
        self.assertEqual((v.major, v.minor, v.tag), (0, 83, ""))
        self.assertIsNone(version.parse("not a version"))
        self.assertIsNone(version.parse(""))

    def test_expected_base(self):
        self.assertEqual(version.expected_wizard_base(version.parse("0.83.0 (7b400)")), 0x3239A)
        self.assertEqual(version.expected_wizard_base(version.parse("0.84.0-alpha (5b1f1d)")), 0x328BA)
        self.assertEqual(version.expected_wizard_base(version.parse("0.85.1")), 0x328BA)
        self.assertIsNone(version.expected_wizard_base(version.parse("0.82.2")))
        self.assertIsNone(version.expected_wizard_base(None))
        self.assertEqual(0x328BA - 0x3239A, 0x520)       # 82 paragraphs: DOS STACKS in 0.84


class LocateTest(unittest.TestCase):
    def test_finds_the_table_wherever_it_is(self):
        for base in (0x328BA, 0x3239A, 0x40000):
            found = locate.find_wizard_tables(bytes(game_memory(base)))
            self.assertEqual([c.base for c in found], [base])
            self.assertEqual(found[0].names[0], "Jafar")

    def test_a_wizard_with_a_very_short_name_is_still_found(self):
        mem = game_memory(names=("Al", "Freya", "Sss'ra", "X", "Tauron"))
        found = locate.find_wizard_tables(bytes(mem))
        self.assertEqual([c.base for c in found], [layout.REFERENCE_WIZARD_BASE])
        self.assertEqual(found[0].names, ["Al", "Freya", "Sss'ra", "X", "Tauron"])
        with FakeDosbox(mem) as fake:
            self.assertTrue(diagnose(DosboxApi(fake.url)).ready)

    def test_nothing_without_a_loaded_game(self):
        self.assertEqual(locate.find_wizard_tables(bytes(game_memory(names=("", "", "", "", "")))), [])

    def test_four_names_are_not_a_table(self):
        self.assertEqual(locate.find_wizard_tables(bytes(game_memory(names=("A1x", "B2y", "C3z", "D4w", "")))), [])

    def test_a_name_must_be_nul_padded(self):
        mem = game_memory()
        at = layout.REFERENCE_WIZARD_BASE + layout.WIZARD_NAME_AT
        mem[at + 10] = ord("x")        # junk after the name's NUL: not a name field
        self.assertEqual(locate.find_wizard_tables(bytes(mem)), [])

    def test_tables_are_checked_at_the_found_shift(self):
        mem = bytes(game_memory(0x3239A))
        checks = locate.check_tables(mem, 0x3239A)
        self.assertTrue(all(c.ok for c in checks), checks)
        wrong = locate.check_tables(mem, 0x328BA)           # the same game, read at the wrong base
        self.assertFalse(all(c.ok for c in wrong))

    def test_implausible_records_fail_a_table(self):
        mem = game_memory(cities=0)
        self.assertFalse(next(c for c in locate.check_tables(bytes(mem), layout.REFERENCE_WIZARD_BASE)
                              if c.name == "cities").ok)
        mem = game_memory(units=2)
        at = layout.UNITS.reference
        mem[at] = 200                                        # x off the map
        self.assertFalse(next(c for c in locate.check_tables(bytes(mem), layout.REFERENCE_WIZARD_BASE)
                              if c.name == "units").ok)


class ApiTest(unittest.TestCase):
    def test_read_and_compare_and_swap(self):
        mem = game_memory()
        with FakeDosbox(mem) as fake:
            api = DosboxApi(fake.url)
            self.assertEqual(api.read(layout.REFERENCE_WIZARD_BASE + 1, 5), b"Jafar")
            api.write(0x300000, b"\x01\x02", expect=b"\x00\x00")
            self.assertEqual(bytes(mem[0x300000:0x300002]), b"\x01\x02")
            with self.assertRaises(Mismatch) as caught:
                api.write(0x300000, b"\xaa\xbb", expect=b"\x00\x00")
            self.assertEqual(caught.exception.current, b"\x01\x02")      # the 412 says what is really there
            self.assertEqual(bytes(mem[0x300000:0x300002]), b"\x01\x02")     # and wrote nothing

    def test_refused_writes_and_dead_servers(self):
        with FakeDosbox(game_memory(), allow_writes=False) as fake:
            with self.assertRaises(WritesDisabled):
                DosboxApi(fake.url).write(0x300000, b"\x01", expect=b"\x00")
        with self.assertRaises(ApiError):
            DosboxApi("http://127.0.0.1:1").info()
        with self.assertRaises(ValueError):
            DosboxApi("http://127.0.0.1:1").write(0, b"ab", expect=b"a")


class DoctorTest(unittest.TestCase):
    def test_healthy_game_is_ready_and_unchanged(self):
        mem = game_memory()
        before = bytes(mem)
        with FakeDosbox(mem) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertTrue(report.ready, render(report, "x"))
        self.assertEqual(report.wizard_base, layout.REFERENCE_WIZARD_BASE)
        self.assertEqual(bytes(mem), before)                  # the write probe changed nothing
        self.assertEqual(len(fake.writes), 1)                 # ...but did write, to test it
        self.assertEqual(statuses(report)["Address"], OK)
        self.assertIn("READY", render(report, "x"))

    def test_the_0_83_layout_is_expected_for_0_83(self):
        with FakeDosbox(game_memory(0x3239A), version="0.83.0 (7b400)") as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertTrue(report.ready)
        self.assertEqual(report.wizard_base, 0x3239A)
        self.assertEqual(statuses(report)["Address"], OK)

    def test_an_unexpected_address_warns_but_still_works(self):
        with FakeDosbox(game_memory(0x3239A), version="0.84.0-alpha (5b1f1d)") as fake:   # a 0.83 layout in a 0.84 DOSBox
            report = diagnose(DosboxApi(fake.url))
        self.assertTrue(report.ready)
        self.assertEqual(statuses(report)["Address"], WARN)
        self.assertEqual(report.wizard_base, 0x3239A)

    def test_no_game_loaded(self):
        with FakeDosbox(game_memory(names=("", "", "", "", ""))) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertFalse(report.ready)
        self.assertEqual(statuses(report)["Game"], FAIL)
        self.assertIn("NOT READY", render(report, "x"))
        self.assertEqual(len(fake.writes), 0)

    def test_wizard_names_with_garbage_around_are_refused(self):
        with FakeDosbox(game_memory(cities=0)) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertFalse(report.ready)
        self.assertIn("do not look right", next(c.detail for c in report.checks if c.name == "Game"))
        self.assertEqual(len(fake.writes), 0)          # never writes into memory that does not look right

    def test_writes_refused_is_read_only(self):
        with FakeDosbox(game_memory(), allow_writes=False) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertFalse(report.ready)
        self.assertEqual(statuses(report)["Writes"], FAIL)
        self.assertIn("webserver_allow_writes", next(c.detail for c in report.checks if c.name == "Writes"))
        self.assertIn("READ-ONLY", render(report, "x"))

    def test_the_game_changing_under_the_probe_is_a_warning_not_a_crash(self):
        with FakeDosbox(game_memory(), race_on_write=True) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertEqual(statuses(report)["Writes"], WARN)
        self.assertFalse(report.ready)

    def test_unreachable_server(self):
        report = diagnose(DosboxApi("http://127.0.0.1:1"))
        self.assertFalse(report.ready)
        self.assertEqual(statuses(report)["DOSBox"], FAIL)

    def test_two_copies_use_the_one_whose_tables_check_out(self):
        mem = game_memory()
        stale = 0x900000                       # a second block with names but nothing around it
        for i, name in enumerate(("Aaa", "Bbb", "Ccc", "Ddd", "Eee")):
            at = stale + i * layout.WIZARD_STRIDE + layout.WIZARD_NAME_AT
            mem[at:at + 20] = name.encode().ljust(20, b"\0")
        with FakeDosbox(mem) as fake:
            report = diagnose(DosboxApi(fake.url))
        self.assertTrue(report.ready)
        self.assertEqual(report.wizard_base, layout.REFERENCE_WIZARD_BASE)


class CliTest(HomeTestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_exit_codes_and_output(self):
        with FakeDosbox(game_memory()) as fake:
            code, out = self.run_cli("doctor", "--url", fake.url)
        self.assertEqual(code, 0)
        self.assertIn("Verdict: READY", out)
        self.assertIn("Jafar, Freya", out)
        code, out = self.run_cli("doctor", "--url", "http://127.0.0.1:1")
        self.assertEqual(code, 1)
        self.assertIn("Start DOSBox Staging", out)


if __name__ == "__main__":
    unittest.main()
