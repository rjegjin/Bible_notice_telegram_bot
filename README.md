# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**
> 
> 이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(Gemini)을 활용해 복잡한 성경 읽기표 이미지를 데이터로 자동 변환하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **AI 자동 파싱**: 성경 읽기표 이미지를 `Gemini 2.0 Flash`가 읽고 날짜별 JSON 데이터로 자동 변환합니다. (수동 입력 불필요!)
*   **다국어 본문 지원**: 
    *   **한국어**: 개역한글판 (KRV)
    *   **영어**: ESV, NLT
    *   **몽골어**: MUV
*   **스마트 발송 시스템**: 요약 메시지 전송 후, 사용자가 바로 읽을 수 있도록 성경 본문 전체를 이어서 발송합니다.
*   **무중단 자동화**: GitHub Actions를 통해 서버 없이도 매일 정해진 시간에 알림을 보낼 수 있습니다.

---

## 🛠️ 시작하기 전에 (Prerequisites)

이 프로젝트를 실행하려면 다음 항목이 준비되어야 합니다.

### 1. 필수 도구 및 계정
*   **Python 3.10+**: 시스템에 설치되어 있어야 합니다.
*   **Telegram Bot Token**: [@BotFather](https://t.me/botfather)에게 메시지를 보내 생성하세요.
*   **Google Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)에서 무료로 발급받으세요.

### 2. 지원되는 이미지 형식 (Supported Image Formats)
Gemini AI가 분석 가능한 다음의 이미지 형식을 준비하세요.
*   **형식**: `JPG`, `JPEG`, `PNG`, `WEBP`
*   **권장 사항**: 텍스트가 선명하게 보이는 고해상도 이미지일수록 AI 분석 정확도가 높아집니다.

### 3. Telegram Chat ID 확인 방법
메시지를 받을 대상에 따라 Chat ID 형식이 다릅니다.

*   **개인 대화 (1:1)**:
    *   텔레그램에서 [@userinfobot](https://t.me/userinfobot) 검색 후 `/start`를 누르면 나오는 `Id` 숫자(예: `12345678`)를 사용합니다.
*   **단체 대화방 (Group)**:
    *   알림을 보낼 그룹 방에 봇을 초대합니다.
    *   해당 방에서 [@get_id_bot](https://t.me/get_id_bot)을 초대하거나, 웹 브라우저 주소창 또는 API를 통해 확인합니다.
    *   **주의**: 단체방 ID는 보통 **마이너스(`-`) 기호**로 시작합니다 (예: `-100123456789`). 이 기호까지 모두 포함하여 입력해야 합니다.

---

## 🚀 설치 및 설정 (Setup)

### 1. 저장소 복제 및 가상환경 설정
프로젝트 표준 가상환경(`unified_venv`) 사용을 권장합니다.

```bash
# 1. 저장소 복제
git clone https://github.com/rjegjin/Bible_notice_telegram_bot.git
cd Bible_notice_telegram_bot

# 2. 가상환경 활성화 (Linux/macOS 기준)
source ../unified_venv/bin/activate

# 3. 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (`.env`)
프로젝트 루트 폴더에 `.env` 파일을 생성하고 아래 내용을 입력하세요.

```ini
# 텔레그램 봇 토큰
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Google Gemini API 키
GOOGLE_API_KEY=your_gemini_api_key_here

# 수신처 Chat ID (예시)
KO_CHAT_ID=12345678        # 개인 대화 ID (양수)
EN_CHAT_ID=-100123456789   # 단체 대화방 ID (음수, - 포함)
MN_CHAT_ID=34567890
```

---

## 📅 사용 방법 (Usage Workflow)

봇 운영은 **[데이터 구축]**과 **[자동 발송]** 두 단계로 나뉩니다.

### Step 1: 성경 읽기표 이미지 변환 (AI 파싱)
매달 한 번만 실행하면 됩니다.

1.  월간 읽기표 이미지를 `assets/` 폴더에 넣습니다. (파일 확장자: .jpg, .png 등)
2.  아래 명령어를 실행합니다 (예: 2026년 3월 데이터 생성 시).
    ```bash
    python tools/gemini_parser.py 2026 3
    ```
3.  Gemini가 이미지를 분석하여 `plans/03.json` 파일을 자동으로 생성합니다.

### Step 2: 알림 발송 테스트
생성된 데이터를 바탕으로 실제로 텔레그램 메시지를 보냅니다.

```bash
python send_bible_passage_all.py
```
*이 스크립트가 실행되면 한국 시간(KST) 기준 오늘 날짜의 본문을 찾아 발송합니다.*

---

## 📂 폴더 구조 (Project Structure)

```text
.
├── assets/                 # 성경 읽기표/QT 이미지 보관 (.jpg, .png, .webp)
├── plans/                  # Gemini가 생성한 월별 읽기 데이터 (JSON)
├── tools/                  # 관리자용 도구 모음
│   ├── gemini_parser.py    # 이미지 -> JSON 변환 AI 도구
│   ├── build_bible_db.py   # 성경 DB 구축 스크립트
│   └── inspect_db.py       # DB 내용 확인 도구
├── bible.db                # [핵심] 3개 국어 성경 본문 데이터베이스
├── bible_common.py         # 공통 비즈니스 로직 (DB 조회, 번역)
├── send_bible_passage_all.py # [실행] 일일 알림 발송 메인 스크립트
└── requirements.txt        # 설치가 필요한 라이브러리 목록
```

---

## 🤖 자동화 (GitHub Actions)

매일 수동으로 실행할 필요가 없습니다. `.github/workflows/` 설정(별도 구성 필요)을 통해 매일 아침 6시(한국 시간)에 봇이 작동하도록 자동화할 수 있습니다. 
*GitHub Secrets에 `.env`에 적힌 변수들을 동일하게 등록해 주세요.*

---

## ❓ 자주 묻는 질문 (FAQ)

**Q: 특정 날짜의 본문이 틀리게 분석되었어요.**
A: `plans/*.json` 파일을 열어 해당 날짜의 텍스트를 수동으로 수정한 뒤 저장하면 됩니다.

**Q: 단체방에 메시지가 안 가요.**
A: Chat ID에 마이너스(`-`) 기호가 포함되어 있는지 확인하고, 봇이 해당 방에 '관리자' 혹은 '메시지 전송 권한'이 있는 멤버로 초대되어 있는지 확인하세요.

---

### 📄 라이선스
이 프로젝트는 개인적인 신앙 생활과 공동체 섬김을 위해 제작되었습니다. 자유롭게 수정 및 배포가 가능합니다.

---
*마지막 업데이트: 2026년 3월 2일*
