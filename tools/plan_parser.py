import logging
import os
import sys
import json
import re
import calendar
import configparser
import sqlite3
import traceback
import PIL.Image
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

from ai.interfaces import AIProviderError
from ai.provider import get_provider

from tools.hwpx_plan_parser import (
    find_hwpx_sources,
    merge_monthly_plan,
    parse_br_hwpx,
    parse_qt_hwpx,
)

# 프로젝트 루트 경로 추가 (core 모듈 임포트용)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.bible_scripture_resolver import BIBLE_MAP
from core.bible_scripture_resolver import DB_FILE

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bible_bot.plan_parser")
PARSER_SETTINGS_PATH = Path(BASE_DIR) / "config" / "plan_parser.ini"


def is_hwpx_parsing_enabled(settings_path=PARSER_SETTINGS_PATH):
    """HWPX parsing 사용 여부. 설정이 없거나 잘못되면 안전하게 OFF로 둔다."""
    config = configparser.ConfigParser()
    config.read(settings_path, encoding="utf-8")
    try:
        return config.getboolean("sources", "hwpx_enabled", fallback=False)
    except ValueError:
        return False


def set_hwpx_parsing_enabled(enabled, settings_path=PARSER_SETTINGS_PATH):
    """HWPX parsing toggle을 로컬 설정 파일에 원자적으로 저장한다."""
    settings_path = Path(settings_path)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config["sources"] = {"hwpx_enabled": "true" if enabled else "false"}
    temporary = settings_path.with_suffix(settings_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        config.write(stream)
    os.replace(temporary, settings_path)
    return enabled

# ==========================================
# ⚙️ 경로 및 환경 설정
# ==========================================

# [보안 & 편의] 중앙 .env 로드 로직 (root/.secrets/.env 우선)
def load_env_centralized():
    central_secrets = Path(BASE_DIR).parent / ".secrets" / ".env"
    if central_secrets.exists():
        load_dotenv(central_secrets)
        return True
    local_env = os.path.join(BASE_DIR, '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)
        return True
    return False

load_env_centralized()

FULL_TO_ABBR = {
    "마태복음": "마", "마가복음": "막", "누가복음": "눅", "요한복음": "요", "사도행전": "행",
    "로마서": "롬", "고린도전서": "고전", "고린도후서": "고후", "갈라디아서": "갈", "에베소서": "엡",
    "빌립보서": "빌", "골로새서": "골", "데살로니가전서": "살전", "데살로니가후서": "살후",
    "디모데전서": "딤전", "디모데후서": "딤후", "디도서": "딛", "빌레몬서": "몬", "히브리서": "히",
    "야고보서": "약", "베드로전서": "벧전", "베드로후서": "벧후", "요한일서": "요일",
    "요한이서": "요이", "요한삼서": "요삼", "유다서": "유", "요한계시록": "계",
    "창세기": "창", "출애굽기": "출", "레위기": "레", "민수기": "민", "신명기": "신",
    "여호수아": "수", "사사기": "삿", "룻기": "룻", "사무엘상": "삼상", "사무엘하": "삼하",
    "열왕기상": "왕상", "열왕기하": "왕하", "역대상": "대상", "역대하": "대하", "에스라": "스",
    "느헤미야": "느", "에스더": "에", "욥기": "욥", "시편": "시", "잠언": "잠", "전도서": "전",
    "아가": "아", "이사야": "사", "예레미야": "렘", "애가": "애", "예레미야애가": "애",
    "에스겔": "겔", "다니엘": "단", "호세아": "호", "요엘": "욜", "아모스": "암",
    "오바댜": "옵", "요나": "욘", "미가": "미", "나훔": "나", "하박국": "합",
    "스바냐": "습", "학개": "학", "스가랴": "슥", "말라기": "말"
}
OCR_BOOK_FIXES = {"엔": "에"}

# OpenAI Structured Outputs(strict json_schema)는 임의 개수의 동적 키(1~31일)를
# 가진 object를 지원하지 않으므로, "일자별 항목의 배열"로 스키마를 고정한다.
# 응답을 받은 뒤 기존 {"1": [...], "2": [...]} 형태로 변환해 하위 로직을 그대로 재사용한다.
BR_PLAN_SCHEMA = {
    "name": "bible_reading_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "integer", "description": "1부터 시작하는 날짜"},
                        "nt": {"type": "string", "description": "신약(NT) 본문, 없으면 빈 문자열"},
                        "ot": {"type": "string", "description": "구약(OT) 본문, 없으면 빈 문자열"},
                        "psalms": {"type": "string", "description": "시편 장, 없으면 빈 문자열"},
                        "proverbs": {
                            "type": "string",
                            "description": (
                                "잠언 열이 있으면 표시된 장, 표에 잠언 열 자체가 없으면 "
                                "빈 문자열. 빈 값은 후처리에서 해당 날짜 장으로 확정한다."
                            ),
                        },
                    },
                    "required": ["day", "nt", "ot", "psalms", "proverbs"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["days"],
        "additionalProperties": False,
    },
}

QT_PLAN_SCHEMA = {
    "name": "quiet_time_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "integer", "description": "1부터 시작하는 날짜"},
                        "qt": {"type": "string", "description": "QT 성경 본문"},
                    },
                    "required": ["day", "qt"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["days"],
        "additionalProperties": False,
    },
}


