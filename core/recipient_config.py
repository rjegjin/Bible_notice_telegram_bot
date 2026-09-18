import os
from collections.abc import Mapping


def resolve_owner_recipient(
    explicit_chat_id=None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """개인 요약 수신처와 그 설정 출처를 반환한다."""
    env = environ if environ is not None else os.environ
    if explicit_chat_id is not None:
        return str(explicit_chat_id), "현재 대화방"

    owner_chat_id = env.get("BIBLE_OWNER_CHAT_ID")
    if owner_chat_id:
        return owner_chat_id, "BIBLE_OWNER_CHAT_ID"

    legacy_chat_id = env.get("EN_CHAT_ID")
    if legacy_chat_id:
        return legacy_chat_id, "EN_CHAT_ID (호환 fallback)"

    raise RuntimeError(
        "개인 요약 수신처가 없습니다. BIBLE_OWNER_CHAT_ID를 설정하거나 "
        "관리봇의 현재 대화방에서 실행해주세요."
    )


def build_trigger_args(command: str, chat_id=None) -> list[str]:
    args = [command]
    if chat_id is None:
        return args
    if command == "summary":
        return [command, "--chat-id", str(chat_id)]
    if command == "run":
        return [command, "--owner-chat-id", str(chat_id)]
    return args


ROOM_CONFIG = {
    "ko": ("KO_CHAT_ID", "KO"),
    "en": ("EN_GROUP_CHAT_ID", "EN"),
    "mn": ("MN_CHAT_ID", "MN"),
}


def resolve_broadcast_recipients(
    target: str = "all",
    environ: Mapping[str, str] | None = None,
) -> list[tuple[str, str, str]]:
    """(방 key, chat ID, 언어) 목록을 버튼 target에 맞게 반환한다."""
    env = environ if environ is not None else os.environ
    room_keys = list(ROOM_CONFIG) if target == "all" else [target]
    if target == "all" and not env.get("EN_GROUP_CHAT_ID"):
        room_keys.remove("en")
    if any(key not in ROOM_CONFIG for key in room_keys):
        raise ValueError(f"지원하지 않는 발송 대상: {target}")

    recipients = []
    for key in room_keys:
        env_name, language = ROOM_CONFIG[key]
        chat_id = env.get(env_name)
        if not chat_id:
            raise RuntimeError(f"{key.upper()}방 수신처 {env_name}가 설정되지 않았습니다.")
        recipients.append((key, chat_id, language))
    return recipients


def build_room_send_args(target: str) -> list[str]:
    return ["send", "--target", target]
