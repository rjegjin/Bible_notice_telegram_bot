"""주간 기도제목 이미지 OCR, 월~토 배정, Telegram 발송."""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ai.provider import get_provider
from common.bot_common import send_telegram
from core.recipient_config import resolve_owner_recipient


BASE_DIR = Path(__file__).resolve().parent.parent
PLAN_DIR = BASE_DIR / "data" / "prayers"
STATE_DIR = PLAN_DIR / "sent"
OAT_STATE_DIR = STATE_DIR / "oat"
DAY_NAMES = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일")
DAILY_COUNTS = (3, 2, 2, 2, 2, 2)

def _column_schema(min_count: int, include_dates: bool, include_leading: bool = False, max_count: int | None = None) -> dict:
    max_count = min_count if max_count is None else max_count
    required = ["people"]
    properties = {
        "people": {
            "type": "array",
            "minItems": min_count,
            "maxItems": max_count,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "members", "prayers"],
                "properties": {
                    "name": {"type": "string"},
                    "members": {"type": "array", "items": {"type": "string"}},
                    "prayers": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                    },
                },
            },
        }
    }
    if include_dates:
        required[:0] = ["week_start", "week_end"]
        properties = {
            "week_start": {"type": "string", "description": "일요일, YYYY-MM-DD"},
            "week_end": {"type": "string", "description": "토요일, YYYY-MM-DD"},
            **properties,
        }
    if include_leading:
        required.insert(0, "leading_prayers")
        properties = {
            "leading_prayers": {"type": "array", "items": {"type": "string"}},
            **properties,
        }
    return {
        "name": "weekly_prayer_column",
        "strict": True,
        "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
        },
    }

PROMPT = """이 이미지는 한국어 '주간기도제목' 문서의 한쪽 세로 칼럼이다. 원문 그대로 OCR하라.
- 둥근 이름표가 붙은 개인 구역만 위에서 아래 순서로 반환한다.
- name은 둥근 이름표의 이름, members는 바로 오른쪽 노란 칸의 이름들, prayers는 아래 베이지 칸의 빨간 번호별 기도문이다.
- 문장을 요약하거나 교정하지 말고 보이는 내용을 충실히 옮긴다. 성경 구절과 괄호도 보존한다.
- 둥근 이름표가 없는 '[전체 기도제목]'과 칼럼 맨 위의 번호 문단은 제외한다.
- 빨간 번호가 없는 별표 메모는 직전 번호 기도문 끝에 붙인다.
"""


def _clean(value: str) -> str:
    return " ".join(str(value).split())


def _clean_prayers(values) -> list[str]:
    prayers = []
    for value in values:
        cleaned = _clean(value)
        if not cleaned:
            continue
        cleaned = re.sub(r"^\d+\s*", "", cleaned)
        if cleaned.startswith("*") and prayers:
            prayers[-1] += f" {cleaned}"
        else:
            prayers.append(cleaned)
    return prayers


def build_plan(week_start: str, week_end: str, people: list[dict], source_sha256: str) -> dict:
    start = date.fromisoformat(week_start)
    end = date.fromisoformat(week_end)
    if start.weekday() != 6 or end != start + timedelta(days=6):
        raise ValueError("주간 날짜는 일요일부터 토요일까지여야 합니다.")
    if len(people) != 13:
        raise ValueError(f"개인 기도제목은 정확히 13명이어야 합니다: {len(people)}명")

    normalized = []
    for person in people:
        item = {
            "name": _clean(person.get("name", "")),
            "members": [_clean(value) for value in person.get("members", []) if _clean(value)],
            "prayers": _clean_prayers(person.get("prayers", [])),
        }
        if not item["name"] or not item["prayers"]:
            raise ValueError("모든 사람에게 이름과 한 개 이상의 기도제목이 필요합니다.")
        normalized.append(item)
    if len({person["name"] for person in normalized}) != 13:
        raise ValueError("13명의 이름은 서로 달라야 합니다.")

    assignments = {}
    offset = 0
    for day_offset, count in enumerate(DAILY_COUNTS, start=1):
        assignments[(start + timedelta(days=day_offset)).isoformat()] = [
            person["name"] for person in normalized[offset:offset + count]
        ]
        offset += count
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "source_sha256": source_sha256,
        "approved": False,
        "people": normalized,
        "assignments": assignments,
    }


