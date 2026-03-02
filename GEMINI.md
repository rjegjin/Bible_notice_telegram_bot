# 📖 Bible Notice Telegram Bot - Gemini Guideline

이 프로젝트는 **다국어 성경 읽기표 및 QT 알림**을 자동화하는 시스템입니다.

## 🏗️ 시스템 아키텍처 (Standardized Structure)

- **Entry Point**: `main.py` (모든 작업은 이 파일을 통해 통합 관리)
- **Core Logic**: `core/`
    - `bible_scripture_resolver.py`: 성경 인용구 해석 및 다국어 매핑 엔진
    - `bible_sender.py`: 텔레그램 메시지 발송기
- **Data & Plans**: `data/`
    - `bible.db`: 성경 데이터베이스 (KO, EN, MN)
    - `plans/`: Gemini가 생성한 월별 JSON 계획 파일
- **Tools**: `tools/` (AI 파서 등 관리 도구)
- **Assets**: `assets/` (원본 이미지 보관함)

## 🔐 보안 및 환경 설정 (Secrets Management)

- **중앙 집중식 관리**: 모든 환경 변수는 루트 폴더의 `.secrets/.env`를 우선적으로 참조합니다.
- **필수 변수**: `TELEGRAM_TOKEN`, `GOOGLE_API_KEY`, `KO_CHAT_ID`, `EN_CHAT_ID`, `MN_CHAT_ID`.
- **로컬 Fallback**: 개발 환경에서는 프로젝트 루트의 `.env`를 사용할 수 있으나, Git에는 포함하지 않습니다.

## 🛠️ 개발 지침

1. **곧장 리팩토링된 수준의 개발**: 
    - 새로운 기능을 추가할 때 반드시 `core/` 또는 `tools/`의 적절한 위치에 모듈화하여 배치하십시오.
    - 약어 매핑이나 상수 데이터는 반드시 `bible_scripture_resolver.py`에 통합하여 관리하십시오.
2. **스마트 실행**: 모든 실행은 `python main.py`를 권장하며, 데이터 누락 시 자동으로 AI 파싱이 수행되도록 설계되었습니다.
3. **파일명 규칙**: `assets/`에 이미지를 업로드할 때는 반드시 `{연도}년_{월}월_{구분}_passage` 형식을 준수하십시오.

---
*Last Updated: 2026-03-02*
