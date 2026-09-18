# RESOLVED — Bible_notice_telegram_bot

완료된 태스크, 해결된 문제, 채택된 제안을 기록한다.
진행 중인 것은 CONTEXT.md, 실패한 접근법은 DEAD_ENDS.md에 쓴다.

---

## 2026-09-18 — OAT 기도 Telegram 요일별 재호출

- 내용: `/oatday` 명령과 `/manage` OAT 월~토 버튼, OAT `--force --chat-id` 발송을 추가했다.
- 결과: owner 개인방에서 이번 주 특정 요일 OAT 기도를 다시 받을 수 있고 자동발송 marker는 보존된다.
- 파일: `manager_bot.py`, `tools/prayer_manager.py`, `tests/test_prayer_manager.py`

## 2026-09-18 — 날짜별 말씀·요일별 기도 Telegram 재호출

- 내용: `/send` 날짜 인자와 `/prayerday` 요일 명령, `/manage` 오늘 말씀·월~토 기도 버튼을 추가했다.
- 결과: 지정 날짜 말씀과 이번 주 특정 요일 기도제목을 Telegram에서 다시 보낼 수 있고, 기도 자동발송 marker는 보존된다.
- 파일: `main.py`, `manager_bot.py`, `tools/prayer_manager.py`, `tests/test_manager_bot.py`, `tests/test_prayer_manager.py`

## 2026-09-18 — Telegram OCR부터 승인·Docs·발송까지 안전 경계 완성

- 내용: BR/QT 앨범 standby 승격, 다국어 책 전환, 주간기도 원본·전체 미리보기, future-only 승인, Docs PDF 검증을 완료했다.
- 결과: 검토한 JSON과 배포 JSON이 동일하며 OCR 오류·늦은 승인·개인 데이터 Git 유입을 fail-closed로 처리한다.
- 파일: `manager_bot.py`, `tools/plan_manager.py`, `tools/plan_parser.py`, `tools/prayer_manager.py`, `core/bible_scripture_resolver.py`, tests, `.gitignore`

## 2026-08-31 — 주간기도제목 13명 OCR·요일별 개별 발송

- 내용: 두 칼럼 이미지에서 개인 구역 13명을 추출해 월요일 3명, 화~토요일 2명씩 배정하고 한 사람당 한 Telegram 메시지로 보내는 관리 명령과 owner 업로드 경로를 추가했다.
- 결과: 기존 매일 06:00 KST timer를 그대로 재사용하며 MydailyBibleBot owner 개인방으로 보낸다. OCR 승인 전 발송 차단과 사람별 중복 방지 marker를 적용한다. 제공 이미지의 2026-08-23 plan은 원문 대조 후 교정했으며 미승인 상태로 배포했다.
- 파일: `tools/prayer_manager.py`, `main.py`, `manager_bot.py`, `tests/test_prayer_manager.py`, `data/prayers/2026-08-23.json`, `README.md`, `.gitignore`

## 2026-07-29 — HWPX source toggle과 이미지 import 간소화

- 내용: HWPX parsing을 기본 비활성화하고 persistent CLI/TUI toggle을 추가했다. 임의 파일명의 BR/QT 이미지를 검증해 표준 asset 이름으로 가져오는 `plan import-images`도 추가했다.
- 결과: 잘못된 HWPX가 이미지보다 우선되는 것을 막고, 사용자가 파일명을 직접 바꾸지 않아도 된다. 기존 asset 교체는 `--replace`를 요구하며 import와 운영 publish는 분리된다.
- 검증: parser settings 및 image import tests, 8월 로컬 plan validation.
- 파일: `config/plan_parser.ini`, `main.py`, `tools/plan_parser.py`, `tools/plan_manager.py`, 관련 tests, `README.md`

## 2026-07-29 — 수정 BR asset에서 7월 plan 재생성·배포·Telegram test