def import_image(image_path: str | Path, *, replace: bool = False, provider=None) -> Path:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    active_provider = provider or get_provider()
    with Image.open(path) as image:
        middle = image.width // 2
        left = image.crop((0, 0, middle, image.height))
        right = image.crop((middle, 0, image.width, image.height))
        left_result = active_provider.generate_from_images(
            [left],
            PROMPT + "\n이 왼쪽 칼럼에서는 제목의 주간 시작일과 종료일도 읽고, 보이는 개인 구역 5~6명을 반환한다.",
            _column_schema(5, True, max_count=6),
        )
        left_count = len(left_result["people"])
        if left_count not in (5, 6):
            raise ValueError(f"왼쪽 칼럼 개인 구역은 5~6명이어야 합니다: {left_count}명")
        right_count = 13 - left_count
        right_result = active_provider.generate_from_images(
            [right],
            PROMPT + (
                f"\n이 오른쪽 칼럼에서 둥근 이름표가 붙은 개인 구역을 정확히 {right_count}명 반환한다. "
                "첫 이름표 위에 있는 빨간 번호 문단은 왼쪽 칼럼 마지막 사람의 이어지는 기도문이므로 "
                "제외하지 말고 leading_prayers에 반환한다. 없으면 빈 배열이다."
            ),
            _column_schema(right_count, False, True),
        )
    left_result["people"][-1]["prayers"].extend(right_result["leading_prayers"])
    plan = build_plan(
        left_result["week_start"],
        left_result["week_end"],
        left_result["people"] + right_result["people"],
        source_sha256,
    )

    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    destination = PLAN_DIR / f"{plan['week_start']}.json"
    if destination.exists() and not replace:
        raise FileExistsError(f"이미 존재합니다: {destination} (--replace로 교체)")
    if destination.exists():
        backup_dir = PLAN_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(destination, backup_dir / f"{destination.stem}_{stamp}.json")
    source_dir = PLAN_DIR / "sources"
    source_dir.mkdir(exist_ok=True)
    source_path = source_dir / f"{plan['week_start']}{path.suffix.lower() or '.jpg'}"
    source_temporary = source_path.with_suffix(source_path.suffix + ".tmp")
    shutil.copy2(path, source_temporary)
    source_temporary.replace(source_path)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination


def load_plan_for(day: date) -> dict | None:
    if not PLAN_DIR.exists():
        return None
    for path in sorted(PLAN_DIR.glob("????-??-??.json"), reverse=True):
        plan = json.loads(path.read_text(encoding="utf-8"))
        if plan["week_start"] <= day.isoformat() <= plan["week_end"]:
            return plan
    return None


def load_oat_plan_for(day: date) -> dict | None:
    for path in sorted(PLAN_DIR.glob("*_oat.json"), reverse=True):
        plan = json.loads(path.read_text(encoding="utf-8"))
        semester = plan.get("semester", {})
        start = plan.get("delivery", {}).get("start_date", semester.get("start_date"))
        end = semester.get("end_date")
        if start and end and start <= day.isoformat() <= end:
            return plan
    return None


def approve_latest() -> Path:
    plans = sorted(PLAN_DIR.glob("????-??-??.json"), reverse=True)
    if not plans:
        raise FileNotFoundError("승인할 주간 기도 plan이 없습니다.")
    path = plans[0]
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["approved"] = True
    plan["approved_at"] = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
    plan["delivery_policy"] = "future_only"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def format_plan_preview(plan: dict) -> str:
    lines = [f"🙏 주간기도 OCR 검토 · {plan['week_start']}~{plan['week_end']}"]
    for person in plan.get("people", []):
        lines.append(f"\n👤 {person['name']}")
        if person.get("members"):
            lines.append(f"함께 기도: {', '.join(person['members'])}")
        lines.extend(f"{index}. {text}" for index, text in enumerate(person.get("prayers", []), 1))
    lines.append("\n검토 후 /prayerapprove · 승인 이전 날짜는 자동 보충 발송하지 않음")
    return "\n".join(lines)


