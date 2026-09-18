import unittest

from core.bible_sender import format_summary
from core.bible_scripture_resolver import translate_citation


class SummaryFormatTests(unittest.TestCase):
    def test_translates_each_book_when_range_crosses_books(self):
        self.assertEqual(translate_citation("마 27-막1", "EN"), "Matt 27-Mark 1")
        self.assertEqual(translate_citation("에 10-욥1", "MN"), "Ест 10-Иов 1")

    def test_omits_proverbs_line_when_new_template_has_no_proverbs_column(self):
        row = ["마 1-5", "왕하 2-3", "시 119:65-88", "", "요 1:1-18"]

        summary = format_summary(row, "KO", "2026/07/01")

        self.assertIn("시편: 시 119:65-88편", summary)
        self.assertNotIn("잠언:", summary)


if __name__ == "__main__":
    unittest.main()
