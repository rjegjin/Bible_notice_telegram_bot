import os
import json
import sys
import re
import PIL.Image
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# 프로젝트 루트 경로 추가 (core 모듈 임포트용)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from core.bible_scripture_resolver import BIBLE_MAP

# ==========================================
# ⚙️ 경로 및 환경 설정
# ==========================================

# [보안 & 편의] 중앙 .env 로드 로직 (root/.secrets/.env 우선)
def load_env_centralized():
    central_secrets = Path("/home/rjegj/projects/.secrets/.env")
    if central_secrets.exists():
        load_dotenv(central_secrets)
        return True
    local_env = os.path.join(BASE_DIR, '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)
        return True
    return False

load_env_centralized()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

def get_next_month():
    """오늘 날짜를 기준으로 '다음 달'의 연도와 월을 반환"""
    today = datetime.now()
    next_month_date = today.replace(day=28) + timedelta(days=4)
    return next_month_date.year, next_month_date.month

def generate_monthly_plan(year, month):
    if not GOOGLE_API_KEY:
        print("❌ 오류: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
        return

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

    print(f"\n🔍 [실행] {year_str}년 {month_str}월 데이터 생성 중...")

    client = genai.Client(api_key=GOOGLE_API_KEY)

    try:
        contents = []
        image_info = []

        if br_path or qt_path:
            if br_path:
                contents.append(PIL.Image.open(br_path))
                image_info.append("BR")
            if qt_path:
                contents.append(PIL.Image.open(qt_path))
                image_info.append("QT")
            print(f"  소스: 로컬 assets ({', '.join(image_info)})")
        else:
            print(f"  로컬 assets 없음 → Google Drive에서 검색합니다...")
            from tools.gdrive_parser import fetch_images_from_drive
            drive_images, image_info = fetch_images_from_drive(year, month)
            if not drive_images:
                print(f"⚠️ {year_str}년 {month_str}월의 이미지를 assets 폴더와 Google Drive 모두에서 찾지 못했습니다.")
                return
            for prefix in ["BR", "QT"]:
                if prefix in drive_images:
                    contents.append(drive_images[prefix])
            print(f"  소스: Google Drive ({', '.join(image_info)})")

        prompt = f"""
        You are a Bible data extraction expert. I am providing TWO images for the {year_str}-{month_str} plan.
        
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
          "2": ["...", "...", "...", "...", "..."],
          ...
        }}
        """
        contents.insert(0, prompt)

        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=contents
        )
        
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        bible_data = json.loads(cleaned_text)
        
        sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

        ALLOWED_BOOKS = set(BIBLE_MAP.keys())

        full_to_abbr = {
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

        # 열별(NT, OT, QT) 이전 성경 권수 독립적 추적
        last_books = {0: "", 1: "", 4: ""} 

        for day, row in sorted_data.items():
            for i in range(len(row)):
                cell = str(row[i]).strip()
                if not cell: continue
                
                # 1. 풀네임 약어로 치환
                for full, abbr in full_to_abbr.items():
                    if cell.startswith(full):
                        cell = cell.replace(full, abbr, 1).strip()
                        break
                
                # 2. 열(Column) 특성에 맞춘 후처리 로직 분리
                if i in [0, 1, 4]:  # 신약(NT), 구약(OT), QT
                    # 권수 추출 (예: "눅 15-16", "고전 3")
                    match = re.match(r"^([가-힣]+)\s*(.*)", cell)
                    if match:
                        book, chapters = match.groups()
                        if book in ALLOWED_BOOKS:
                            last_books[i] = book  # 새로운 성경 권수 업데이트
                            row[i] = f"{book} {chapters}".strip()
                    elif last_books[i] and re.match(r"^\d", cell):
                        # 숫자로 시작하는 경우(장수만 있는 경우) 이전 권수 상속
                        row[i] = f"{last_books[i]} {cell}"
                        
                elif i == 2:  # 시편 (Psalms)
                    if re.match(r"^\d", cell):
                        row[i] = f"시 {cell}"
                        
                elif i == 3:  # 잠언 (Proverbs)
                    if re.match(r"^\d", cell):
                        row[i] = f"잠 {cell}"
            
            sorted_data[day] = row

        plans_dir = os.path.join(BASE_DIR, 'data', 'plans')
        if not os.path.exists(plans_dir): os.makedirs(plans_dir)

        output_file = os.path.join(plans_dir, f"{month_str}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 생성 성공! 저장 위치: data/plans/{month_str}.json (이미지 {len(image_info)}개 반영)")
        
    except Exception as e:
        print(f"❌ 생성 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    now = datetime.now()
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
            except: pass
        else:
            next_year, next_month = get_next_month()
            generate_monthly_plan(next_year, next_month)
