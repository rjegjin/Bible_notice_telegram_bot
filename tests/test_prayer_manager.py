import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools import prayer_manager
from tools.prayer_manager import (
    approve_latest,
    build_plan,
    format_plan_preview,
    import_image,
    oat_people_for_date,
    send_for_date,
    send_oat_for_date,
    send_today,
)


class PrayerManagerTests(unittest.TestCase):
    def setUp(self):
        self.people = [
            {"name": f"사람{i}", "members": [], "prayers": [f"기도 {i}"]}
            for i in range(1, 14)
        ]

    def test_assigns_three_on_monday_and_two_until_saturday(self):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")

        self.assertEqual(
            [len(plan["assignments"][day]) for day in sorted(plan["assignments"])],
            [3, 2, 2, 2, 2, 2],
        )
        self.assertEqual(plan["assignments"]["2026-08-24"][0], "사람1")
        self.assertEqual(plan["assignments"]["2026-08-29"][-1], "사람13")

    def test_two_columns_keep_order_and_attach_leading_continuation(self):
        class Provider:
            def __init__(self, people):
                self.people = people
                self.calls = 0
                self.schemas = []

            def generate_from_images(self, images, prompt, schema):
                self.calls += 1
                self.schemas.append(schema)
                if self.calls == 1:
                    return {
                        "week_start": "2026-08-23",
                        "week_end": "2026-08-29",
                        "people": self.people[:5],
                    }
                return {"leading_prayers": ["2 이어지는 기도"], "people": self.people[5:]}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "weekly.jpg"
            Image.new("RGB", (20, 20), "white").save(image_path)
            provider = Provider(self.people)
            with patch.object(prayer_manager, "PLAN_DIR", root / "plans"):
                plan_path = import_image(image_path, provider=provider)
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                source_path = root / "plans" / "sources" / "2026-08-23.jpg"
                source_saved = source_path.exists()

        self.assertEqual([person["name"] for person in plan["people"]], [f"사람{i}" for i in range(1, 14)])
        self.assertTrue(source_saved)
        self.assertEqual(plan["people"][4]["prayers"], ["기도 5", "이어지는 기도"])
        self.assertEqual(provider.schemas[0]["schema"]["properties"]["people"]["minItems"], 5)
        self.assertEqual(provider.schemas[0]["schema"]["properties"]["people"]["maxItems"], 6)
        self.assertEqual(provider.schemas[1]["schema"]["properties"]["people"]["minItems"], 8)
        self.assertEqual(provider.schemas[1]["schema"]["properties"]["people"]["maxItems"], 8)

    def test_preview_contains_every_person_and_prayer(self):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        preview = format_plan_preview(plan)
        self.assertEqual(sum(name in preview for name in ("사람1", "사람13")), 2)
        self.assertIn("기도 1", preview)
        self.assertIn("기도 13", preview)

    def test_approval_records_future_only_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
            path = root / "2026-08-23.json"
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            with patch.object(prayer_manager, "PLAN_DIR", root):
                approve_latest()
            approved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(approved["approved"])
        self.assertEqual(approved["delivery_policy"], "future_only")
        self.assertIn("approved_at", approved)

    @patch("tools.prayer_manager.send_telegram", return_value=True)
    def test_one_message_per_person_and_resume_without_duplicates(self, send):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        plan["approved"] = True
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            sent = send_for_date(
                plan,
                date(2026, 8, 24),
                token="token",
                chat_id="chat",
                state_dir=state_dir,
            )
            repeated = send_for_date(
                plan,
                date(2026, 8, 24),
                token="token",
                chat_id="chat",
                state_dir=state_dir,
            )

        self.assertEqual(sent, 3)
        self.assertEqual(repeated, 0)
        self.assertEqual(send.call_count, 3)
        self.assertTrue(all(call.args[0].startswith("🙏 주간 기도제목") for call in send.call_args_list))

    @patch("tools.prayer_manager.send_telegram", return_value=True)
    def test_force_resends_without_deleting_existing_markers(self, send):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        plan["approved"] = True
        day = date(2026, 8, 24)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            first = send_for_date(
                plan, day, token="token", chat_id="owner", state_dir=state_dir
            )
            repeated = send_for_date(
                plan,
                day,
                token="token",
                chat_id="owner",
                state_dir=state_dir,
                force=True,
            )
        self.assertEqual((first, repeated), (3, 3))
        self.assertEqual(send.call_count, 6)

    @patch("tools.prayer_manager.send_for_date")
    def test_unapproved_plan_never_sends(self, send):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        with patch("tools.prayer_manager.load_plan_for", return_value=plan):
            self.assertEqual(send_today(day=date(2026, 8, 24)), 0)
        send.assert_not_called()

    @patch("tools.prayer_manager.send_for_date", return_value=3)
    @patch("tools.prayer_manager.resolve_owner_recipient", return_value=("owner", "BIBLE_OWNER_CHAT_ID"))
    def test_regular_send_defaults_to_owner_private_room(self, resolve_owner, send):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        plan["approved"] = True
        with patch("tools.prayer_manager.load_plan_for", return_value=plan), patch.dict(
            "os.environ", {"TELEGRAM_TOKEN": "token"}, clear=True
        ):
            self.assertEqual(send_today(day=date(2026, 8, 24)), 3)

        resolve_owner.assert_called_once_with()
        self.assertEqual(send.call_args.kwargs["chat_id"], "owner")

    @patch("tools.prayer_manager.send_for_date", return_value=3)
    def test_manual_recall_uses_explicit_chat_and_force(self, send):
        plan = build_plan("2026-08-23", "2026-08-29", self.people, "abc")
        plan["approved"] = True
        with patch("tools.prayer_manager.load_plan_for", return_value=plan), patch.dict(
            prayer_manager.os.environ, {"TELEGRAM_TOKEN": "token"}, clear=True
        ):
            self.assertEqual(
                send_today(
                    day=date(2026, 8, 24),
                    force=True,
                    chat_id="current-owner-chat",
                ),
                3,
            )
        self.assertEqual(send.call_args.kwargs["chat_id"], "current-owner-chat")
        self.assertTrue(send.call_args.kwargs["force"])

    def test_oat_attaches_supplemental_person_after_weekly_anchor(self):
        oat = {
            "people": [
                *[
                    {"name": f"앞사람{i}", "role": "weekly_leader", "weekly_anchor": None, "prayers": [{"id": f"앞사람{i}-01", "text": "기도"}]}
                    for i in range(1, 6)
                ],
                {"name": "정석훈", "role": "weekly_leader", "weekly_anchor": None, "prayers": [{"id": "정석훈-01", "text": "기도"}]},
                {"name": "이준우", "role": "weekly_leader", "weekly_anchor": None, "prayers": [{"id": "이준우-01", "text": "기도"}]},
                *[
                    {"name": f"뒷사람{i}", "role": "weekly_leader", "weekly_anchor": None, "prayers": [{"id": f"뒷사람{i}-01", "text": "기도"}]}
                    for i in range(1, 7)
                ],
                {"name": "심창민", "role": "supplemental", "weekly_anchor": "정석훈", "prayers": [{"id": "심창민-01", "text": "기도"}]},
            ]
        }

        people = oat_people_for_date(oat, date(2026, 9, 9))

        self.assertEqual([person["name"] for person in people], ["정석훈", "심창민", "이준우"])

    @patch("tools.prayer_manager.send_telegram", return_value=True)
    def test_oat_sends_one_rotating_prayer_per_person_without_duplicates(self, send):
        oat = {
            "semester": {"start_date": "2026-09-01", "end_date": "2026-12-31"},
            "delivery": {"start_date": "2026-09-07"},
            "approved": True,
            "people": [
                {
                    "name": "임세범",
                    "role": "weekly_leader",
                    "weekly_anchor": None,
                    "prayers": [
                        {"id": "임세범-01", "text": "첫 기도"},
                        {"id": "임세범-02", "text": "둘째 기도"},
                    ],
                },
                *[
                    {"name": f"사람{i}", "role": "weekly_leader", "weekly_anchor": None, "prayers": [{"id": f"사람{i}-01", "text": "기도"}]}
                    for i in range(2, 14)
                ],
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            sent = send_oat_for_date(
                oat, date(2026, 9, 7), token="token", chat_id="chat", state_dir=state_dir
            )
            repeated = send_oat_for_date(
                oat, date(2026, 9, 7), token="token", chat_id="chat", state_dir=state_dir
            )
            next_week = send_oat_for_date(
                oat, date(2026, 9, 14), token="token", chat_id="chat", state_dir=state_dir
            )

        self.assertEqual((sent, repeated, next_week), (3, 0, 3))
        self.assertEqual(send.call_count, 6)
        self.assertIn("기도 2/2", send.call_args_list[3].args[0])
        self.assertIn("둘째 기도", send.call_args_list[3].args[0])


if __name__ == "__main__":
    unittest.main()
