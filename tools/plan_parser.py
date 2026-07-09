import logging
import os
import sys
import json
import re
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

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bible_bot.plan_parser")

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

# OpenAI Structured Outputs(strict json_schema)는 임의 개수의 동적 키(1~31일)를
# 가진 object를 지원하지 않으므로, "일자별 항목의 배열"로 스키마를 고정한다.
# 응답을 받은 뒤 기존 {"1": [...], "2": [...]} 형태로 변환해 하위 로직을 그대로 재사용한다.
BIBLE_PLAN_SCHEMA = {
    "name": "bible_monthly_plan",
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
                        "proverbs": {"type": "string", "description": "잠언 장, 없으면 빈 문자열"},
                        "qt": {"type": "string", "description": "QT 본문, 없으면 빈 문자열"},
                    },
                    "required": ["day", "nt", "ot", "psalms", "proverbs", "qt"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["days"],
        "additionalProperties": False,
    },
}


def build_prompt(year_str: str, month_str: str) -> str:
    return f"""
    You are a Bible data extraction expert. I am providing images for the {year_str}-{month_str} plan.

    IMAGE 1 (Bible Reading Plan) DETAILS:
    - Contains columns: Date (날짜), 신약 (NT), 구약 (OT), 시 (Psalms), 잠 (Proverbs).
    - Layout: Two side-by-side tables (1-16 on left, 17-31 on right).

    CRITICAL INSTRUCTION FOR IMAGE 1:
    1. Look EXACTLY at the "Date" column number. Match the row content to that date.
    2. If a cell is blank (especially NT/OT on Sundays), use an empty string "".
    3. Capture the Bible book names (e.g., '눅', '막', '창', '출') carefully. They often only appear on the first day of the week or when the book changes.
    4. For Psalms (시) and Proverbs (잠) columns, just extract the numbers if that's all that is there.

    IMAGE 2 (QT Calendar) DETAILS:
    - This is a monthly calendar grid. Each box contains a Date number and a QT passage.
    - IMPORTANT: On Sundays (SUN), the passage usually starts with a book name like '시편' or '잠언'.
    - IMPORTANT: On Weekdays (MON-SAT), if only numbers like "1: 18-25" are shown, YOU MUST INFER the book name from the previous consecutive day. Output the full book abbreviation + chapter/verse.

    Return one entry per calendar day, for ALL DAYS from 1 to the last day of the month, in the "days" array.
    Each entry must have: day (integer), nt, ot, psalms, proverbs, qt (strings, "" when blank).
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
        images = []
        image_info = []

        if br_path or qt_path:
            if br_path:
                images.append(PIL.Image.open(br_path))
                image_info.append("BR")
            if qt_path:
                images.append(PIL.Image.open(qt_path))
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
            for prefix in ["BR", "QT"]:
                if prefix in drive_images:
                    images.append(drive_images[prefix])
            logger.info(f"  소스: Google Drive ({', '.join(image_info)})")

        prompt = build_prompt(year_str, month_str)
        ai_result = provider.generate_from_images(images, prompt, BIBLE_PLAN_SCHEMA)

        logger.info("[INFO] Parsing structured output...")
        sorted_data = _ai_days_to_sorted_data(ai_result)
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


def generate_monthly_plan(year, month):
    year_str = str(year)
    month_str = str(month).zfill(2)
    assets_dir = os.path.join(BASE_DIR, 'assets')

    logger.info(f"\n🔍 [실행] {year_str}년 {month_str}월 데이터 생성 중...")

    hwpx_sources = find_hwpx_sources(assets_dir, year, month)
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

    plans_dir = os.path.join(BASE_DIR, 'data', 'plans')
    if not os.path.exists(plans_dir):
        os.makedirs(plans_dir)

    output_file = os.path.join(plans_dir, f"{year_str}_{month_str}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_plan, f, ensure_ascii=False, indent=4)

    source_label = "HWPX"
    if fallback_plan:
        source_label = "HWPX + AI fallback"
    logger.info(f"✅ 생성 성공! 저장 위치: data/plans/{year_str}_{month_str}.json ({source_label})")


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
