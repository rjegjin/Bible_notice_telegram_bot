import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 저장할 파일 이름과 경로 (원하는 곳으로 변경 가능)
output_file = "available_gemini_models.txt"

print(f"🔍 사용 가능한 모델 목록을 '{output_file}' 파일로 저장 중...")

try:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== Google Gemini 사용 가능한 모델 목록 ===\n")
        f.write(f"조회 시각: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        model_count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                model_name = m.name
                f.write(f"- {model_name}\n")
                print(f"- {model_name}")  # 화면에도 동시에 보고 싶으면 이 줄 유지
                model_count += 1
        
        f.write(f"\n총 {model_count}개의 텍스트 생성 가능 모델이 있습니다.\n")

    print(f"✅ 완료! 총 {model_count}개 모델을 '{output_file}'에 저장했습니다.")

except Exception as e:
    error_msg = f"오류 발생: {e}"
    print(error_msg)
    # 에러가 나도 파일에 기록되게 하고 싶다면
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(error_msg)