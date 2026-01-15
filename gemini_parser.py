import os
import json
import PIL.Image
from dotenv import load_dotenv
from google import genai  # [변경] 새로운 패키지 임포트

# .env 파일 활성화
load_dotenv()

# 환경변수에서 API 키 로드
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

def generate_plan_with_gemini(reading_img_path, qt_img_path):
    if not GOOGLE_API_KEY:
        print("❌ 오류: .env 파일에 GOOGLE_API_KEY가 설정되지 않았습니다.")
        return

    print("🚀 Gemini에게 이미지 분석을 요청합니다... (약 5~10초 소요)")
    
    # [변경] 클라이언트 인스턴스 생성 방식
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    if not os.path.exists(reading_img_path) or not os.path.exists(qt_img_path):
        print(f"❌ 이미지 파일을 찾을 수 없습니다.\n- {reading_img_path}\n- {qt_img_path}")
        return

    # 이미지 파일 열기
    img1 = PIL.Image.open(reading_img_path)
    img2 = PIL.Image.open(qt_img_path)
    
    prompt = """
    You are a data assistant. I will provide two images.
    - Image 1: A monthly Bible reading plan table (New Testament, Psalms, Proverbs).
    - Image 2: A monthly QT (Quiet Time) calendar.

    Your task is to extract data from both images and merge them into a SINGLE JSON object.
    
    **Rules:**
    1. The Key must be the day of the month as a STRING (e.g., "1", "2").
    2. The Value must be a list of 4 strings: [New Testament, Psalms, Proverbs, QT Passage].
    3. If a field is empty, use an empty string "".
    4. Remove headers, "Date", or unnecessary labels.
    
    **Output Format Example:**
    {
        "1": ["마1-4", "35", "2", "삼상 1:1-18"],
        "2": ["마5-8", "36", "3", "삼상 1:19-28"]
    }
    
    Return ONLY the raw JSON string. Do NOT use Markdown code blocks.
    """
    
    try:
        # [변경] 모델 호출 방식 변경 (client.models.generate_content)
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt, img1, img2]
        )
        
        raw_text = response.text
        
        # Markdown 코드 블록 제거
        cleaned_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        bible_data = json.loads(cleaned_text)
        
        # 날짜(숫자) 기준 정렬
        sorted_data = dict(sorted(bible_data.items(), key=lambda item: int(item[0])))

        output_file = 'bible_plan.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 성공! '{output_file}' 파일이 생성되었습니다.")
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    # 실행 전 이미지 파일명을 실제 파일명과 일치시키세요.
    generate_plan_with_gemini("reading_plan.png", "qt_calendar.png")