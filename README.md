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
EN_CHAT_ID="..."          # owner 개인방 호환값
EN_GROUP_CHAT_ID="..."    # 별도 영어 그룹방
MN_CHAT_ID="..."
BIBLE_OWNER_CHAT_ID="..."   # 개인 3개 국어 요약 수신처

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

# 방 하나만 선택 발송
python main.py send --target ko  # ko / en / mn / owner / all

# all: KO/MN 그룹에는 전문, owner 개인방에는 3개 국어 요약만 발송
python main.py send --target all

# 지정 날짜 말씀 재전송 (Telegram: /send 2026-09-11 ko)
python main.py send --date 2026-09-11 --target ko

# 이번 주 특정 요일 기도제목 재호출 (Telegram owner 개인방: /prayerday 월)
python main.py prayer send --date 2026-09-14 --force --chat-id "..."

# 이번 주 특정 요일 OAT 기도제목 재호출 (Telegram owner 개인방: /oatday 월)
python main.py prayer oat-send --date 2026-09-14 --force --chat-id "..."

# 개인 대화방으로 3개 국어 요약본(진도표)만 보내고 싶을 때
python main.py summary

# 특정 대화방으로 명시해서 보내기 (관리봇은 현재 대화방 ID를 자동 전달)
python main.py summary --chat-id "..."

# 최근 메시지를 통해 새로운 채팅방 ID를 확인하고 싶을 때
python main.py check

# 특정 달의 데이터를 강제로 새로 생성하고 싶을 때
python main.py parse 2026 3
```

### 4. 월별 말씀 plan 관리 UI

```bash
# 대화형 관리 메뉴
python main.py plan

# 보유 월 목록 / 조회 / 검증
python main.py plan list
python main.py plan show 2026 7
python main.py plan show 2026 7 --day 15
python main.py plan validate 2026 7

# 특정 날짜 수정: diff 확인 후 --yes가 있어야 비대화식 저장
python main.py plan edit 2026 7 15 --qt "요 5:1-18" --yes

# Telegram 발송 없는 요약 미리보기
python main.py plan preview 2026 7 15 --lang ALL

# [권장] asset 재파싱 → JSON 교체 → mh_bot 배포 → owner Telegram test
python main.py plan publish 2026 7

# 임의 파일명의 이미지를 표준 asset 이름으로 가져오기
python main.py plan import-images 2026 8 \
  --br ~/Downloads/br.jpg \
  --qt ~/Downloads/qt.jpg

# 주간기도제목 이미지 OCR: 13명을 월 3명, 화~토 2명씩 저장
python main.py prayer import ~/Downloads/주간기도제목.jpg

# 오늘 배정 미리보기 / 발송
python main.py prayer approve
python main.py prayer send --dry-run
python main.py prayer send

# 기존 파일 backup 후 OCR 재생성
python main.py plan reparse 2026 7

# 이미 생성된 JSON만 검증 후 운영 mh_bot에 재반영
python main.py plan deploy 2026 7

# HWPX parsing은 기본 OFF. 필요할 때만 명시적으로 toggle
python main.py parse --hwpx-status
python main.py parse --enable-hwpx
python main.py parse --disable-hwpx
```

수정 저장은 `data/plans/backups/`에 원본을 보관한 뒤 atomic replace로 처리합니다.
검증에 실패하면 원본 JSON을 변경하지 않습니다. `deploy`는 로컬 검증과 원격
검증을 모두 통과해야 완료됩니다. asset 자체가 바뀐 경우에는 `deploy`가 아니라
`publish`를 사용해야 하며, publish 실패 시 backup을 복원하고 배포와 Telegram
test를 중단합니다.

`assets/`에 이미지를 복사하는 것만으로 JSON 생성이나 운영 배포가 자동 실행되지는
않습니다. `import-images`는 이미지 유효성을 확인하고
`YYYY년_MM월_BR_passage`/`QT_passage` 이름으로 정리하며, 기존 파일 교체에는
`--replace`가 필요합니다. 가져온 뒤 `publish`를 실행해야 JSON 생성·운영 배포·
Telegram test가 완료됩니다. 운영 06:00 timer는 `send`만 실행하므로 월말에 미리
`publish`하는 방식을 권장합니다.

### Quiet Time 월별 Google Docs 탭

`plan publish YEAR MONTH`는 OCR/월 검증 후 기존 Google Doc
`1v4qG2b2jKL8j2JUhqCIWJbNTSctCnp10vQo4y7rUv3s`의 `M월` 탭을 생성/갱신합니다.
문서 새 파일은 만들지 않습니다. 제목은 `YYYY년 M월 Quiet Time 적용 시트`입니다.

```text
BR/QT asset → publish → OCR → 월 검증 → 월 탭 생성/갱신 → Docs readback → 배포 → owner test
                         실패: JSON 복원    실패/충돌: 배포 중단