def build_br_prompt(year_str: str, month_str: str) -> str:
    return f"""
    Transcribe ONLY the Bible Reading Plan table for {year_str}-{month_str}.
    - Contains columns: Date (날짜), 신약 (NT), 구약 (OT), 시 (Psalms).
    - Some templates also contain 잠 (Proverbs). If the image has a Proverbs column,
      transcribe it exactly. If the image has NO Proverbs column, return an empty
      string for proverbs on EVERY day. The deterministic postprocessor will use
      the calendar day as the Proverbs chapter, so never guess it from the image.
    - Layout: Two side-by-side tables (1-16 on left, 17-31 on right).
    1. Look EXACTLY at the "Date" column number. Match the row content to that date.
    2. If a cell is blank (especially NT/OT on Sundays), use an empty string "".
    3. Preserve Korean Bible abbreviations exactly. In particular: 마=Matthew, 막=Mark,
       눅=Luke, 요=John, 행=Acts, 롬=Romans. Do not infer a different book.
    4. Return every day of the month exactly once. Do not read decorative text or the other image.
    5. In Psalms, stacked small verse numbers are a verse range. Write them with a colon,
       for example chapter 119 with verses 65-88 must be `119:65-88`, never `119-65-88`.
    """


def build_qt_prompt(year_str: str, month_str: str) -> str:
    return f"""
    Transcribe ONLY the Quiet Time calendar table for {year_str}-{month_str}.
    1. Map each visible date number to the passage directly below it in the SAME calendar cell.
    2. Korean '요' means John; never change it to Job ('욥').
    3. A book label may be printed above the chapter/verse inside the cell. Include it in qt.
    4. Return every day of the month exactly once and preserve exact chapter/verse numbers.
    """


def _ai_days_to_sorted_data(ai_result: dict) -> dict:
    """{"days": [{"day": 1, "nt": ..., ...}, ...]} -> {"1": [nt, ot, ps, pr, qt], ...}"""
    sorted_data = {}
    for entry in ai_result.get("days", []):
        day = str(int(entry["day"]))
        sorted_data[day] = [
            entry.get("nt", ""),
            entry.get("ot", ""),
            entry.get("psalms", ""),
            entry.get("proverbs", ""),
            entry.get("qt", ""),
        ]
    return dict(sorted(sorted_data.items(), key=lambda item: int(item[0])))