def format_message(person: dict, day: date, position: int, total: int) -> str:
    lines = [
        f"🙏 주간 기도제목 · {DAY_NAMES[day.weekday()]} ({position}/{total})",
        f"\n👤 {person['name']}",
    ]
    if person["members"]:
        lines.append(f"🤝 함께 기도: {', '.join(person['members'])}")
    lines.extend(f"\n{i}. {prayer}" for i, prayer in enumerate(person["prayers"], 1))
    return "\n".join(lines)


def oat_people_for_date(oat_plan: dict, day: date) -> list[dict]:
    if day.weekday() >= len(DAILY_COUNTS):
        return []
    leaders = [
        person for person in oat_plan.get("people", []) if person.get("role") == "weekly_leader"
    ]
    if len(leaders) != 13:
        raise ValueError(f"OAT 주간 대표는 정확히 13명이어야 합니다: {len(leaders)}명")
    supplementals = [
        person for person in oat_plan.get("people", []) if person.get("role") == "supplemental"
    ]
    offset = sum(DAILY_COUNTS[:day.weekday()])
    daily_leaders = leaders[offset:offset + DAILY_COUNTS[day.weekday()]]
    selected = []
    for person in daily_leaders:
        selected.append(person)
        selected.extend(
            supplemental
            for supplemental in supplementals
            if supplemental.get("weekly_anchor") == person["name"]
        )
    return selected


def format_oat_message(
    person: dict,
    prayer: dict,
    prayer_number: int,
    day: date,
    position: int,
    total: int,
) -> str:
    lines = [
        f"🙏 2026년 2학기 OAT 기도 · {DAY_NAMES[day.weekday()]} ({position}/{total})",
        f"\n👤 {person['name']}",
        f"📌 기도 {prayer_number}/{len(person['prayers'])}",
    ]
    if person.get("role") == "supplemental":
        lines.append(f"🤝 {person['weekly_anchor']}과 함께 발송")
    lines.append(f"\n{prayer['text']}")
    return "\n".join(lines)


def send_for_date(
    plan: dict,
    day: date,
    *,
    token: str,
    chat_id: str,
    state_dir: Path = STATE_DIR,
    dry_run: bool = False,
) -> int:
    people_by_name = {person["name"]: person for person in plan.get("people", [])}
    people = [
        people_by_name[name]
        for name in plan.get("assignments", {}).get(day.isoformat(), [])
    ]
    sent = 0
    for index, person in enumerate(people, 1):
        marker = state_dir / day.isoformat() / f"{index:02d}.sent"
        if marker.exists() and not dry_run:
            continue
        message = format_message(person, day, index, len(people))
        if dry_run:
            print(message, "\n")
            sent += 1
            continue
        if not send_telegram(message, token=token, chat_id=chat_id, parse_mode=None):
            raise RuntimeError(f"기도제목 발송 실패: {person['name']}")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        sent += 1
    return sent


def send_oat_for_date(
    oat_plan: dict,
    day: date,
    *,
    token: str,
    chat_id: str,
    state_dir: Path = OAT_STATE_DIR,
    dry_run: bool = False,
) -> int:
    delivery_start = date.fromisoformat(oat_plan["delivery"]["start_date"])
    week_index = (day - delivery_start).days // 7
    people = oat_people_for_date(oat_plan, day)
    sent = 0
    for position, person in enumerate(people, 1):
        prayer_index = week_index % len(person["prayers"])
        prayer = person["prayers"][prayer_index]
        marker = state_dir / day.isoformat() / f"{position:02d}-{prayer['id']}.sent"
        if marker.exists() and not dry_run:
            continue
        message = format_oat_message(
            person, prayer, prayer_index + 1, day, position, len(people)
        )
        if dry_run:
            print(message, "\n")
            sent += 1
            continue
        if not send_telegram(message, token=token, chat_id=chat_id, parse_mode=None):
            raise RuntimeError(f"OAT 기도제목 발송 실패: {person['name']}")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        sent += 1
    return sent