```

```bash
python main.py plan sheet 2026 10                 # 기존 검증된 JSON으로 Docs만 갱신
python main.py plan publish 2026 10 --yes          # 전체 흐름
python main.py plan publish 2026 10 --yes --no-sheet  # 긴급 Docs 생략
```

- 기존 service account의 Cloud project에서 Google Docs API를 활성화하고, 대상 문서를
  해당 계정에 **편집자**로 공유해야 합니다. 키를 변경하거나 코드에 넣지 않습니다.
- 설치: unified environment에서 `pip install -r requirements.txt`.
- 1~15일/16~말일의 7열 표, 148×203mm, section break와 양면 여백을 적용합니다.
- 같은 월 갱신 시 사용자의 중심구절·제목·적용·체크 텍스트는 보존합니다.
  다른 연도나 예상과 다른 기존 표 구조는 덮어쓰지 않고 중단합니다.
- 모든 쓰기는 대상 `tabId`와 직전 revision을 명시합니다. 날짜·요일·전체 QT 본문을
  readback 검증하며, 실패 후에도 검증된 로컬 JSON과 기존 backup은 남습니다.
  Docs는 여러 batch이므로 일부 변경이 남을 수 있습니다. 동일 월 재실행으로 재개합니다.
- 공휴일은 `holidays`의 KR PUBLIC 달력(음력·대체공휴일 포함)을 사용합니다.
  새 임시공휴일 발표 시 패키지를 갱신해야 합니다.
- 최초 실문서 실행 후 PDF로 정확한 2쪽 배치와 여백을 확인해야 합니다.
  API 구조 검증만으로 인쇄 페이지 수를 보장하지 않습니다.

주간기도제목은 owner 개인방에서 사진 caption을 `/prayer`로 보내도 가져올 수 있습니다.
OCR 결과가 정확히 13명일 때만 저장되며, 요일별 이름을 검토하고 `/prayerapprove`로
승인해야 합니다. 승인 뒤 기존 일일 `run`/`send --target all` 실행이 매일 06:00 KST에
월요일 3명, 화~토요일 2명을 `PRAYER_CHAT_ID`(없으면 MydailyBibleBot owner 개인방)로 한 사람당
한 메시지씩 보냅니다. 사람별 발송 marker를 남겨 같은 날 재실행해도 중복 발송하지
않습니다.

월별 QT/BR 사진은 owner 개인방에서 각각 `/qt 2026 10`, `/br 2026 10`처럼
caption을 붙여 보냅니다. 한 장만 도착하면 상대 이미지를 기다리고, 두 장이 모두
모이면 OCR과 월 전체 검증 후 `data/plans/standby/2026_10.json`에 저장합니다.
standby 파일은 자동 발송·Docs 갱신·운영 배포에 사용되지 않으며, 검토 후 기존
`plan publish`로 **같은 JSON을 재OCR 없이** 승격합니다. standby가 없을 때만
기존 이미지 OCR 경로를 사용합니다.

주간기도 원본은 `data/prayers/sources/`에 주차별로 보존됩니다. OCR 직후 전체
기도문 미리보기가 owner 방에 분할 전송되며 `/prayerpreview`로 다시 확인할 수
있습니다. `/prayerapprove`는 `future_only` 정책으로 승인하여 이미 지난 날짜를
자동 보충 발송하지 않습니다.

2026년 2학기 OAT는 `data/prayers/2026_H2_oat.json`에서 관리합니다. 2026-09-07부터
같은 06:00 KST 실행에서 요일별 담당자에게 매주 다음 기도제목 1개를 별도 메시지로
보냅니다. 수요일에는 `정석훈 → 심창민 → 이준우` 순서이며, OAT 전용 marker로
중복을 막습니다. `python main.py prayer oat-send --date YYYY-MM-DD --dry-run`으로
해당 날짜를 미리 볼 수 있습니다. OAT는 현재 기존 JSON을 읽어 발송하며, 이미지 OCR
추출 기능은 없습니다.

---

## 📂 폴더 구조 (Project Structure)

*   `main.py`: 통합 실행 엔트리 포인트 (봇의 심장)
*   `ai/`: AI Provider 추상화 계층
    *   `interfaces.py`: `ImageAnalysisProvider` 인터페이스 및 예외 타입 정의
    *   `openai_provider.py`: OpenAI Vision + Structured Outputs 구현체
    *   `provider.py`: `get_provider()` 팩토리 (환경변수 `AI_PROVIDER`로 교체 가능, 기본값 `openai`)
*   `core/`: 핵심 비즈니스 로직 (성경 해석 및 텔레그램 발송)
*   `data/`: 데이터 저장소 (SQLite 성경 DB 및 날짜별 계획 JSON)
*   `tools/`: AI 파서 및 관리용 유틸리티 (`plan_parser.py`: 이미지 → JSON, `plan_manager.py`: 조회·수정·검증·배포)
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

관리봇 `/manage`에는 오늘 말씀 재전송과 이번 주 월~토 기도제목 재호출 버튼이 있습니다. 기도제목 수동 재호출은 기존 발송 marker를 지우지 않으므로 정기 자동발송의 중복 방지 상태에 영향을 주지 않습니다.

---
*마지막 업데이트: 2026년 7월 6일 (bot_common 헬퍼 모듈 도입 + Gemini 기본값 정의)*
