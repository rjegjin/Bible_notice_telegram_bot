import unittest

from core.recipient_config import (
    build_room_send_args,
    build_trigger_args,
    resolve_broadcast_recipients,
    resolve_owner_recipient,
)


class OwnerRecipientTests(unittest.TestCase):
    def test_explicit_current_chat_has_highest_priority(self):
        recipient = resolve_owner_recipient(
            12345,
            {"BIBLE_OWNER_CHAT_ID": "999", "EN_CHAT_ID": "888"},
        )
        self.assertEqual(recipient, ("12345", "현재 대화방"))

    def test_named_bible_owner_setting_precedes_legacy_english_chat(self):
        recipient = resolve_owner_recipient(
            environ={"BIBLE_OWNER_CHAT_ID": "999", "EN_CHAT_ID": "888"}
        )
        self.assertEqual(recipient, ("999", "BIBLE_OWNER_CHAT_ID"))

    def test_attendance_chat_is_not_used_as_fallback(self):
        with self.assertRaisesRegex(RuntimeError, "BIBLE_OWNER_CHAT_ID"):
            resolve_owner_recipient(environ={"ATTENDANCE_TELEGRAM_CHAT_ID": "777"})

    def test_manager_summary_targets_the_current_chat(self):
        self.assertEqual(
            build_trigger_args("summary", 12345),
            ["summary", "--chat-id", "12345"],
        )

    def test_manager_run_targets_owner_summary_to_current_chat(self):
        self.assertEqual(
            build_trigger_args("run", 12345),
            ["run", "--owner-chat-id", "12345"],
        )


class BroadcastRecipientTests(unittest.TestCase):
    def setUp(self):
        self.environ = {
            "KO_CHAT_ID": "100",
            "EN_CHAT_ID": "200",
            "EN_GROUP_CHAT_ID": "250",
            "MN_CHAT_ID": "300",
        }

    def test_each_group_target_selects_only_that_group(self):
        self.assertEqual(
            resolve_broadcast_recipients("ko", self.environ),
            [("ko", "100", "KO")],
        )
        self.assertEqual(
            resolve_broadcast_recipients("en", self.environ),
            [("en", "250", "EN")],
        )
        self.assertEqual(
            resolve_broadcast_recipients("mn", self.environ),
            [("mn", "300", "MN")],
        )

    def test_all_target_excludes_owner_private_room_from_full_passages(self):
        self.assertEqual(
            resolve_broadcast_recipients("all", self.environ),
            [
                ("ko", "100", "KO"),
                ("en", "250", "EN"),
                ("mn", "300", "MN"),
            ],
        )

    def test_all_keeps_working_before_english_group_is_configured(self):
        del self.environ["EN_GROUP_CHAT_ID"]
        self.assertEqual(
            resolve_broadcast_recipients("all", self.environ),
            [
                ("ko", "100", "KO"),
                ("mn", "300", "MN"),
            ],
        )

    def test_room_button_builds_explicit_target_argument(self):
        self.assertEqual(build_room_send_args("mn"), ["send", "--target", "mn"])


if __name__ == "__main__":
    unittest.main()
