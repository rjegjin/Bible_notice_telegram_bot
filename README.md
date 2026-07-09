# 📖 다국어 성경 읽기 & QT 알림 텔레그램 봇 🤖
> **"이미지 한 장으로 시작하는 스마트한 성경 읽기 생활"**

이 봇은 매일 아침 정해진 시간에 **성경 읽기 진도**와 **오늘의 QT 본문**을 텔레그램으로 자동 발송합니다. 인공지능(OpenAI Vision)이 두 종류의 이미지(성경 읽기표, QT 본문표)를 동시에 분석하여 데이터를 통합 생성하며, 한국어·영어·몽골어의 3개 국어를 지원합니다.

---

## ✨ 주요 기능 (Key Features)

*   **통합 관리 (`main.py`)**: 단 한 줄의 명령어로 데이터 생성부터 발송까지 완벽 제어.
*   **고지능 AI 파싱**: `OpenAI Vision` + `Structured Outputs`가 여러 장의 이미지를 동시에 분석하여 5가지 요소(`신약`, `구약`, `시편`, `잠언`, `QT`)를 JSON Schema에 맞춰 정밀하게 추출합니다.
*   **자동 권수 상속**: 읽기표 이미지에 권수가 생략되어도 AI가 이전 날짜의 정보를 추론하여 데이터를 보정합니다.
*   **스마트 발송 시스템**: 긴 신약/구약 본문은 제외하고, 묵상에 필요한 **QT, 시편, 잠언 본문만 전문 전송**하여 가독성을 높였습니다.
*   **다국어 지원**: 한국어(개역한글), 영어(ESV/NLT), 몽골어(MUV/키릴 문자) 지원.
*   **Provider 추상화**: `ai/` 패키지가 AI 모델 호출부를 분리하고 있어, 향후 다른 모델(Claude/Gemini 등)로 교체하더라도 `main.py`나 파서 로직은 변경할 필요가 없습니다.

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
OPENAI_API_KEY="sk-..."
TELEGRAM_TOKEN="..."
KO_CHAT_ID="..."
EN_CHAT_ID="..."
MN_CHAT_ID="..."

# 선택 (기본값: gpt-5.5)
OPENAI_MODEL="gpt-5.5"
```

이 프로젝트는 `OPENAI_API_KEY`와 `OPENAI_MODEL`만으로 동작하며, Google Gemini 관련 API Key는 더 이상 필요하지 않습니다.
(단, `assets/`에 이미지가 없을 때 Google Drive에서 자동으로 이미지를 가져오는 기능은 별도로 Google 서비스 계정 키(`.secrets/service_key.json`)를 사용합니다. AI 분석과는 무관합니다.)

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

기본 모델은 `gpt-5.5`입니다. 다른 Vision 지원 모델로 바꾸려면 환경변수만 수정하면 됩니다.

```dotenv
OPENAI_MODEL="gpt-4.1"
```

코드 변경이나 재배포는 필요하지 않습니다.

---

## 🩹 오류 해결 방법 (Troubleshooting)

| 증상 | 원인 | 해결 방법 |
|---|---|---|
| `OPENAI_API_KEY가 없습니다` | `.env`에 키가 없거나 경로가 틀림 | `.secrets/.env` 또는 프로젝트 루트 `.env`에 `OPENAI_API_KEY` 추가 |
| `OpenAI 인증 실패` | API 키가 잘못되었거나 만료됨 | [OpenAI 대시보드](https://platform.openai.com/api-keys)에서 키 재발급 |
| `OpenAI 서버에 연결할 수 없습니다` | 네트워크 문제 또는 OpenAI 장애 | 잠시 후 재시도, 방화벽/프록시 확인 |
| `insufficient_quota` (429) | OpenAI 계정 크레딧/결제 한도 초과 | [Billing 페이지](https://platform.openai.com/account/billing)에서 결제 수단/한도 확인 |
| `OpenAI 응답이 최대 토큰 길이에서 잘렸습니다` | 이미지가 너무 많거나 복잡함 | 이미지를 나눠서 요청하거나 재시도 |
| `JSON 파싱 실패` / Schema 오류 | 매우 드묾 (Structured Outputs로 강제됨) | 재시도, 그래도 반복되면 이미지 화질 확인 |
| `2월 데이터가 없습니다...` | `assets/`에 이미지가 없고 Google Drive에도 없음 | `assets/{연도}년_{월}월_BR_passage.jpg`, `..._QT_passage.jpg` 파일 추가 |

오류 발생 시 콘솔에 `[INFO]/[SUCCESS]/❌` 형식의 로그와 함께 상세 Stack Trace가 함께 출력되므로, 로그를 그대로 확인하면 원인 파악에 도움이 됩니다.

---

## 🤖 자동화 (GitHub Actions)
`GitHub Actions`를 통해 서버 없이도 매일 아침 자동으로 실행됩니다. 데이터가 누락되어도 **스마트 모드**를 통해 당일 아침 자동으로 파싱 및 발송을 수행합니다. (Repository Secrets에 `OPENAI_API_KEY`를 등록해야 합니다.)

---
*마지막 업데이트: 2026년 7월 1일 (OpenAI 기반으로 리팩터링)*
