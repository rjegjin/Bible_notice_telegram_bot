import os
import json
import PIL.Image
from dotenv import load_dotenv
from google import genai

# .env 파일 활성화
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

def generate_monthly_plan(year, month):
    """
    연도와 월을 입력받아 지정된 패턴의 이미지 파일을 찾고 JSON을 생성합니다.
    패턴 1: YYYY년_MM월_BR_passage.png (언더바)
    패턴 2: YYYY년 MM월 QT_passage.png (띄어쓰기)
    """
    
    if not GOOGLE_API_KEY:
        print("❌ 오류: .env 파일에 GOOGLE_API_KEY가 없습니다.")
        return

    # 1. 파일명 조합 (숫자가 6이어도 '06'으로 변환)
    year_str = str(year)
    month_str = str(month).zfill(2) # 1 -> '01', 12 -> '12'

    # 사용자 요청 패턴에 맞춘 파일명 생성
    # 예: 2025년_06월_BR_passage.png
    br_filename = f"{year_str}년_{month_str}월_BR_passage.png"
    # 예: 2025년_06월_QT_passage.png
    qt_filename = f"{year_str}년_{month_str}월_QT_passage.png"

    print(f"\n🔍 파일 찾는 중...")
    print(f"   - 성경읽기: {br_filename}")
    print(f"   - QT본문  : {qt_filename}")

    # 파일 존재 여부 확인
    if not os.path.exists(br_filename) or not os.path.exists(qt_filename):
        print("\n❌ [오류] 파일을 찾을 수 없습니다!")
        print("   파일 이름이 정확한지, 폴더에 파일이 있는지 확인해주세요.")
        return

    print("\n🚀 Gemini 3.0에게 분석 요청 중... (잠시만 기다려주세요)")

    # 2. Gemini 클라이언트 설정
    client = genai.Client(api_key=GOOGLE_API_KEY)
    img1 = PIL.Image.open(br_filename)
    img2 = PIL.Image.open(qt_filename)

    # 3. 프롬프트 (데이터 병합 요청)
    prompt = f"""
    You are a data assistant. I will provide two images for {year_str}-{month_str}.
    - Image 1: Monthly Bible reading plan (New Testament, Psalms, Proverbs).
    - Image 2: Monthly QT (Quiet Time) calendar.

    Your task is to merge them into a SINGLE JSON object.
    
    **Rules:**
    1. Key: Day of the month as a STRING (e.g., "1", "2").
    2. Value: ["New Testament", "Psalms", "Proverbs", "QT Passage"].
    3. If empty, use "".
    4. Ignore headers or date labels.
    
    **Output Example:**
    {{
        "1": ["마1-4", "35", "2", "삼상 1:1-18"],
        "2": ["마5-8", "36", "3", "삼상 1:19-28"]
    }}
    
    Return ONLY raw JSON.
    """

    try:
        # 모델 호출 (Gemini 3.0 Flash Preview)
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt, img1, img2]
        )
        
        # 결과 처리
        cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
        bible_data = json.loads(cleaned_text)
        
        # 날짜순 정렬
        sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

        # 파일 저장 (봇이 바로 읽을 수 있게 bible_plan.json으로 저장)
        output_file = 'bible_plan.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ 성공! {year_str}년 {month_str}월 데이터가 '{output_file}'에 저장되었습니다.")
        print("   이제 봇을 실행하면 이 달의 말씀이 전송됩니다.")
        
    except Exception as e:
        print(f"\n❌ 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    # --- 사용자 입력 ---
    print("=== 📅 월간 성경읽기 JSON 생성기 ===")
    try:
        input_year = input("연도(Year)를 입력하세요 (예: 2025): ").strip()
        input_month = input("월(Month)을 입력하세요 (예: 6): ").strip()
        
        generate_monthly_plan(input_year, input_month)
        
    except KeyboardInterrupt:
        print("\n취소되었습니다.")