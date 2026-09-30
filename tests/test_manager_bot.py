import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
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
    def test_review_blocks_changed_standby(self):
        from manager_bot import _review_standby
        from tests.test_plan_manager import valid_july_plan
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / '2026_07.json'
            path.write_text(json.dumps(valid_july_plan()))
            with patch('tools.plan_manager.DEFAULT_STANDBY_DIR', root):
                _, _, digest = _review_standby(2026, 7)
                path.write_text(json.dumps(valid_july_plan()) + '\n')
                with self.assertRaisesRegex(ValueError, '변경'):
                    _review_standby(2026, 7, digest)

    def test_builds_historical_bible_send_command(self):
        self.assertEqual(
            _send_command_args(["2026-09-11", "ko"]),
            ["send", "--target", "ko", "--date", "2026-09-11"],
        )

    def test_resolves_weekday_inside_current_sunday_to_saturday_week(self):
        self.assertEqual(_resolve_prayer_day("월", date(2026, 9, 18)), date(2026, 9, 14))
        self.assertEqual(_resolve_prayer_day("토요일", date(2026, 9, 18)), date(2026, 9, 19))


class PlanPublishCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_callback_calls_reviewed_publish_and_reports_success(self):
        from manager_bot import handle_plan_callback
        message = SimpleNamespace(reply_text=AsyncMock())
        query = SimpleNamespace(
            data='plan:publish:2026:10:hash', message=message,
            answer=AsyncMock(), edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=123))
        with patch.dict('os.environ', {'BIBLE_OWNER_CHAT_ID': '123'}), patch(
            'manager_bot._publish_reviewed_plan'
        ) as publish:
            await handle_plan_callback(update, None)
        publish.assert_called_once_with(2026, 10, 'hash')
        self.assertIn('게시 완료', message.reply_text.call_args.args[0])

    async def test_non_owner_cannot_publish(self):
        from manager_bot import handle_plan_callback
        message = SimpleNamespace(reply_text=AsyncMock())
        query = SimpleNamespace(
            data='plan:publish:2026:10:hash', message=message,
            answer=AsyncMock(), edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=456))
        with patch.dict('os.environ', {'BIBLE_OWNER_CHAT_ID': '123'}), patch(
            'manager_bot._publish_reviewed_plan'
        ) as publish:
            await handle_plan_callback(update, None)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
