# 📖 Bible Notice Telegram Bot - Gemini Guideline

이 프로젝트는 **다국어 성경 읽기표 및 QT 알림**을 자동화하는 시스템입니다.

## 🏗️ 시스템 아키텍처 (Standardized Structure)

- **Entry Point**: `main.py` (명령어: `run`, `parse`, `send`, `summary`, `check`)
- **Core Logic**: `core/`
    - `bible_scripture_resolver.py`: 성경 인용구 해석 및 다국어 매핑 엔진
    - `bible_sender.py`: 텔레그램 메시지 발송기
- **Data & Plans**: `data/`
    - `bible.db`: 성경 데이터베이스 (KO, EN, MN)
    - `plans/`: Gemini가 생성한 월별 JSON 계획 파일
- **Tools**: `tools/` (AI 파서, ID 확인 도구 등)
- **Assets**: `assets/` (원본 이미지 보관함)

## 🔐 보안 및 환경 설정 (Secrets Management)

- **중앙 집중식 관리**: 모든 환경 변수는 루트 폴더의 `.secrets/.env`를 우선적으로 참조합니다.
- **필수 변수**: `TELEGRAM_TOKEN`, `GOOGLE_API_KEY`, `KO_CHAT_ID`, `EN_CHAT_ID`, `MN_CHAT_ID`.

## 🛠️ 개발 및 데이터 지침

1. **데이터 파싱 및 발송 규칙**:
    - **JSON 구조**: `[신약, 구약, 시편, 잠언, QT]`의 5개 요소 순서를 반드시 유지해야 합니다.
    - **본문 발송**: 구약과 신약은 길이가 길어 진도표(요약)에만 표시하고, 실제 본문은 **QT, 시편, 잠언**만 전송합니다.
    - **상속 및 보정**: `gemini_parser.py`가 이전 날짜의 권수를 자동 상속하고, 풀네임을 약어(예: 마태복음 -> 마)로 자동 보정합니다.
2. **이미지 처리**: `assets/` 폴더에 `{연도}년_{월}월_{구분}_passage` 형식으로 업로드하십시오. (구분: `BR`=읽기표, `QT`=QT표)
3. **GitHub Actions**: `daily_bible.yml`은 `python main.py` 스마트 모드를 사용하여 데이터 누락에 자동 대응합니다.

---
*Last Updated: 2026-03-02*