def _merge_ai_results(br_result: dict, qt_result: dict) -> dict:
    """별도 이미지 요청 결과를 기존 5열 월간 plan 형태로 합친다."""
    br_days = {str(int(entry["day"])): entry for entry in br_result.get("days", [])}
    qt_days = {str(int(entry["day"])): entry for entry in qt_result.get("days", [])}
    merged = {}
    for day in sorted(set(br_days) | set(qt_days), key=int):
        br = br_days.get(day, {})
        qt = qt_days.get(day, {})
        proverbs = str(br.get("proverbs", "")).strip() or day
        merged[day] = [
            br.get("nt", ""),
            br.get("ot", ""),
            br.get("psalms", ""),
            proverbs,
            qt.get("qt", ""),
        ]
    return merged


def _validate_qt_reference(day: str, citation: str) -> None:
    match = re.fullmatch(r"([가-힣]+)\s*(\d+)\s*:\s*(\d+)\s*[-~]\s*(\d+)", citation)
    if not match:
        raise ValueError(f"{day}일 QT 형식 오류: {citation!r}")

    book, chapter, start_verse, end_verse = match.groups()
    if book not in BIBLE_MAP:
        raise ValueError(f"{day}일 QT 성경 권 오류: {book}")

    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT MIN(verse), MAX(verse) FROM bible_ko_KRV WHERE book=? AND chapter=?",
            (book, int(chapter)),
        ).fetchone()
    min_verse, max_verse = row if row else (None, None)
    if (
        min_verse is None
        or int(start_verse) < min_verse
        or int(end_verse) > max_verse
        or int(start_verse) > int(end_verse)
    ):
        raise ValueError(f"{day}일 QT가 성경 DB 범위 밖입니다: {citation}")


def _validate_reading_reference(day: str, label: str, citation: str) -> None:
    match = re.fullmatch(
        r"([가-힣]+)\s*(\d+)(?:\s*[-~]\s*(?:([가-힣]+)\s*)?(\d+))?",
        str(citation),
    )
    if not match:
        raise ValueError(f"{day}일 {label} 형식 오류: {citation!r}")
    for book in (match.group(1), match.group(3)):
        if book and book not in BIBLE_MAP:
            raise ValueError(f"{day}일 {label} 성경 권 오류: {book}")


def validate_monthly_plan(plan: dict, year: int, month: int) -> None:
    """AI 결과가 완전하고 실제 성경 범위 안인지 저장 전에 검사한다."""
    last_day = calendar.monthrange(int(year), int(month))[1]
    expected_days = {str(day) for day in range(1, last_day + 1)}
    if set(plan) != expected_days:
        missing = sorted(expected_days - set(plan), key=int)
        extra = sorted(set(plan) - expected_days, key=int)
        raise ValueError(f"날짜 누락/중복: missing={missing}, extra={extra}")

    for day in sorted(plan, key=int):
        row = plan[day]
        if len(row) != 5:
            raise ValueError(f"{day}일 열 개수가 5개가 아닙니다")
        nt, ot, psalms, proverbs, qt = row
        if bool(nt) != bool(ot):
            raise ValueError(f"{day}일 신약/구약 공란 상태가 다릅니다")
        if nt:
            _validate_reading_reference(day, "신약", nt)
            _validate_reading_reference(day, "구약", ot)
        if not re.fullmatch(r"시\s+\d+(?::\d+[-~]\d+)?", str(psalms)):
            raise ValueError(f"{day}일 시편 값 오류: {psalms!r}")
        if not re.fullmatch(r"잠\s+\d+", str(proverbs)):
            raise ValueError(f"{day}일 잠언 값 오류: {proverbs!r}")
        if ":" in str(psalms):
            _validate_qt_reference(day, str(psalms))
        _validate_qt_reference(day, str(qt))


