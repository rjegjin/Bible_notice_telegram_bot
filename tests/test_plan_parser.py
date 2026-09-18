import tempfile
import unittest
from pathlib import Path

from tools.plan_parser import (
    _merge_ai_results,
    is_hwpx_parsing_enabled,
    postprocess_plan_data,
    set_hwpx_parsing_enabled,
    validate_monthly_plan,
)


class MergeAiResultsTests(unittest.TestCase):
    def test_corrects_confirmed_esther_ocr_typo(self):
        plan = {"11": ["마27-막1", "엔10-욥1", "37", "11", "요20:1-18"]}
        self.assertEqual(postprocess_plan_data(plan)["11"][1], "에 10-욥1")

    def test_merges_separate_br_and_qt_results_by_day(self):
        br_result = {
            "days": [
                {
                    "day": 1,
                    "nt": "마1-5",
                    "ot": "왕하2-3",
                    "psalms": "119:65-88",
                    "proverbs": "1",
                }
            ]
        }
        qt_result = {"days": [{"day": 1, "qt": "요1:1-18"}]}

        self.assertEqual(
            _merge_ai_results(br_result, qt_result),
            {"1": ["마1-5", "왕하2-3", "119:65-88", "1", "요1:1-18"]},
        )

    def test_fills_proverbs_with_day_when_column_is_absent(self):
        br_result = {
            "days": [
                {
                    "day": 8,
                    "nt": "막1-4",
                    "ot": "왕하14-15",
                    "psalms": "122",
                    "proverbs": "",
                }
            ]
        }
        qt_result = {"days": [{"day": 8, "qt": "요3:1-15"}]}

        self.assertEqual(
            _merge_ai_results(br_result, qt_result),
            {"8": ["막1-4", "왕하14-15", "122", "8", "요3:1-15"]},
        )


class ParserSettingsTests(unittest.TestCase):
    def test_hwpx_parsing_defaults_to_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "missing.ini"
            self.assertFalse(is_hwpx_parsing_enabled(settings))

    def test_hwpx_toggle_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "plan_parser.ini"

            set_hwpx_parsing_enabled(True, settings)
            self.assertTrue(is_hwpx_parsing_enabled(settings))

            set_hwpx_parsing_enabled(False, settings)
            self.assertFalse(is_hwpx_parsing_enabled(settings))


class MonthlyPlanValidationTests(unittest.TestCase):
    def _valid_plan(self):
        return {
            str(day): ["마 1", "창 1", "시 1", f"잠 {day}", "요 1:1-2"]
            for day in range(1, 32)
        }

    def test_rejects_missing_calendar_day(self):
        plan = self._valid_plan()
        del plan["31"]

        with self.assertRaisesRegex(ValueError, "날짜 누락/중복"):
            validate_monthly_plan(plan, 2026, 7)

    def test_rejects_empty_proverbs_column(self):
        plan = self._valid_plan()
        plan["8"][3] = ""

        with self.assertRaisesRegex(ValueError, "잠언"):
            validate_monthly_plan(plan, 2026, 7)

    def test_rejects_unprocessed_template_without_proverbs_values(self):
        plan = self._valid_plan()
        for row in plan.values():
            row[3] = ""

        with self.assertRaisesRegex(ValueError, "잠언"):
            validate_monthly_plan(plan, 2026, 7)

    def test_rejects_qt_verse_outside_bible_database(self):
        plan = self._valid_plan()
        plan["3"][4] = "욥 1:35-51"

        with self.assertRaisesRegex(ValueError, "성경 DB 범위 밖"):
            validate_monthly_plan(plan, 2026, 7)

    def test_rejects_ambiguous_psalm_verse_range(self):
        plan = self._valid_plan()
        plan["1"][2] = "시 119-65-88"

        with self.assertRaisesRegex(ValueError, "시편 값 오류"):
            validate_monthly_plan(plan, 2026, 7)

    def test_rejects_unknown_book_in_reading_plan(self):
        plan = self._valid_plan()
        plan["11"][1] = "엔 10-욥1"

        with self.assertRaisesRegex(ValueError, "구약 성경 권 오류"):
            validate_monthly_plan(plan, 2026, 7)


if __name__ == "__main__":
    unittest.main()