def send_today(*, day: date | None = None, dry_run: bool = False) -> int:
    target_day = day or datetime.now(ZoneInfo("Asia/Seoul")).date()
    plan = load_plan_for(target_day)
    if not plan or target_day.isoformat() not in plan.get("assignments", {}):
        print(f"ℹ️ 기도제목 배정 없음: {target_day.isoformat()}")
        return 0
    if not plan.get("approved") and not dry_run:
        print(f"⚠️ 미승인 기도제목: {plan['week_start']} (prayer approve 필요)")
        return 0
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = "dry-run" if dry_run else os.getenv("PRAYER_CHAT_ID")
    if not chat_id:
        chat_id, _ = resolve_owner_recipient()
    if not dry_run and (not token or not chat_id):
        raise RuntimeError("TELEGRAM_TOKEN과 owner 개인방 수신처가 필요합니다.")
    return send_for_date(
        plan, target_day, token=token or "dry-run", chat_id=chat_id, dry_run=dry_run
    )


def send_oat_today(*, day: date | None = None, dry_run: bool = False) -> int:
    target_day = day or datetime.now(ZoneInfo("Asia/Seoul")).date()
    oat_plan = load_oat_plan_for(target_day)
    if not oat_plan or not oat_people_for_date(oat_plan, target_day):
        print(f"ℹ️ OAT 기도제목 배정 없음: {target_day.isoformat()}")
        return 0
    if not oat_plan.get("approved") and not dry_run:
        print(f"⚠️ 미승인 OAT 기도제목: {target_day.isoformat()}")
        return 0
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = "dry-run" if dry_run else os.getenv("PRAYER_CHAT_ID")
    if not chat_id:
        chat_id, _ = resolve_owner_recipient()
    if not dry_run and (not token or not chat_id):
        raise RuntimeError("TELEGRAM_TOKEN과 owner 개인방 수신처가 필요합니다.")
    return send_oat_for_date(
        oat_plan,
        target_day,
        token=token or "dry-run",
        chat_id=chat_id,
        dry_run=dry_run,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="주간 기도제목 이미지 관리")
    subparsers = parser.add_subparsers(dest="command", required=True)
    import_parser = subparsers.add_parser("import", help="이미지 OCR 후 13명 주간 plan 저장")
    import_parser.add_argument("image")
    import_parser.add_argument("--replace", action="store_true")
    subparsers.add_parser("approve", help="가장 최근 OCR 결과 승인")
    subparsers.add_parser("preview", help="가장 최근 OCR 전체 기도문 검토")
    send_parser = subparsers.add_parser("send", help="오늘 배정된 사람을 한 메시지씩 발송")
    send_parser.add_argument("--date", type=date.fromisoformat)
    send_parser.add_argument("--dry-run", action="store_true")
    oat_send_parser = subparsers.add_parser("oat-send", help="오늘 배정된 OAT 기도를 별도 발송")
    oat_send_parser.add_argument("--date", type=date.fromisoformat)
    oat_send_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "import":
        path = import_image(args.image, replace=args.replace)
        plan = json.loads(path.read_text(encoding="utf-8"))
        print(f"✅ {path.name}: {len(plan['people'])}명, 월 3명 + 화~토 각 2명")
        for day, names in plan["assignments"].items():
            print(f"- {day}: {', '.join(names)}")
        print(format_plan_preview(plan))
    elif args.command == "approve":
        path = approve_latest()
        print(f"✅ 승인 완료: {path.name}\n과거 날짜는 건너뛰고 승인 이후 일정만 발송합니다.")
    elif args.command == "preview":
        plans = sorted(PLAN_DIR.glob("????-??-??.json"), reverse=True)
        if not plans:
            raise FileNotFoundError("검토할 주간 기도 plan이 없습니다.")
        print(format_plan_preview(json.loads(plans[0].read_text(encoding="utf-8"))))
    elif args.command == "send":
        count = send_today(day=args.date, dry_run=args.dry_run)
        print(f"✅ 기도제목 {count}명 {'미리보기' if args.dry_run else '발송'} 완료")
    else:
        count = send_oat_today(day=args.date, dry_run=args.dry_run)
        print(f"✅ OAT 기도제목 {count}명 {'미리보기' if args.dry_run else '발송'} 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
