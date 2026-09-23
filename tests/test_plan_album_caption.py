"""앨범 caption: 순서 무관 + 나중에 edit 해도 동작.

caption 줄 순서와 사진 순서를 사람이 맞추게 하면 조용히 뒤바뀐 달이 만들어진다.
그리고 caption 없이 올린 뒤 나중에 붙이는 건 실제로 자주 하는 순서다.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("TELEGRAM_TOKEN", "x")

import manager_bot as mb


class FakeMessage:
    def __init__(self, message_id, media_group_id=None, caption=None, media="m"):
        self.message_id = message_id
        self.media_group_id = media_group_id
        self.caption = caption
        self.photo = [media]
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


def test_caption_parser_accepts_either_order():
    assert mb._parse_plan_captions("/qt 2026 10\n/br 2026 10")
    assert mb._parse_plan_captions("/br 2026 10\n/qt 2026 10")


def test_album_photos_are_remembered_and_returned_in_order():
    mb._PENDING_ALBUMS.clear()
    first = FakeMessage(11, media_group_id="g1", media="A")
    second = FakeMessage(12, media_group_id="g1", media="B")
    mb._remember_album_photo(first)
    mb._remember_album_photo(second)
    later = FakeMessage(11, media_group_id="g1", caption="/qt 2026 10\n/br 2026 10", media="A")
    assert mb._remembered_album_photos(later) == ["A", "B"]


def test_single_photo_is_not_remembered():
    mb._PENDING_ALBUMS.clear()
    mb._remember_album_photo(FakeMessage(1, media_group_id=None))
    assert not mb._PENDING_ALBUMS


def test_kinds_follow_the_image_not_the_caption_order(monkeypatch):
    """caption은 /qt 먼저인데 실제 사진은 BR이 먼저인 경우."""
    commands = [("QT", "2026", "10"), ("BR", "2026", "10")]
    by_path = {"p1": "BR", "p2": "QT"}
    monkeypatch.setattr(mb, "_classify_photo", lambda path: _async(by_path[path]))

    kinds, note = asyncio.run(mb._assign_kinds(["p1", "p2"], commands))
    assert kinds == ["BR", "QT"], "이미지 판별이 caption 순서를 이겨야 한다"
    assert "판별" in note


def test_falls_back_to_caption_order_when_classification_fails(monkeypatch):
    commands = [("QT", "2026", "10"), ("BR", "2026", "10")]
    monkeypatch.setattr(mb, "_classify_photo", lambda path: _async(None))

    kinds, note = asyncio.run(mb._assign_kinds(["p1", "p2"], commands))
    assert kinds == ["QT", "BR"]
    assert "실패" in note


def test_album_rejects_mismatched_photo_and_command_counts():
    message = FakeMessage(1, media_group_id="g")
    asyncio.run(mb._process_plan_album(message, ["only-one"], [("QT", "2026", "10"), ("BR", "2026", "10")]))
    assert "수가 다릅니다" in message.replies[0]


def test_album_requires_one_br_and_one_qt():
    message = FakeMessage(1, media_group_id="g")
    asyncio.run(mb._process_plan_album(message, ["a", "b"], [("QT", "2026", "10"), ("QT", "2026", "10")]))
    assert "하나씩" in message.replies[0]


def test_edited_message_updates_are_handled():
    src = (Path(__file__).resolve().parents[1] / "manager_bot.py").read_text(encoding="utf-8")
    assert "filters.UpdateType.EDITED_MESSAGE" in src
    assert "update.effective_message" in src


async def _await(value):
    return value


def _async(value):
    return _await(value)
