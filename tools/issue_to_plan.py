import os
import sys
import re
import json
import urllib.request
import tempfile
import PIL.Image
from datetime import datetime, timedelta
from google import genai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from core.bible_scripture_resolver import BIBLE_MAP

def extract_year_month(title):
    """제목에서 연도와 월을 추출 (예: '2026년 4월 플랜', '2026-04')"""
    matches = re.findall(r'(\d{4})[^\d]*(\d{1,2})', title)
    if matches:
        return int(matches[0][0]), int(matches[0][1])
    # 찾지 못하면 다음 달로 기본 설정
    today = datetime.now()
    next_month_date = today.replace(day=28) + timedelta(days=4)
    return next_month_date.year, next_month_date.month

def extract_image_urls(body):
    """GitHub 마크다운 이슈 본문에서 이미지 URL 추출"""
    if not body: return []
    # 마크다운 이미지 정규식: ![alt](url) 또는 <img src="url">
    urls = re.findall(r'!\[.*?\]\((https://github\.com/user-attachments/assets/[a-zA-Z0-9-]+)\)', body)
    if not urls:
        urls = re.findall(r'src="(https://github\.com/user-attachments/assets/[a-zA-Z0-9-]+)"', body)
    return urls

def main():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY가 없습니다.")
        sys.exit(1)

    issue_title = os.getenv('ISSUE_TITLE', '')
    issue_body = os.getenv('ISSUE_BODY', '')

    year, month = extract_year_month(issue_title)
    month_str = str(month).zfill(2)
    print(f"📅 파싱 타겟: {year}년 {month_str}월")

    img_urls = extract_image_urls(issue_body)
    if not img_urls:
        print("❌ 본문에서 이미지 링크(user-attachments)를 찾을 수 없습니다.")
        sys.exit(1)

    print(f"🔗 {len(img_urls)}개의 이미지를 찾았습니다.")

    client = genai.Client(api_key=api_key)
    contents = []

    # 프롬프트 구성
    prompt = f"""
    You are a Bible data extraction expert. I am providing images for the {year}-{month_str} plan.
    
    IMAGE DETAILS:
    - Contains columns: Date (날짜), 신약 (NT), 구약 (OT), 시 (Psalms), 잠 (Proverbs).
    - Contains "QT" passage for each day.
    
    CRITICAL INSTRUCTION FOR DATES (DO NOT SHIFT):
    The very first column in the table is the "Date" (1, 2, 3...). 
    You MUST map the exact printed Date to the JSON key.
    - If the Date is "1" (Sunday) and the '신약' and '구약' columns are BLANK in the image, you MUST return an empty string "" for NT and OT for key "1".
    - If Date "2" says "막 1-2" and "창 1-3", you MUST map these to the key "2".
    - If Date "5" says "막 7-8" and "창 10-12", it goes to key "5".
    DO NOT shift the rows. Row for Date N must be key "N" in JSON.
    
    EXTRACT BOOK NAMES EXACTLY:
    If a cell contains a book name (e.g., "창 1-3", "막 1-2"), you MUST include the book name ("창", "막"). Pay close attention to changes in book names (e.g., '막', '눅', '출', etc.) and extract exactly what is written.
    
    QT: Extract the "QT" passage for each day.
    
    Return ONLY raw JSON in this format:
    {{
      "1": ["", "", "1", "1", "시 23:1-6"],
      "2": ["막 1-2", "창 1-3", "2", "2", "사 53:1-12"],
      "3": ["막 3-4", "창 4-6", "3", "3", "시 1:1-6"],
      "4": ["막 5-6", "창 7-9", "4", "4", "요 10:1-30"],
      "5": ["막 7-8", "창 10-12", "5", "5", "엡 5:1-21"]
    }}
    """
    contents.append(prompt)

    # 이미지 임시 다운로드 및 로드
    temp_dir = tempfile.mkdtemp()
    for i, url in enumerate(img_urls):
        img_path = os.path.join(temp_dir, f"img_{i}.jpg")
        print(f"📥 이미지 다운로드 중... ({i+1}/{len(img_urls)})")
        urllib.request.urlretrieve(url, img_path)
        contents.append(PIL.Image.open(img_path))

    print("🤖 Gemini에 파싱을 요청합니다...")
    response = client.models.generate_content(model='gemini-2.0-flash', contents=contents)
    
    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
    bible_data = json.loads(cleaned_text)
    sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

    # 권수 상속 및 정제 로직 (기존과 동일)
    ALLOWED_BOOKS = set(BIBLE_MAP.keys())
    full_to_abbr = { "마태복음": "마", "마가복음": "막", "누가복음": "눅", "요한복음": "요", "창세기": "창", "출애굽기": "출" }
    last_books = ["", "", "", "", ""]

    for day, row in sorted_data.items():
        for i in range(len(row)):
            cell = row[i].strip()
            if not cell: continue
            for full, abbr in full_to_abbr.items():
                if cell.startswith(full):
                    cell = cell.replace(full, abbr, 1)
                    row[i] = cell
                    break
            if i < 4:
                match = re.match(r"^([가-힣\d]+)", cell)
                if match:
                    potential_book = match.group(1)
                    if potential_book in ALLOWED_BOOKS:
                        last_books[i] = potential_book
                    elif re.match(r"^\d", cell) and last_books[i]:
                        row[i] = f"{last_books[i]} {cell}"
                elif last_books[i]:
                    row[i] = f"{last_books[i]} {cell}"
            if i == 4 and re.match(r"^\d", cell):
                row[i] = f"마{cell}"

    plans_dir = os.path.join(BASE_DIR, 'data', 'plans')
    os.makedirs(plans_dir, exist_ok=True)
    output_file = os.path.join(plans_dir, f"{month_str}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 생성 성공! 저장 위치: {output_file}")

if __name__ == "__main__":
    main()