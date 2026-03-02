import os
import json
import sys
import PIL.Image
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# ==========================================
# ⚙️ 경로 및 환경 설정
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# [보안 패치] 중앙 .env 로드 로직
def load_central_env():
    current = Path(os.getcwd())
    while current != current.parent:
        target = current / '.secrets' / '.env'
        if target.exists():
            load_dotenv(target)
            print(f"🔐 Loaded central .env from {target}")
            return
        current = current.parent
    load_dotenv(os.path.join(BASE_DIR, '.env')) # Fallback

load_central_env()
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

        prompt = f"""
        You are a data assistant. Parse the provided image(s) for {year_str}-{month_str}.
        Images provided: {', '.join(image_info)}
        
        Rules:
        1. Key: Day string (e.g., "1", "2").
        2. Value: A list ["NT", "Psalms", "Proverbs", "QT"].
           - "NT", "Psalms", "Proverbs" are from the BR image.
           - "QT" is from the QT image.
        3. If an image is missing, leave the corresponding values empty ("").
        4. Output Example: {{"1": ["마1", "시1", "잠1", "삼상1"]}}
        
        Return ONLY raw JSON. No code blocks.
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
        # 로컬 테스트용 input()은 주석 처리하거나, 조건문으로 분기 가능하지만
        # 자동화를 위해 기본 동작을 '다음 달 계산'으로 설정합니다.
        
        # 만약 로컬에서 수동 입력을 계속 쓰고 싶다면:
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