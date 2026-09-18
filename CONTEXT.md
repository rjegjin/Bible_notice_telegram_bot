# CONTEXT — Bible Notice Telegram Bot

## 2026-09-18 — OCR 승인 경계·운영 검증 완료

- [완료] Telegram BR/QT 앨범은 검증된 standby JSON을 만들고 `plan publish`는 그 동일 JSON을 재OCR 없이 승격한다.
- [완료] 주간기도 원본을 주차별 보존하고 전체 OCR 미리보기·`/prayerpreview`·`future_only` 승인을 제공한다.
- [완료] 9월 Google Docs 탭 API readback과 PDF 실측을 완료했다. 전체 export의 탭 표지 뒤 9월 본문은 정확히 2쪽이며 표 잘림이 없다.
- [운영] manager bot과 daily timer 정상, EN 그룹 설정 완료, 2026-09-13 주간기도 JSON 승인·수목 발송 marker 확인.
- [정책] 개인 기도 JSON·원본·marker는 `data/prayers/` 운영 데이터로 Git에서 제외한다.

## 2026-09-07 — Quiet Time Docs 자동화 구현

- [구현] `plan publish`의 검증 후 Docs 월 탭 갱신/readback을 연결. `plan sheet YEAR MONTH`, `--no-sheet` 제공.
- [보존] 같은 월의 사용자 적용 칸을 보존하고 revision 충돌/Docs 실패 시 배포를 중단한다.
- [해결] Docs API 활성화·편집자 공유 후 탭 readback과 PDF 2쪽 시각 검증 완료.

## 2026-09-06 — 2026년 2학기 OAT 정기 발송

- [완료] 승인된 `2026_H2_oat.json`을 2026-09-07부터 기존 06:00 KST daily timer에 연결했다.
- [운영] 월요일 3명·화~토요일 2명에게 매주 다음 OAT 항목 1개를 기존 주간기도와 별도 메시지로 보낸다.
- [예외] 심창민은 수요일 정석훈 직후 별도 메시지로 보내며, 사람·날짜·항목별 marker로 중복 발송을 막는다.
- [검증] 전체 36 tests, 월요일·수요일 dry-run, 운영 timer ExecStart와 다음 실행 시각을 확인했다.

## 2026-08-31 — 주간기도제목 이미지 OCR·13명 일일 발송

- [완료] owner 개인방에서 caption `/prayer`로 이미지를 받아 왼쪽 6명·오른쪽 7명을 분리 OCR하고, 월 3명·화~토 2명씩 주간 plan으로 저장한다.
- [안전] OCR 결과는 `/prayerapprove` 전까지 미승인 상태이며, 사람별 marker로 일일 재실행 중복 발송을 막는다.
- [운영] 기존 `bible-daily-send.timer`의 매일 06:00 KST `main.py send`를 재사용하며 `PRAYER_CHAT_ID`, 없으면 MydailyBibleBot owner 개인방으로 한 사람당 한 메시지를 보낸다.
- [검증] 전체 33 tests, 실제 2026-08-23 이미지 13명 OCR·수동 교정, 로컬/원격 preview·checksum, manager active/running, daily timer active/waiting 확인.

## 2026-07-31 — 별도 영어 그룹 라우팅 복구

- [원인] `EN_CHAT_ID`와 `ENGLISH_CHAT_ID`가 모두 MH 개인방을 가리켰고 별도 영어 그룹 ID는 저장돼 있지 않았다. 7월 15일 개인방 전문 차단 시 EN 그룹 경로도 함께 제거됐다.
- [완료] 별도 `EN_GROUP_CHAT_ID`를 선택적으로 사용하는 EN 전문 경로·버튼과 `/chatid` 확인 명령을 복구했다.
- [안전] `EN_GROUP_CHAT_ID`가 없으면 KO/MN 자동발송은 그대로 유지된다.
- [해결] 운영 `EN_GROUP_CHAT_ID` 설정 확인 완료.

## 2026-07-29 — HWPX 기본 OFF와 월 이미지 import

- [완료] HWPX parsing을 기본 OFF로 전환하고 `main.py parse --enable-hwpx/--disable-hwpx/--hwpx-status` persistent toggle을 추가했다.
- [완료] `plan import-images`와 대화형 메뉴에서 임의 이름 BR/QT 이미지를 검사한 뒤 표준 asset 이름으로 가져올 수 있다.
- [확인] 8월 BR/QT asset과 로컬 `2026_08.json`은 이미 있으며 JSON validation을 통과했다.
- [주의] 운영 timer는 `main.py send`만 실행하므로 asset 배치·JSON 생성·mh_bot 배포는 자동이 아니다. 월말에 `plan publish`를 명시적으로 실행한다.
- [운영] 8월 JSON은 아직 mh_bot에 배포하지 않았다.

## 2026-07-29 — 오늘 수정 BR asset 기반 7월 JSON publish

