import os
import sys
import re
import json
import urllib.request
import tempfile
import PIL.Image
from datetime import datetime, timedelta
from google import genai

# 프로젝트 루트 경로 추가 (core 모듈 임포트용)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from core.bible_scripture_resolver import BIBLE_MAP

def extract_year_month(title):
    """제목에서 연도와 월을 추출 (예: '2026년 4월 플랜', '2026-04')"""
    matches = re.findall(r'(\d{4})[^\d]*(\d{1,2})', title)
    if matches:
        return int(matches[0][0]), int(matches[0][1])
    
    # 제목에 연도가 없으면 숫자(월)만이라도 찾고 연도는 현재 연도 사용
    month_match = re.search(r'(\d{1,2})\s*월', title)
    if month_match:
        return datetime.now().year, int(month_match.group(1))
        
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
    year_str = str(year)
    print(f"📅 파싱 타겟: {year_str}년 {month_str}월")

    img_urls = extract_image_urls(issue_body)
    if not img_urls:
        print("❌ 본문에서 이미지 링크(user-attachments)를 찾을 수 없습니다.")
        sys.exit(1)

    print(f"🔗 {len(img_urls)}개의 이미지를 찾았습니다.")

    client = genai.Client(api_key=api_key)
    contents = []

    # 고도화된 범용 프롬프트 (gemini_parser.py와 동기화)
    prompt = f"""
    You are a Bible data extraction expert. I am providing images for the {year_str}-{month_str} plan.
    
    IMAGE 1 (Bible Reading Plan) DETAILS:
    - Contains columns: Date (날짜), 신약 (NT), 구약 (OT), 시 (Psalms), 잠 (Proverbs).
    - Layout: Two side-by-side tables (1-16 on left, 17-31 on right).
    
    CRITICAL INSTRUCTION FOR IMAGE 1:
    1. Look EXACTLY at the "Date" column number. Match the row content to that date. 
    2. If a cell is blank (especially NT/OT on Sundays), use `""`.
    3. Capture the Bible book names (e.g., '눅', '막', '창', '출') carefully. They often only appear on the first day of the week or when the book changes.
    4. For Psalms (시) and Proverbs (잠) columns, just extract the numbers if that's all that is there.
    
    IMAGE 2 (QT Calendar) DETAILS:
    - This is a monthly calendar grid. Each box contains a Date number and a QT passage.
    - IMPORTANT: On Sundays (SUN), the passage usually starts with a book name like '시편' or '잠언'.
    - IMPORTANT: On Weekdays (MON-SAT), if only numbers like "1: 18-25" are shown, YOU MUST INFER the book name from the previous consecutive day. Output the full book abbreviation + chapter/verse.
    
    Return ONLY raw JSON in this EXACT format for ALL DAYS from 1 to the end of the month:
    {{
      "1": ["NT", "OT", "Ps_Chap", "Pr_Chap", "QT_Passage"],
      ...
    }}
    """
    contents.append(prompt)

    # 이미지 임시 다운로드 및 로드
    temp_dir = tempfile.mkdtemp()
    for i, url in enumerate(img_urls):
        img_path = os.path.join(temp_dir, f"img_{i}.jpg")
        print(f"📥 이미지 다운로드 중... ({i+1}/{len(img_urls)})")
        try:
            urllib.request.urlretrieve(url, img_path)
            contents.append(PIL.Image.open(img_path))
        except Exception as e:
            print(f"⚠️ 이미지 다운로드 실패 ({url}): {e}")

    print("🤖 Gemini에 파싱을 요청합니다...")
    response = client.models.generate_content(model='gemini-2.0-flash', contents=contents)
    
    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
    bible_data = json.loads(cleaned_text)
    sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

    # 고도화된 후처리 로직 (gemini_parser.py와 동기화)
    ALLOWED_BOOKS = set(BIBLE_MAP.keys())
    full_to_abbr = {
        "마태복음": "마", "마가복음": "막", "누가복음": "눅", "요한복음": "요", "사도행전": "행",
        "로마서": "롬", "고린도전서": "고전", "고린도후서": "고후", "갈라디아서": "갈", "에베소서": "엡",
        "빌립보서": "빌", "골로새서": "골", "데살로니가전서": "살전", "데살로니가후서": "살후",
        "디모데전서": "딤전", "디모데후서": "딤후", "디도서": "딛", "빌레몬서": "몬", "히브리서": "히",
        "야고보서": "약", "베드로전서": "벧전", "베드로후서": "벧후", "요한일서": "요일", "요한일": "요일",
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

    last_books = {0: "", 1: "", 4: ""} 

    for day, row in sorted_data.items():
        for i in range(len(row)):
            cell = str(row[i]).strip()
            if not cell: continue
            
            for full, abbr in full_to_abbr.items():
                if cell.startswith(full):
                    cell = cell.replace(full, abbr, 1).strip()
                    break
            
            if i in [0, 1, 4]:
                match = re.match(r"^([가-힣]+)\s*(.*)", cell)
                if match:
                    book, chapters = match.groups()
                    if book in ALLOWED_BOOKS:
                        last_books[i] = book
                        row[i] = f"{book} {chapters}".strip()
                elif last_books[i] and re.match(r"^\d", cell):
                    row[i] = f"{last_books[i]} {cell}"
            elif i == 2:
                if re.match(r"^\d", cell): row[i] = f"시 {cell}"
            elif i == 3:
                if re.match(r"^\d", cell): row[i] = f"잠 {cell}"
        
        sorted_data[day] = row

    plans_dir = os.path.join(BASE_DIR, 'data', 'plans')
    os.makedirs(plans_dir, exist_ok=True)
    output_file = os.path.join(plans_dir, f"{month_str}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 생성 성공! 저장 위치: {output_file}")

if __name__ == "__main__":
    main()
