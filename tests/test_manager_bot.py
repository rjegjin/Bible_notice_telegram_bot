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
    def test_reviewed_publish_promotes_snapshot_to_runtime_plan(self):
        from manager_bot import _review_standby, _publish_reviewed_plan
        from tools.plan_manager import PlanManager
        from tests.test_plan_manager import valid_july_plan
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            standby = root / 'standby'
            standby.mkdir()
            approved = valid_july_plan()
            (standby / '2026_07.json').write_text(json.dumps(approved))
            manager = PlanManager(root / 'runtime')
            with patch('tools.plan_manager.DEFAULT_STANDBY_DIR', standby), patch(
                'tools.plan_manager.PlanManager', return_value=manager
            ), patch('tools.plan_manager.upsert_quiet_time_tab', return_value='verified'):
                _, _, digest = _review_standby(2026, 7)
                _publish_reviewed_plan(2026, 7, digest)
            self.assertEqual(manager.load(2026, 7), approved)

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
    async def test_command_errors_are_reported_without_exception_secrets(self):
        import manager_bot as bot
        message = SimpleNamespace(reply_text=AsyncMock())
        with patch('manager_bot.run_bot') as run:
            bot.main()
        handler = run.call_args.kwargs.get('error_handler')
        self.assertIsNotNone(handler, '처리 실패를 Telegram에 표시해야 한다')
        await handler(SimpleNamespace(effective_message=message), SimpleNamespace(error=RuntimeError('secret-token')))
        reply = message.reply_text.call_args.args[0]
        self.assertIn('❌', reply)
        self.assertIn('RuntimeError', reply)
        self.assertNotIn('secret-token', reply)

    async def test_unknown_command_gets_help_instead_of_silence(self):
        import manager_bot as bot
        with patch('manager_bot.run_bot') as run:
            bot.main()
        handlers = run.call_args.args[1]
        fallback = [handler for handler in handlers if handler.callback.__name__ == 'cmd_unknown']
        self.assertEqual(len(fallback), 1, '없는 명령도 오류를 표시해야 한다')
        message = SimpleNamespace(reply_text=AsyncMock())
        await fallback[0].callback(SimpleNamespace(effective_message=message), None)
        self.assertIn('/help', message.reply_text.call_args.args[0])

    async def test_plan_publish_command_opens_review(self):
        from manager_bot import cmd_plan
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message, effective_chat=SimpleNamespace(id=123))
        context = SimpleNamespace(args=['publish', '2026', '10'])
        with patch.dict('os.environ', {'BIBLE_OWNER_CHAT_ID': '123'}), patch(
            'manager_bot._show_plan_review', new_callable=AsyncMock
        ) as review:
            await cmd_plan(update, context)
        review.assert_awaited_once_with(message, 2026, 10)
        self.assertEqual(context.args, ['publish', '2026', '10'])

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
