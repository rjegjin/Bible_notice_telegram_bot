import unittest
from types import SimpleNamespace

from manager_bot import _album_result_message, _message_media, _parse_plan_captions


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


if __name__ == "__main__":
    unittest.main()
