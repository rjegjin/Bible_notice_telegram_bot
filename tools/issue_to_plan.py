import os
import sys
import re
import json
import logging
import tempfile
import traceback
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import PIL.Image

# 프로젝트 루트 경로 추가 (core/ai/tools 모듈 임포트용)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from ai.interfaces import AIProviderError
from ai.provider import get_provider
from tools.plan_parser import (
    BIBLE_PLAN_SCHEMA,
    _ai_days_to_sorted_data,
    build_prompt,
    postprocess_plan_data,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bible_bot.issue_to_plan")


def extract_year_month(title):
    """제목에서 연도와 월을 추출 (예: '2026년 4월 플랜', '2026-04')"""
    matches = re.findall(r'(\d{4})[^\d]*(\d{1,2})', title)
    if matches:
        return int(matches[0][0]), int(matches[0][1])

    # 제목에 연도가 없으면 숫자(월)만이라도 찾고 연도는 현재 연도 사용
    month_match = re.search(r'(\d{1,2})\s*월', title)
    if month_match:
        return datetime.now(ZoneInfo("Asia/Seoul")).year, int(month_match.group(1))

    # 찾지 못하면 다음 달로 기본 설정
    today = datetime.now(ZoneInfo("Asia/Seoul"))
    next_month_date = today.replace(day=28) + timedelta(days=4)
    return next_month_date.year, next_month_date.month


def extract_image_urls(body):
    """GitHub 마크다운 이슈 본문에서 이미지 URL 추출"""
    if not body:
        return []
    # 마크다운 이미지 정규식: ![alt](url) 또는 <img src="url">
    urls = re.findall(r'!\[.*?\]\((https://github\.com/user-attachments/assets/[a-zA-Z0-9-]+)\)', body)
    if not urls:
        urls = re.findall(r'src="(https://github\.com/user-attachments/assets/[a-zA-Z0-9-]+)"', body)
    return urls


def main():
    try:
        provider = get_provider()
    except AIProviderError as e:
        logger.error(f"❌ 오류: {e}")
        sys.exit(1)

    issue_title = os.getenv('ISSUE_TITLE', '')
    issue_body = os.getenv('ISSUE_BODY', '')

    year, month = extract_year_month(issue_title)
    month_str = str(month).zfill(2)
    year_str = str(year)
    logger.info(f"📅 파싱 타겟: {year_str}년 {month_str}월")

    img_urls = extract_image_urls(issue_body)
    if not img_urls:
        logger.error("❌ 본문에서 이미지 링크(user-attachments)를 찾을 수 없습니다.")
        sys.exit(1)

    logger.info(f"🔗 {len(img_urls)}개의 이미지를 찾았습니다.")

    logger.info("[INFO] Loading image...")
    images = []
    temp_dir = tempfile.mkdtemp()
    for i, url in enumerate(img_urls):
        img_path = os.path.join(temp_dir, f"img_{i}.jpg")
        logger.info(f"📥 이미지 다운로드 중... ({i + 1}/{len(img_urls)})")
        try:
            urllib.request.urlretrieve(url, img_path)
            images.append(PIL.Image.open(img_path))
        except Exception as e:
            logger.warning(f"⚠️ 이미지 다운로드 실패 ({url}): {e}")

    if not images:
        logger.error("❌ 다운로드에 성공한 이미지가 없습니다.")
        sys.exit(1)

    prompt = build_prompt(year_str, month_str)

    try:
        logger.info("[INFO] Sending request to OpenAI...")
        ai_result = provider.generate_from_images(images, prompt, BIBLE_PLAN_SCHEMA)

        logger.info("[INFO] Parsing structured output...")
        sorted_data = _ai_days_to_sorted_data(ai_result)
        sorted_data = postprocess_plan_data(sorted_data)
    except AIProviderError as e:
        logger.error(f"❌ AI 분석 중 오류 발생: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 생성 중 예기치 못한 오류 발생: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    plans_dir = os.path.join(BASE_DIR, 'data', 'plans')
    os.makedirs(plans_dir, exist_ok=True)
    output_file = os.path.join(plans_dir, f"{year_str}_{month_str}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)

    logger.info(f"[SUCCESS] {year_str}-{month_str} data generated.")
    logger.info(f"✅ 생성 성공! 저장 위치: {output_file}")


if __name__ == "__main__":
    main()