- 내용: 오늘 수정된 7월 BR JPG와 기존 QT JPG를 분리 parsing해 월 JSON을 새 버전으로 교체하고, publish workflow로 mh_bot에 배포한 뒤 owner 개인방에 검증 메시지를 보냈다.
- 결과: 7월 신약/구약 진도가 새 이미지와 일치하며 로컬·원격 JSON checksum이 같다. 기존 7월본은 timestamp backup으로 복구 가능하다.
- 검증: 전체 24 tests, 로컬/원격 monthly validation, 핵심 날짜 조회, owner Telegram publish test 성공.
- 파일: `assets/2026년_07월_BR_passage.jpg`, `data/plans/2026_07.json`, `tools/plan_parser.py`, `tools/plan_manager.py`, `core/bible_sender.py`, 관련 tests

## 2026-07-29 — 월별 말씀 JSON 안전 관리 CLI/TUI

- 내용: `main.py plan` 아래에 월 목록·조회·날짜별 수정·검증·OCR 재생성·발송 없는 preview·운영 deploy 기능을 추가했다.
- 결과: 사용자가 Python 코드를 열거나 JSON을 직접 편집하지 않아도 되며, 잘못된 장절은 저장 전에 차단되고 기존 파일은 timestamp backup으로 보존된다.
- 검증: 전체 19 tests, 7월 plan smoke test, 실제 mh_bot sync 및 remote validation 통과.
- 파일: `main.py`, `tools/plan_manager.py`, `tests/test_plan_manager.py`, `.gitignore`, `README.md`

## 2026-07-15 — owner 개인방에는 요약만 발송하도록 역할 분리

- 내용: `EN_CHAT_ID`가 실제 영어 그룹이 아닌 owner 개인방임을 확인하고 broadcast room에서 제외했다. daily/all 발송을 KO/MN 전문 + owner 요약으로 분리했다.
- 결과: 개인방에는 QT·시편·잠언 전문이 전송되지 않고 3개 국어 요약만 전송된다. timer 명령은 그대로여도 새 `all` 의미를 사용한다.
- 파일: `main.py`, `manager_bot.py`, `core/bible_sender.py`, `core/recipient_config.py`, `tests/test_delivery.py`, `tests/test_recipient_config.py`

## 2026-07-14 — KO/EN/MN 방별 발송 버튼 추가

- 내용: 관리봇의 인라인·하단 메뉴에 각 방 발송 버튼을 추가하고 CLI target을 해당 방 설정에 연결했다.
- 결과: 전체 발송 없이 KO, EN, MN 중 원하는 방 하나만 선택해서 보낼 수 있다. 기존 timer의 기본 전체 발송은 유지된다.
- 파일: `manager_bot.py`, `main.py`, `core/bible_sender.py`, `core/recipient_config.py`, `tests/test_recipient_config.py`

## 2026-07-14 — MydailyBibleBot 개인방 발송 대상 불명확 문제 해결

- 내용: 개인 ID 하드코딩과 출결 봇 설정 fallback을 제거하고, 관리봇의 현재 대화방을 명시적 CLI 인자로 전달하도록 변경했다.
- 결과: 그룹 전체 발송과 현재 개인방 요약 발송이 메뉴와 로그에서 구분된다. 운영 개인방 파일럿 3건이 성공했다.
- 파일: `main.py`, `manager_bot.py`, `core/recipient_config.py`, `tests/test_recipient_config.py`, `README.md`

## 2026-07-13 — 7월 passage OCR 오인식 및 무검증 저장 해결

- 내용: Gemini 요청을 BR/QT 이미지별로 분리하고 월간 plan 완전성·성경 DB 범위 검증을 추가했다. 7월 QT와 시편 119 절 범위를 JPG 기준으로 교정했다.
- 결과: 실제 Gemini split extraction이 31일 전체 검증을 통과하며, 이후 잘못된 결과는 기존 JSON을 덮어쓰지 않는다. 시편 절 범위 본문도 정상 조회한다.
- 파일: `tools/plan_parser.py`, `tests/test_plan_parser.py`, `core/bible_sender.py`, `data/plans/2026_07.json`, `CONTEXT.md`, `DEAD_ENDS.md`
