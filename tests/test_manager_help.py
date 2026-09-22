"""/help 가 이미지 등록 절차를 실제 동작과 같게 설명하는지 확인.

이 봇의 이미지 등록은 caption 규칙이 전부라, 문서가 코드와 어긋나면
"어떻게 하는지 기억이 안 난다"가 그대로 재발한다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SRC = (Path(__file__).resolve().parents[1] / "manager_bot.py").read_text(encoding="utf-8")
HELP = SRC[SRC.index('HELP_TEXT = """'):SRC.index('async def cmd_help')]


def test_help_registered():
    assert 'CommandHandler("help",    cmd_help)' in SRC
    assert "run_bot(TOKEN, handlers, post_init=post_init)" in SRC


def test_help_covers_every_command():
    registered = set(re.findall(r'CommandHandler\("(\w+)"', SRC))
    # start 는 manage 별칭이라 따로 적지 않는다
    for cmd in registered - {"start"}:
        assert f"/{cmd}" in HELP, f"/{cmd} 가 /help 에 없다"


def test_help_caption_examples_match_parser():
    from manager_bot import _parse_plan_captions

    # /help 가 보여주는 앨범 caption 예시가 실제로 파싱되어야 한다
    example = "\n".join(
        line.strip() for line in HELP.splitlines()
        if line.strip().startswith(("/qt ", "/br "))
    )
    assert example, "help 에 caption 예시가 없다"
    parsed = _parse_plan_captions(example)
    assert {kind for kind, _, _ in parsed} == {"QT", "BR"}
    assert len({(y, m) for _, y, m in parsed}) == 1


def test_help_states_publish_is_still_needed():
    """이미지 등록만으로는 운영 반영이 안 된다는 사실이 빠지면 안 된다."""
    assert "plan publish" in HELP
    assert "반영" in HELP


def test_help_states_owner_only():
    assert "owner" in HELP
