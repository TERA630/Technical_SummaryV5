import unittest

from technical_summary.parsing import parse_tickers_from_md


class ParsingTest(unittest.TestCase):
    def test_bulleted_tickers_do_not_include_marker(self):
        self.assertEqual(
            parse_tickers_from_md("- トヨタ自動車 (7203)\n- ソニーグループ (6758)\n"),
            [("トヨタ自動車", "7203"), ("ソニーグループ", "6758")],
        )

    def test_duplicate_codes_keep_first_name(self):
        self.assertEqual(
            parse_tickers_from_md("- トヨタ自動車 (7203)\n- TOYOTA (7203)\n"),
            [("トヨタ自動車", "7203")],
        )


if __name__ == "__main__":
    unittest.main()
