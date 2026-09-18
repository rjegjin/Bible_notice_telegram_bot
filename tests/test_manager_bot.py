import unittest
from datetime import date
from types import SimpleNamespace

from manager_bot import (
    _album_result_message,
    _message_media,
    _parse_plan_captions,
    _resolve_prayer_day,
    _send_command_args,
)


class PlanCaptionTests(unittest.TestCase):
    def test_accepts_two_commands_in_album_caption(self):
        self.assertEqual(
            _parse_plan_captions("/qt 2026 09\n/br 2026 09"),
            [("QT", "2026", "09"), ("BR", "2026", "09")],
        )

    def test_rejects_caption_with_unrecognized_lines(self):
        self.assertEqual(_parse_plan_captions("/qt 2026 09\n메모"), [])

    def test_accepts_photo_or_image_document(self):
        photo = object()
        document = object()
        self.assertIs(_message_media(SimpleNamespace(photo=[photo], document=None)), photo)
        self.assertIs(_message_media(SimpleNamespace(photo=[], document=document)), document)

    def test_album_success_message_does_not_repeat_waiting_state(self):
        message = _album_result_message(
            [("BR", "2026", "09"), ("QT", "2026", "09")],
            ["⏳ BR 저장 완료 · QT 이미지 대기 중", "✅ standby 생성: 2026_09.json"],
        )
        self.assertIn("BR 저장 완료", message)
        self.assertIn("QT 저장 완료", message)
        self.assertIn("standby JSON 생성", message)
        self.assertIn("운영 반영 안 됨", message)
        self.assertNotIn("대기 중", message)


class ManualSendTests(unittest.TestCase):
    def test_builds_historical_bible_send_command(self):
        self.assertEqual(
            _send_command_args(["2026-09-11", "ko"]),
            ["send", "--target", "ko", "--date", "2026-09-11"],
        )

    def test_resolves_weekday_inside_current_sunday_to_saturday_week(self):
        self.assertEqual(_resolve_prayer_day("월", date(2026, 9, 18)), date(2026, 9, 14))
        self.assertEqual(_resolve_prayer_day("토요일", date(2026, 9, 18)), date(2026, 9, 19))


if __name__ == "__main__":
    unittest.main()
