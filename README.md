# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**

이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(OpenAI Vision)이 두 종류의 이미지(성경 읽기표, QT 본문표)를 동시에 분석하여 데이터를 통합 생성하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **통합 관리 (`main.py`)**: 단 한 줄의 명령어로 데이터 생성부터 발송까지 완벽 제어 + 웹 GUI 관리봇 (`manager_bot.py`).
*   **고지능 AI 파싱**: Vision 기능을 지닌 여러 AI 모델(기본값: Gemini 무료 티어, OpenAI 선택 가능)이 성경 읽기표 + QT 본문표 2장의 이미지를 동시에 분석하여 5가지 요소(`신약`, `구약`, `시편`, `잠언`, `QT`)를 정밀하게 추출합니다.
*   **자동 권수 상속**: 읽기표 이미지에 권수가 생략되어도 AI가 이전 날짜의 정보를 추론하여 데이터를 보정합니다.
*   **스마트 발송 시스템**: 긴 신약/구약 본문은 제외하고, 묵상에 필요한 **QT, 시편, 잠언 본문만 전문 전송**하여 가독성을 높였습니다.
*   **다국어 지원**: 한국어(개역한글), 영어(ESV/NLT), 몽골어(MUV/키릴 문자) 지원.
*   **Provider 추상화**: `ai/` 패키지가 AI 모델 호출부를 분리하고 있어, 환경변수 `AI_PROVIDER`로 Gemini ↔ OpenAI 전환 가능 (코드 변경 불필요). `manager_bot.py`는 `bot_common` 헬퍼 모듈로 Telegram 부트스트랩 단순화.

---

## 🚀 퀵 스타트 (Quick Start)

### 1. 가상환경 및 설치
```bash
git clone https://github.com/rjegjin/Bible_notice_telegram_bot.git
cd Bible_notice_telegram_bot
source ../unified_venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.secrets/.env` (또는 프로젝트 루트 `.env`)에 아래 값을 설정합니다.

```dotenv
# 필수
TELEGRAM_TOKEN="..."
KO_CHAT_ID="..."
EN_CHAT_ID="..."
MN_CHAT_ID="..."

# AI 공급자 선택 (기본값: gemini = Google Gemini 무료 티어)
AI_PROVIDER="gemini"          # 또는 "openai"
GOOGLE_API_KEY="..."          # Gemini 사용 시 필수
# OPENAI_API_KEY="sk-..."     # OpenAI 사용 시 필수 (AI_PROVIDER="openai" 설정 필요)
```

**비용 최적화**: 기본값은 Gemini 무료 티어(`gemini-2.5-flash`)입니다. OpenAI로 전환하려면 `AI_PROVIDER=openai`로 변경하고 `OPENAI_API_KEY` 설정 후 결제 수단 등록이 필요합니다.

*선택 항목*:
- `GEMINI_MODEL`: Gemini 모델 명시 (기본값: `gemini-2.5-flash`)
- `OPENAI_MODEL`: OpenAI 모델 명시 (기본값: `gpt-4o`)
- Google Drive 자동 이미지 가져오기: 별도 Google 서비스 계정 키(`.secrets/service_key.json`)가 필요합니다.

### 3. 통합 명령어 사용 (모든 기능 하나로!)
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
*   `ai/`: AI Provider 추상화 계층
    *   `interfaces.py`: `ImageAnalysisProvider` 인터페이스 및 예외 타입 정의
    *   `openai_provider.py`: OpenAI Vision + Structured Outputs 구현체
    *   `provider.py`: `get_provider()` 팩토리 (환경변수 `AI_PROVIDER`로 교체 가능, 기본값 `openai`)
*   `core/`: 핵심 비즈니스 로직 (성경 해석 및 텔레그램 발송)
*   `data/`: 데이터 저장소 (SQLite 성경 DB 및 날짜별 계획 JSON)
*   `tools/`: AI 파서 및 관리용 유틸리티 (`plan_parser.py`가 이미지 → JSON 변환 담당)
*   `assets/`: 성경 읽기표/QT 이미지 보관함 (형식: `{연도}년_{월}월_{구분}_passage`)

---

## 🔧 모델 변경 방법

기본 AI 공급자는 **Gemini**(무료 티어)입니다. 다른 모델로 전환하려면 환경변수만 수정하면 됩니다.

**Gemini 모델 변경**:
```dotenv
AI_PROVIDER="gemini"
GEMINI_MODEL="gemini-2.0-flash"  # 기본값: gemini-2.5-flash
```

**OpenAI로 전환**:
```dotenv
AI_PROVIDER="openai"
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o"  # 기본값: gpt-4o
```

코드 변경이나 재배포는 필요하지 않습니다.

---

## 🩹 오류 해결 방법 (Troubleshooting)

| 증상 | 원인 | 해결 방법 |
|---|---|---|
| `GOOGLE_API_KEY가 없습니다` | Gemini 사용 시 `.env`에 키가 없음 | `.secrets/.env`에 `GOOGLE_API_KEY` 추가 또는 `AI_PROVIDER=openai` + `OPENAI_API_KEY` 설정 |
| `OPENAI_API_KEY가 없습니다` | OpenAI 사용(`AI_PROVIDER=openai`)시 키가 없음 | [OpenAI 대시보드](https://platform.openai.com/api-keys)에서 키 생성 후 `.secrets/.env`에 추가 |
| API 인증 실패 | API 키가 잘못되었거나 만료됨 | 해당 AI 공급자 대시보드에서 키 재발급 |
| 서버에 연결할 수 없습니다 | 네트워크 문제 또는 API 장애 | 잠시 후 재시도, 방화벽/프록시 확인 |
| `insufficient_quota` (OpenAI 429) | 계정 크레딧/결제 한도 초과 | [Billing 페이지](https://platform.openai.com/account/billing)에서 결제 수단/한도 확인 또는 Gemini로 전환 |
| `JSON 파싱 실패` | 매우 드묾 | 이미지 화질 확인 후 재시도 |
| `{월} 데이터가 없습니다...` | `assets/`에 이미지가 없고 Google Drive도 비어있음 | `assets/{연도}년_{월}월_BR_passage.jpg`, `..._QT_passage.jpg` 파일 추가 |

오류 발생 시 콘솔에 `[INFO]/[SUCCESS]/❌` 형식의 로그와 함께 상세 Stack Trace가 함께 출력되므로, 로그를 그대로 확인하면 원인 파악에 도움이 됩니다.

---

## 🤖 자동화 (GitHub Actions & systemd Timer)
기본적으로 `mh_bot` 서버의 `systemd` user timer(`bible-daily-send.timer`)가 매일 정해진 시간에 `manager_bot.py run` 명령을 수행합니다. (실제 발송은 `mh_bot`@100.103.20.9에서 관리됨)

`GitHub Actions`의 `daily_bible.yml`은 `workflow_dispatch` 전용이며, 자동 스케줄은 systemd timer로 대체되었습니다.

---
*마지막 업데이트: 2026년 7월 6일 (bot_common 헬퍼 모듈 도입 + Gemini 기본값 정의)*