- [완료] 12:04 KST에 수정된 `assets/2026년_07월_BR_passage.jpg`를 Gemini로 다시 parsing했다.
- [완료] 신약 진도를 `마21-24`, `마25-28`, `막1-4`, `눅17-20`, `행25-28`, `롬16-고전4` 등 새 이미지 기준으로 교체했다.
- [완료] 새 양식에 잠언 열이 없으면 deterministic하게 날짜 번호를 잠언 장으로 채우는 기존 계약을 유지했다.
- [완료] `plan publish` transaction을 추가해 backup → asset parse → validation → JSON 교체 → mh_bot deploy → owner Telegram test를 한 번에 실행한다.
- [검증] 새 JSON checksum `1a8d7b4b...ff6d6`, 로컬/원격 일치, remote validation, owner publish test 1건, 전체 24 tests 통과.
- [backup] `data/plans/backups/2026_07_20260729_155154_773844.json`에 이전 7월본 보존.

## 2026-07-29 — 월별 말씀 plan CLI/TUI 추가

- [완료] `python main.py plan` 대화형 관리 메뉴와 list/show/edit/validate/preview/reparse/deploy subcommand를 추가했다.
- [완료] 수정은 월 전체 validation → timestamp backup → atomic replace 순서로만 저장된다.
- [완료] 비대화식 edit는 `--yes` 없이는 diff만 표시하며, preview는 Telegram을 호출하지 않는다.
- [완료] deploy는 로컬 검증 후 rsync하고 운영 서버에서 같은 validator를 다시 실행한다.
- [검증] 전체 19개 unittest, 7월 29일 조회·KO preview·월 검증, 실제 mh_bot deploy/remote validation 통과.
- [주의] backup은 `data/plans/backups/`에 생성되며 git에서 제외된다.

## 2026-07-15 — owner 개인방 전문 오발송 수정

- [원인] 최신 코드가 실행됐지만 `EN_CHAT_ID`를 영어 그룹으로 모델링했다. 실제로는 owner 개인방 MH라서 timer의 `send --target all`이 개인방에도 전문을 보냈다.
- [완료] `all`을 `KO/MN 그룹 전문 + owner 개인방 3개 국어 요약`으로 재정의했다.
- [완료] `ko/mn`은 해당 그룹 전문, `owner`는 개인 요약만 보내며 EN 전문 발송 경로를 제거했다.
- [완료] 관리봇 버튼을 `KO방 전문`, `MN방 전문`, `내 방 요약`, `그룹 전문 + 내 방 요약`으로 변경했다.
- [검증] owner가 full-passage recipient에서 제외되는 회귀 테스트 및 daily orchestration 테스트 포함 전체 15개 통과.

## 2026-07-14 — 방별 발송 버튼 추가

- [완료] 관리봇에 `KO방`, `EN방`, `MN방`, `등록된 전체 방` 발송 버튼을 각각 추가했다.
- [완료] CLI에 `main.py send --target all|ko|en|mn`을 추가하고 수신처 선택을 `core/recipient_config.py`로 일원화했다.
- [검증] target별 단일 방 선택 및 all의 3개 방 선택 테스트 포함 전체 13개 테스트 통과.
- [운영] manager service 재시작 후 active/running, 버튼 callback 매핑 확인. 실제 그룹 메시지는 발송하지 않았다.

## 2026-07-14 — MydailyBibleBot 개인방 수신처 명확화

- [완료] 개인 요약 수신처의 숫자 하드코딩과 `ATTENDANCE_TELEGRAM_CHAT_ID` 의존을 제거했다.
- [완료] 수신처 우선순위는 `현재 대화방(--chat-id)` → `BIBLE_OWNER_CHAT_ID` → `EN_CHAT_ID` 호환 fallback으로 명시했다.
- [완료] 관리봇 요약/스마트 실행은 버튼을 누른 현재 대화방 ID를 자식 프로세스에 전달한다.
- [완료] 메뉴를 `등록된 전체 방에 발송`, `이 대화방에 요약 발송`, `전체 발송 + 이 대화방 요약`으로 구분했다.
- [검증] 운영 개인방 MH에 3개 국어 요약 파일럿 3건 전송 성공, manager service active/running.

## 2026-07-13 — 7월 passage OCR 복구

- [완료] BR/QT 이미지를 Gemini 한 요청에 함께 보내던 방식을 이미지별 2회 요청으로 분리했다.
- [완료] 월 날짜 완전성, BR 필수 열, QT/시편 장·절의 성경 DB 범위를 저장 전에 검증하고 실패 시 기존 plan을 보존한다.
- [완료] `data/plans/2026_07.json`의 잘못된 QT 27건과 시편 119 절 범위 5건을 현재 JPG 기준으로 교정했다.
- [완료] 시편의 `장:절-절` 범위를 실제 본문으로 발송하도록 sender를 보강했다.
- [주의] `/home/rjegj/Documents/QT_BR_passage_old/`의 7월 HWPX는 현재 JPG와 내용이 달라 복구 소스로 사용하면 안 된다.

## 2026-07-05 — 컨텍스트 현대화

- [현재] 운영 중 — 매일 성경 읽기 + QT 자동 발송
- [주의] mh_bot의 bible-daily-send.timer + bible-daily-send.service로 자동화
- [주의] GitHub Actions daily_bible.yml은 workflow_dispatch 전용 (자동 schedule 아님)
- 운영: mh_bot@100.103.20.9, systemd user timer
- 최근 git: 2026-06-30 (경로 이식성 확보 + plan 신형식 통일)