def postprocess_plan_data(sorted_data: dict) -> dict:
    """권수 생략분 상속 + 정식 명칭 -> 약어 치환 (NT/OT/QT 열 대상)."""
    allowed_books = set(BIBLE_MAP.keys())
    # 열별(NT, OT, QT) 이전 성경 권수 독립적 추적
    last_books = {0: "", 1: "", 4: ""}

    for day, row in sorted_data.items():
        for i in range(len(row)):
            cell = str(row[i]).strip()
            if not cell:
                continue

            cell = re.sub(
                r"(?<![가-힣])(엔)(?=\s*\d)",
                lambda match: OCR_BOOK_FIXES[match.group(1)],
                cell,
            )

            # 1. 풀네임 약어로 치환
            for full, abbr in FULL_TO_ABBR.items():
                if cell.startswith(full):
                    cell = cell.replace(full, abbr, 1).strip()
                    break

            # 2. 열(Column) 특성에 맞춘 후처리 로직 분리
            if i in [0, 1, 4]:  # 신약(NT), 구약(OT), QT
                match = re.match(r"^([가-힣]+)\s*(.*)", cell)
                if match:
                    book, chapters = match.groups()
                    if book in allowed_books:
                        last_books[i] = book
                        row[i] = f"{book} {chapters}".strip()
                elif last_books[i] and re.match(r"^\d", cell):
                    row[i] = f"{last_books[i]} {cell}"

            elif i == 2:  # 시편 (Psalms)
                if re.match(r"^\d", cell):
                    row[i] = f"시 {cell}"

            elif i == 3:  # 잠언 (Proverbs)
                if re.match(r"^\d", cell):
                    row[i] = f"잠 {cell}"

        sorted_data[day] = row

    return sorted_data


def get_next_month():
    """오늘 날짜(KST)를 기준으로 '다음 달'의 연도와 월을 반환"""
    today = datetime.now(ZoneInfo("Asia/Seoul"))
    next_month_date = today.replace(day=28) + timedelta(days=4)
    return next_month_date.year, next_month_date.month


def _extract_plan_from_images(year, month):
    year_str = str(year)
    month_str = str(month).zfill(2)
    assets_dir = os.path.join(BASE_DIR, 'assets')

    def find_local_image(prefix):
        for ext in ['.png', '.jpg', '.jpeg']:
            path = os.path.join(assets_dir, f"{year_str}년_{month_str}월_{prefix}_passage{ext}")
            if os.path.exists(path):
                return path
        return None

    br_path = find_local_image("BR")
    qt_path = find_local_image("QT")

    logger.info(f"\n🔍 [실행] {year_str}년 {month_str}월 데이터 생성 중...")

    try:
        provider = get_provider()
    except AIProviderError as e:
        logger.error(f"❌ 오류: {e}")
        return None

    try:
        images = {}
        image_info = []

        if br_path or qt_path:
            if br_path:
                images["BR"] = PIL.Image.open(br_path)
                image_info.append("BR")
            if qt_path:
                images["QT"] = PIL.Image.open(qt_path)
                image_info.append("QT")
            logger.info(f"  소스: 로컬 assets ({', '.join(image_info)})")
        else:
            logger.info("  로컬 assets 없음 → Google Drive에서 검색합니다...")
            from tools.gdrive_parser import fetch_images_from_drive
            drive_images, image_info = fetch_images_from_drive(year, month)
            if not drive_images:
                logger.warning(
                    f"⚠️ {year_str}년 {month_str}월의 이미지를 assets 폴더와 Google Drive 모두에서 찾지 못했습니다."
                )
                return None
            images.update(drive_images)
            logger.info(f"  소스: Google Drive ({', '.join(image_info)})")

        br_result = {"days": []}
        qt_result = {"days": []}
        if "BR" in images:
            br_result = provider.generate_from_images(
                [images["BR"]],
                build_br_prompt(year_str, month_str),
                BR_PLAN_SCHEMA,
            )
        if "QT" in images:
            qt_result = provider.generate_from_images(
                [images["QT"]],
                build_qt_prompt(year_str, month_str),
                QT_PLAN_SCHEMA,
            )

        logger.info("[INFO] Parsing structured output...")
        sorted_data = _merge_ai_results(br_result, qt_result)
        sorted_data = postprocess_plan_data(sorted_data)

        logger.info(f"[SUCCESS] {year_str}-{month_str} data generated.")
        return sorted_data

    except AIProviderError as e:
        logger.error(f"❌ AI 분석 중 오류 발생: {e}")
        logger.debug(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"❌ 생성 중 예기치 못한 오류 발생: {e}")
        logger.error(traceback.format_exc())
        return None


