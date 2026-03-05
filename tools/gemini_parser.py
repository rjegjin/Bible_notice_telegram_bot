import os
import json
import sys
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
    # 현재 날짜 (KST 기준 보정 없이 UTC로 해도 무방, 월 단위 계산이므로)
    today = datetime.now()
    # 28일 + 4일 = 다음 달 1일 or 2일 (안전하게 다음 달로 넘어감)
    next_month_date = today.replace(day=28) + timedelta(days=4)
    return next_month_date.year, next_month_date.month

def generate_monthly_plan(year, month):
    if not GOOGLE_API_KEY:
        print("❌ 오류: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
        return

    year_str = str(year)
    month_str = str(month).zfill(2)
    assets_dir = os.path.join(BASE_DIR, 'assets')
    
    # [업그레이드] 확장자 유연성 확보 (.png, .jpg, .jpeg)
    def find_image(prefix):
        for ext in ['.png', '.jpg', '.jpeg']:
            path = os.path.join(assets_dir, f"{year_str}년_{month_str}월_{prefix}_passage{ext}")
            if os.path.exists(path):
                return path
        return None

    br_path = find_image("BR")
    qt_path = find_image("QT")

    if not br_path and not qt_path:
        print(f"⚠️ {year_str}년 {month_str}월의 이미지 파일(BR 또는 QT)이 'assets' 폴더에 없습니다.")
        return

    print(f"\n🔍 [자동 실행] {year_str}년 {month_str}월 데이터 생성 중...")
    
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    try:
        contents = []
        image_info = []
        
        if br_path:
            contents.append(PIL.Image.open(br_path))
            image_info.append("Bible Reading Plan (BR)")
        if qt_path:
            contents.append(PIL.Image.open(qt_path))
            image_info.append("QT Passage (QT)")

        valid_abbrs = ", ".join(list(BIBLE_MAP.keys()))

        prompt = f"""
        You are a Bible data extraction expert. I am providing TWO images for the {year_str}-{month_str} plan.
        
        IMAGE 1 (Bible Reading Plan) DETAILS:
        - Contains columns: Date (날짜), 신약 (NT), 구약 (OT), 시 (Psalms), 잠 (Proverbs).
        - Layout: Two side-by-side tables (1-16 on left, 17-31 on right).
        
        CRITICAL INSTRUCTION FOR DATES (ABSOLUTELY DO NOT SHIFT):
        Look EXACTLY at the "Date" column number.
        - Look at the row for Date "1" (March 1st). The '신약' and '구약' cells are BLANK. Therefore, your JSON MUST have `""` (empty string) for NT and OT in key "1".
        - Look at the row for Date "2" (March 2nd). The '신약' cell says "막 1-2" and '구약' cell says "창 1-3". Your JSON MUST have `"막 1-2"` and `"창 1-3"` in key "2".
        - Look at the row for Date "5" (March 5th). The '신약' cell says "막 7-8" and '구약' cell says "창 10-12". Your JSON MUST have these in key "5".
        If you put "막 1-2" into key "1", you have failed. The row numbers must match the printed Date perfectly.
        
        EXTRACT BOOK NAMES EXACTLY:
        If a cell contains a book name (e.g., "창 1-3", "막 1-2"), you MUST include the book name ("창", "막"). Pay close attention to changes in book names (e.g., '막', '눅', '출', etc.) and extract exactly what is written.
        
        IMAGE 2 (QT):
        Extract the "QT" passage for each day from the calendar image.
        
        Return ONLY raw JSON in this EXACT format for ALL DAYS from 1 to {month_str} (Notice key 1 has empty NT/OT in this example, and YOU MUST continue up to the last day of the month):
        {{
          "1": ["", "", "1", "1", "시 23:1-6"],
          "2": ["막 1-2", "창 1-3", "2", "2", "사 53:1-12"],
          "3": ["막 3-4", "창 4-6", "3", "3", "시 1:1-6"],
          "4": ["막 5-6", "창 7-9", "4", "4", "요 10:1-30"],
          "5": ["막 7-8", "창 10-12", "5", "5", "엡 5:1-21"],
          ... (CONTINUE FOR ALL DAYS UNTIL THE END OF THE MONTH) ...
        }}
        """
        contents.insert(0, prompt)

        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=contents
        )
        
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        bible_data = json.loads(cleaned_text)
        
        # 날짜순 정렬
        sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

        # 후처리: 권수가 생략되고 장수만 있는 경우 이전 날짜의 권수를 상속 (NT, OT, Psalms, Proverbs)
        import re
        last_books = ["", "", "", "", ""]
        
        # 성경 권수 약어 허용 리스트 (Resolver의 BIBLE_MAP 기반)
        ALLOWED_BOOKS = set(BIBLE_MAP.keys())

        # 풀네임 -> 약어 변환 매핑 (예외 처리용)
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

        for day, row in sorted_data.items():
            for i in range(len(row)):
                cell = row[i].strip()
                if not cell: continue
                
                # 1. 풀네임 약어로 치환 (특히 QT에서 유용)
                for full, abbr in full_to_abbr.items():
                    if cell.startswith(full):
                        cell = cell.replace(full, abbr, 1)
                        row[i] = cell
                        break
                
                # 2. 권수 상속 로직 (QT 제외, 0~3번 인덱스만)
                if i < 4:
                    # 권수 추출 (문자로 시작하는 부분)
                    match = re.match(r"^([가-힣\d]+)", cell)
                    if match:
                        potential_book = match.group(1)
                        # 숫자가 포함된 권수(고전, 벧전 등) 처리 및 허용 리스트 확인
                        if potential_book in ALLOWED_BOOKS:
                            last_books[i] = potential_book
                        elif re.match(r"^\d", cell):
                            # 숫자로 시작하는 경우(장수만 있는 경우) 상속
                            if last_books[i]:
                                row[i] = f"{last_books[i]} {cell}"
                    elif last_books[i]:
                        # 아예 숫자로만 되어 있는 경우 등
                        row[i] = f"{last_books[i]} {cell}"
                
                # 3. QT(인덱스 4)에 장절만 있는 경우 기본값(마태복음) 추가
                if i == 4:
                    if re.match(r"^\d", cell):
                        row[i] = f"마{cell}"
            
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
    # 인자가 있으면 그 날짜로, 없으면 '다음 달'로 자동 실행
    if len(sys.argv) >= 3:
        input_year = sys.argv[1]
        input_month = sys.argv[2]
        generate_monthly_plan(input_year, input_month)
    else:
        # 사용자 입력 대신 자동 계산 로직
        if sys.stdin.isatty(): # 사람이 터미널에서 실행했을 때
            try:
                print("=== 📅 월간 성경읽기 생성기 (수동 모드) ===")
                y = input("연도: ").strip()
                m = input("월: ").strip()
                generate_monthly_plan(y, m)
            except: pass
        else: # GitHub Actions 등 자동화 환경일 때
            next_year, next_month = get_next_month()
            generate_monthly_plan(next_year, next_month)
