# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**

이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(Gemini)이 두 종류의 이미지(성경 읽기표, QT 본문표)를 동시에 분석하여 데이터를 통합 생성하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **통합 관리 (`main.py`)**: 단 한 줄의 명령어로 데이터 생성부터 발송까지 완벽 제어.
*   **고지능 AI 파싱**: `Gemini 2.0 Flash`가 여러 장의 이미지를 동시에 분석하여 5가지 요소(`신약`, `구약`, `시편`, `잠언`, `QT`)를 정밀하게 추출합니다.
*   **자동 권수 상속**: 읽기표 이미지에 권수가 생략되어도 AI가 이전 날짜의 정보를 추론하여 데이터를 보정합니다.
*   **스마트 발송 시스템**: 긴 신약/구약 본문은 제외하고, 묵상에 필요한 **QT, 시편, 잠언 본문만 전문 전송**하여 가독성을 높였습니다.
*   **다국어 지원**: 한국어(개역한글), 영어(ESV/NLT), 몽골어(MUV/키릴 문자) 지원.

---

## 🚀 퀵 스타트 (Quick Start)

### 1. 가상환경 및 설치
```bash
git clone https://github.com/rjegjin/Bible_notice_telegram_bot.git
cd Bible_notice_telegram_bot
source ../unified_venv/bin/activate
pip install -r requirements.txt
```

### 2. 통합 명령어 사용 (모든 기능 하나로!)
```bash
# [추천] 스마트 실행 (데이터가 없으면 자동 생성 후 오늘 본문 발송)
python main.py

# 메시지만 즉시 발송하고 싶을 때
python main.py send

# 개인 대화방으로 3개 국어 요약본(진도표)만 보내고 싶을 때
python main.py summary

# 최근 메시지를 통해 새로운 채팅방 ID를 확인하고 싶을 때
python main.py check

# 특정 달의 데이터를 강제로 새로 생성하고 싶을 때
python main.py parse 2026 3
```

---

## 📂 폴더 구조 (Project Structure)

*   `main.py`: 통합 실행 엔트리 포인트 (봇의 심장)
*   `core/`: 핵심 비즈니스 로직 (성경 해석 및 텔레그램 발송)
*   `data/`: 데이터 저장소 (SQLite 성경 DB 및 날짜별 계획 JSON)
*   `tools/`: AI 파서 및 관리용 유틸리티
*   `assets/`: 성경 읽기표/QT 이미지 보관함 (형식: `{연도}년_{월}월_{구분}_passage`)

---

## 🤖 자동화 (GitHub Actions)
`GitHub Actions`를 통해 서버 없이도 매일 아침 자동으로 실행됩니다. 데이터가 누락되어도 **스마트 모드**를 통해 당일 아침 자동으로 파싱 및 발송을 수행합니다.

---
*마지막 업데이트: 2026년 3월 2일*