def generate_monthly_plan(year, month, use_hwpx=None, output_dir=None):
    year_str = str(year)
    month_str = str(month).zfill(2)
    assets_dir = os.path.join(BASE_DIR, 'assets')

    logger.info(f"\n🔍 [실행] {year_str}년 {month_str}월 데이터 생성 중...")

    if use_hwpx is None:
        use_hwpx = is_hwpx_parsing_enabled()

    if use_hwpx:
        hwpx_sources = find_hwpx_sources(assets_dir, year, month)
    else:
        hwpx_sources = {}
        logger.info("  HWPX parsing: OFF (이미지/AI만 사용)")
    br_path = hwpx_sources.get("BR")
    qt_path = hwpx_sources.get("QT")

    br_plan = {}
    qt_plan = {}
    fallback_plan = None

    if br_path:
        try:
            br_plan = parse_br_hwpx(br_path)
            logger.info(f"  소스: BR HWPX ({os.path.basename(br_path)})")
        except Exception as e:
            logger.warning(f"⚠️ BR HWPX 파싱 실패: {e}")

    if qt_path:
        try:
            qt_plan = parse_qt_hwpx(qt_path)
            logger.info(f"  소스: QT HWPX ({os.path.basename(qt_path)})")
        except Exception as e:
            logger.warning(f"⚠️ QT HWPX 파싱 실패: {e}")

    if not br_path or not qt_path or not br_plan or not qt_plan:
        logger.info("  HWPX가 부족하여 기존 이미지/AI 방식으로 보강합니다...")
        fallback_plan = _extract_plan_from_images(year, month)
        if fallback_plan is None:
            logger.error("❌ HWPX 보강에 실패했습니다. 이미지/AI fallback도 실패했습니다.")
            return

    final_plan = merge_monthly_plan(br_plan, qt_plan, fallback_plan)
    if not final_plan:
        logger.error("❌ 병합할 데이터를 만들지 못했습니다.")
        return

    try:
        validate_monthly_plan(final_plan, int(year), int(month))
    except ValueError as e:
        logger.error(f"❌ 생성 결과 검증 실패 — 기존 plan을 보존합니다: {e}")
        return

    plans_dir = os.fspath(output_dir or os.path.join(BASE_DIR, 'data', 'plans'))
    if not os.path.exists(plans_dir):
        os.makedirs(plans_dir)

    output_file = os.path.join(plans_dir, f"{year_str}_{month_str}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_plan, f, ensure_ascii=False, indent=4)

    if not use_hwpx:
        source_label = "Image/AI (HWPX OFF)"
    elif fallback_plan:
        source_label = "HWPX + AI fallback"
    else:
        source_label = "HWPX"
    logger.info(f"✅ 생성 성공! 저장 위치: {output_file} ({source_label})")
    return final_plan


if __name__ == "__main__":
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if len(sys.argv) >= 3:
        input_year = sys.argv[1]
        input_month = sys.argv[2]
        generate_monthly_plan(input_year, input_month)
    elif len(sys.argv) == 2:
        input_year = now.year
        input_month = sys.argv[1]
        generate_monthly_plan(input_year, input_month)
    else:
        if sys.stdin.isatty():
            try:
                print("=== 📅 월간 성경읽기 생성기 (수동 모드) ===")
                y = input(f"연도 (기본 {now.year}): ").strip() or now.year
                m = input(f"월 (기본 {now.month}): ").strip() or now.month
                generate_monthly_plan(y, m)
            except Exception:
                pass
        else:
            next_year, next_month = get_next_month()
            generate_monthly_plan(next_year, next_month)
