# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**
> 
> 이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(Gemini)을 활용해 복잡한 성경 읽기표 이미지를 데이터로 자동 변환하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **통합 관리 (`main.py`)**: 명령어 하나로 데이터 생성부터 발송까지 한 번에 처리합니다.
*   **스마트 자동 실행**: 오늘 날짜의 데이터(JSON)가 없으면 `assets/` 폴더를 확인해 자동으로 AI 파싱을 먼저 수행합니다.
*   **AI 자동 파싱**: 성경 읽기표 이미지를 `Gemini 2.0 Flash`가 읽고 날짜별 JSON 데이터로 변환합니다.
*   **다국어 본문 지원**: 한국어(개역한글), 영어(ESV/NLT), 몽골어(MUV) 지원.

---

## 🛠️ 시작하기 전에 (Prerequisites)

### 1. 필수 도구 및 계정
*   **Python 3.10+** (시스템 설치)
*   **Telegram Bot Token** ([@BotFather](https://t.me/botfather))
*   **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))

### 2. 파일 이름 규칙 (중요!)
`assets/` 폴더에 이미지를 넣을 때 아래 형식을 지켜주세요.
*   **성경 읽기표**: `2026년_03월_BR_passage.png`
*   **QT 본문표**: `2026년_03월_QT_passage.jpg`
*   *월(Month)은 반드시 2자리(01, 02... 12)로 입력하세요.*

---

## 🚀 설치 및 사용 방법 (Quick Start)

### 1. 가상환경 및 설치
```bash
git clone https://github.com/rjegjin/Bible_notice_telegram_bot.git
cd Bible_notice_telegram_bot
source ../unified_venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (`.env`)
루트 폴더에 `.env` 파일을 생성하고 발급받은 키 값과 수신처 Chat ID를 입력합니다.

### 3. 명령어 하나로 실행
이제 여러 스크립트를 옮겨 다닐 필요가 없습니다.

```bash
# [추천] 스마트 실행: 데이터가 없으면 자동 생성 후 오늘 본문 발송
python main.py

# 특정 연도/월 데이터를 생성하고 발송하고 싶을 때
python main.py run --year 2026 --month 4

# 데이터(JSON)만 생성하고 싶을 때
python main.py parse 2026 3

# 메시지만 즉시 발송하고 싶을 때
python main.py send
```

---

## 📂 폴더 구조 (Project Structure)

*   `main.py`: **[핵심]** 모든 기능을 통합 관리하는 실행 파일
*   `assets/`: 성경 읽기표/QT 이미지 보관 (.jpg, .png 등)
*   `plans/`: Gemini가 생성한 월별 데이터 (JSON)
*   `tools/`: AI 파서 및 DB 관리 도구 모음
*   `bible.db`: 3개 국어 성경 데이터베이스

---

## 🤖 자동화 (GitHub Actions)
GitHub Actions에서 `python main.py`를 매일 실행하도록 설정하면, 매달 새로운 이미지를 `assets/`에 업로드하는 것만으로 봇 운영이 가능합니다.

---

### 📄 라이선스
개인 및 공동체 신앙 생활을 위해 자유롭게 사용 및 수정 가능합니다.

---
*마지막 업데이트: 2026년 3월 2일*
