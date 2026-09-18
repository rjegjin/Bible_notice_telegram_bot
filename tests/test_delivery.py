import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from core.bible_sender import deliver_daily


class DailyDeliveryTests(unittest.IsolatedAsyncioTestCase):
    @patch("core.bible_sender.send_only_summaries", new_callable=AsyncMock)
    @patch("core.bible_sender.resolve_owner_recipient", return_value=("200", "EN_CHAT_ID fallback"))
    @patch("core.bible_sender.broadcast_messages", new_callable=AsyncMock, return_value=True)
    async def test_groups_receive_passages_and_owner_receives_summaries_only(
        self, broadcast, resolve_owner, summaries
    ):
        now = datetime(2026, 7, 15, 6, 0)

        result = await deliver_daily(now)

        self.assertTrue(result)
        broadcast.assert_awaited_once_with(now, target="all")
        summaries.assert_awaited_once_with("200", now)

    @patch("core.bible_sender.send_only_summaries", new_callable=AsyncMock)
    @patch("core.bible_sender.broadcast_messages", new_callable=AsyncMock, return_value=False)
    async def test_owner_summary_is_not_sent_when_group_delivery_fails(
        self, broadcast, summaries
    ):
        result = await deliver_daily(datetime(2026, 7, 15, 6, 0))

        self.assertFalse(result)
        summaries.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
