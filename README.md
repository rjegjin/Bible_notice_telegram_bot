# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**

이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(Gemini)을 활용해 복잡한 성경 읽기표 이미지를 데이터로 자동 변환하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **통합 관리 (`main.py`)**: 명령어 하나로 데이터 생성부터 발송까지 한 번에 처리합니다.
*   **성경 본문 해석기 (`BibleScriptureResolver`)**: 복잡한 인용구(예: `시 1-3`, `사 53:1-12`)를 분석하고 다국어 본문을 매칭하는 강력한 핵심 엔진을 탑재했습니다.
*   **AI 자동 파싱**: `Gemini 2.0 Flash`가 이미지를 분석하여 5가지 요소(`신약`, `구약`, `시편`, `잠언`, `QT`)를 자동 추출하고 생략된 권수까지 똑똑하게 추론하여 저장합니다.
*   **스마트 발송 시스템**: 긴 구약과 신약 본문은 요약본(진도표)에만 표시하고, 실제 묵상에 필요한 **QT, 시편, 잠언 본문만 텔레그램으로 전송**하여 피로도를 줄였습니다.
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

### 2. 스마트 실행
```bash
# 데이터가 없으면 자동 생성 후 오늘 본문 발송
python main.py
```

---

## 📂 폴더 구조 (Project Structure)

*   `main.py`: 통합 실행 엔트리 포인트
*   `core/`: 핵심 비즈니스 로직
    *   `bible_scripture_resolver.py`: **[핵심]** 성경 본문 해석 및 다국어 매핑 엔진
    *   `bible_sender.py`: 텔레그램 발송 엔진
*   `data/`: 데이터 저장소 (`bible.db`, `plans/`)
*   `tools/`: AI 파서 및 관리용 도구
*   `assets/`: 성경 읽기표/QT 이미지 보관함

---
*마지막 업데이트: 2026년 3월 2일*
