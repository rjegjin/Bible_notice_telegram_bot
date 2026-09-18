# DEAD_ENDS — Bible_notice_telegram_bot

실패한 접근법과 피해야 할 패턴을 기록한다.
새로운 실패가 확인되면 즉시 추가할 것.

---

## 2026-09-12 — `plan_manager.py`만 배포해 caption 처리가 import에서 실패

- 증상: `/qt`·`/br` caption 처리 시 `ModuleNotFoundError: tools.quiet_time_docs`가 발생했다.
- 결론: `plan_manager.py`의 새 top-level dependency인 `tools/quiet_time_docs.py`와 runtime dependency `holidays`를 운영 배포에서 누락했다.
- 다음에는 이렇게: 연결 파일 배포 전 import graph를 확인하고, 정확한 상대 경로로 동기화한 뒤 운영 venv의 requirements와 `main.py plan --help`를 smoke test한다.

## 2026-09-12 — 운영 venv의 `pip` wrapper 직접 실행

- 증상: `/home/mh_bot/projects/unified_venv/bin/pip install`은 로컬 `/home/rjegj/projects/unified_venv`에 이미 설치됐다고 출력했지만 운영 Python은 `holidays`를 import하지 못했다.
- 결론: 복사된 `pip` script의 shebang이 원래 로컬 Python 절대경로를 유지하고 있다.
- 다음에는 이렇게: 운영 package 설치는 `/home/mh_bot/projects/unified_venv/bin/python -m pip`로 실행하고 그 Python으로 즉시 import readback한다.

## 2026-09-11 — 운영 서버 SSH 이름 `mh_bot` 사용

- 증상: `ssh mh_bot`이 `Could not resolve hostname mh_bot`으로 실패했다.
- 결론: 문서의 서버 표시명과 현재 SSH config의 실제 host alias가 같지 않다.
- 다음에는 이렇게: `ssh -G mhbot`으로 현재 alias를 확인한 뒤 `mhbot`을 사용한다.

## 2026-09-07 — Quiet Time Docs 스타일 batch의 REST 필드명

- 증상: 9월 탭 스타일 batch가 400으로 원자적 거부됨.
- 결론: 공개 API는 `documentSize`가 아닌 `pageSize`, `columnProperties`가 아닌 `tableColumnProperties`, 셀 수직 정렬은 `CENTER`가 아닌 `MIDDLE`을 사용한다.
- 다음에는 이렇게: discovery schema 또는 오류의 `fieldViolations`를 확인하고, 스타일 batch를 다시 실행하기 전에 해당 필드명을 검증한다.

## 2026-09-07 — 실측 pt를 mm로 재변환

- 증상: 9월 표의 행이 약 2.8배 높아져 각 페이지가 4행씩 분리됐다.
- 결론: 문서 snapshot의 row height와 title spacing은 이미 PT 단위인데 `_pt()`에 다시 넣었다.
- 다음에는 이렇게: 템플릿에서 읽은 PT 값은 그대로 요청하고, mm 단위 설계값에만 변환 함수를 사용한다.

## 2026-09-07 — Quiet Time service account Docs 접근

- 증상: Docs scope를 요청해도 Docs API GET은 403 SERVICE_DISABLED, Drive GET은 404.
- 결론: scope만 추가해서 해결되지 않는다. Cloud project의 Docs API 활성화와 대상 Doc 공유가 선행되어야 한다.
- 다음에는 이렇게: API 활성화/편집자 공유 후 `plan sheet 2026 9`로 검증한다. connector 접근 성공을 unattended service account 권한으로 간주하지 않는다.
- 참고: connector의 저장 응답은 정규화된 `tabs[].body` 구조이므로 공개 API의 `tabs[].documentTab.body`와 구분한다.

## 2026-09-06 — Google Docs `updateTableRowStyle`에 `tableRange` 사용

- 증상: 9월 Quiet Time 문서의 2쪽 행 높이 조정 batch가 `Unknown name "tableRange"` 400 오류로 전체 거부됐다.
- 결론: `updateTableRowStyle`은 `tableRange`가 아니라 `tableStartLocation`과 `rowIndices`를 받는다. batch는 원자적으로 거부되어 문서 변경은 없었다.
- 다음에는 이렇게: 표 행 높이는 현재 표 시작 index를 다시 확인한 뒤 `tableStartLocation` + 0-based `rowIndices`로 지정한다.

## 2026-09-06 — Google Docs 탭 목록을 부분 read 결과만으로 단정

- 증상: 복사본의 `8월` 탭을 `9월`로 바꾸려다 이미 존재하는 `9월` 탭 때문에 `Tab title must be unique`로 batch 전체가 거부됐다.
- 결론: 첫 구조 read의 큰 응답이 잘려 보이는 상태에서 단일 탭이라고 단정했다. 실제 문서에는 `8월`, `9월` 두 탭이 있었다.
- 다음에는 이렇게: 내용 read와 별도로 `tabs(tabProperties)`만 먼저 요청해 전체 탭 수·제목·ID를 확정한 뒤 대상 탭을 고른다.

## 2026-09-06 — OAT 발송을 해당 주의 이미지 plan 존재 여부에 결합

- 증상: 승인된 학기 OAT가 있어도 9월 주간 이미지 plan이 없으면 OAT 미리보기가 0명으로 끝났다.
- 결론: 고정된 월 3명·화~토 2명 OAT 일정은 주간 이미지 파일 존재 여부와 독립적으로 계산해야 한다.
- 다음에는 이렇게: 같은 daily timer에서 연이어 실행하되, OAT 대상은 승인된 학기 JSON의 대표 순서와 요일별 인원수로 결정한다.

(아직 기록된 실패 접근법 없음 — 프로젝트 현대화 시점: 2026-07-05)

## 2026-09-03 — LibreOffice로 OAT HWP/HWPX 일괄 텍스트 변환

- 증상: DOCX 1개만 변환되고 HWP/HWPX 8개는 `source file could not be loaded`로 실패했다.
- 결론: 이 환경의 LibreOffice import filter는 해당 HWP/HWPX 원본을 읽지 못한다.
- 다음에는 이렇게: HWP 5는 pyhwp parser, HWPX는 ZIP/XML 직접 추출을 사용하고 원본은 보존한다.

## 2026-07-31 — owner용 `EN_CHAT_ID` 제거를 영어 그룹 제거로 확장

- 증상: MH 개인방 전문 오발송을 막으면서 별도 영어 그룹용 설정과 라우팅을 마련하지 않아 7월 16일부터 영어 전문 발송이 사라졌다.
- 결론: owner 개인방과 EN 그룹은 서로 다른 역할·환경변수여야 한다.
- 다음에는 이렇게: owner는 `BIBLE_OWNER_CHAT_ID`/legacy `EN_CHAT_ID`, 영어 그룹은 `EN_GROUP_CHAT_ID`로 분리하고 그룹 ID 미설정 시 KO/MN은 계속 발송한다.

## 2026-07-31 — Telegram 파일럿에서 HTTP client INFO 로그 허용

- 증상: EN방 파일럿은 성공했지만 `httpx` INFO 로그가 bot token이 포함된 요청 URL을 출력했다.
- 결론: 실제 발송 전에 공용 Telegram helper에서 HTTP 요청 URL 로그를 차단해야 한다.
- 다음에는 이렇게: `bot_common` import 시 `httpx` logger를 WARNING으로 고정하고, 노출된 token은 BotFather에서 교체한 뒤 검증한다.

## 2026-07-31 — workspace root에서 Bible bot unittest discovery 실행

- 증상: `projects/`에서 `unittest discover -s Bible_notice_telegram_bot/tests`를 실행해 `core`와 `tools` import가 모두 실패했다.
- 추가 증상: 원격 홈 디렉터리에서 `common.bot_common` guard를 확인해 `common` import도 실패했다.
- 결론: 테스트는 모듈 import 기준점인 `Bible_notice_telegram_bot/`에서 실행해야 한다.
- 다음에는 이렇게: 공용 모듈은 workspace root, sub-project 테스트는 해당 project root에서 실행하고, `set -e`가 후속 배포를 중단했는지 확인한다.

## 2026-07-13 — 파일명만 보고 7월 HWPX를 JPG의 원본으로 간주

- 증상: `/home/rjegj/Documents/QT_BR_passage_old/`의 2026년 7월 BR/QT HWPX를 구조 파싱했으나, 현재 봇 asset JPG와 본문이 전혀 달랐다. 예를 들어 JPG의 7월 1일 BR은 `마 1-5`인데 HWPX는 `창 2-3`이었고 날짜도 일부 누락됐다.
- 결론: 이 HWPX들은 현재 운영 중인 7월 JPG의 신뢰 가능한 원본이 아니므로 자동 복구 소스로 사용할 수 없다.
- 다음에는 이렇게: 월/파일명이 일치해도 대표 날짜의 BR·QT 값을 JPG와 대조한 뒤에만 HWPX를 우선 소스로 채택한다. 불일치하면 이미지 분석 결과에 완전성·연속성 검증을 적용한다.

## 2026-07-14 — 로컬 호스트에서 Telegram API 파일럿 발송 시도

- 증상: 로컬에서 `api.telegram.org`로 직접 연결하면 connection refused가 발생했다.
- 결론: Bible bot의 실제 Telegram 송수신 경로는 네트워크가 열려 있는 운영 호스트 `mh_bot`에서 검증해야 한다.
- 다음에는 이렇게: token/chat 매핑 확인과 파일럿 발송은 `mh_bot`에서 수행하고, 로컬에서는 수신처 결정 로직과 payload만 테스트한다.

## 2026-07-14 — 발송 loop 중첩 제거 후 들여쓰기 잔존

- 증상: 기존 `chat -> languages` 이중 loop를 `room` 단일 loop로 바꾸면서 내부 발송 블록의 들여쓰기가 한 단계 남아 `IndentationError`가 발생했다.
- 결론: loop 구조 변경은 header만 바꾸지 말고 loop body 전체의 indentation을 함께 검토해야 한다.
- 다음에는 이렇게: 구조 변경 직후 해당 함수 구간을 읽고 `py_compile`을 통과한 뒤 테스트·배포한다.

## 2026-07-15 — `EN_CHAT_ID`를 영어 그룹으로 간주해 개인방에 전문 발송

- 증상: 06:00 timer의 최신 코드가 `send --target all`을 실행해 KO·EN·MN 모두에 QT·시편·잠언 전문을 보냈다. 실제 `EN_CHAT_ID`는 영어 그룹이 아니라 소유자 개인방 MH였다.
- 결론: 코드 버전 문제가 아니라 수신처 의미 모델링 오류였다. 개인방을 언어 그룹과 같은 broadcast room으로 취급하면 안 된다.
- 다음에는 이렇게: `all`은 KO/MN 그룹 전문 + owner 개인방 요약으로 정의하고, owner에는 `send_only_summaries()`만 호출한다. 실제 Telegram `getChat`의 type/title을 확인한 뒤 room 역할을 정한다.

## 2026-07-29 — argparse `REMAINDER`만으로 중첩 CLI help 전달

- 증상: `main.py plan` 뒤의 일반 명령은 전달됐지만 `main.py plan --help`는 상위 argparse가 unknown option으로 거부했다.
- 결론: help option은 `argparse.REMAINDER` positional보다 먼저 option parsing 대상이 되므로 자동 전달되지 않는다.
- 다음에는 이렇게: 상위 `plan` subparser가 `-h/--help`를 명시적으로 받고 하위 plan manager parser의 help 호출로 변환한다.

## 2026-07-29 — `deploy`를 asset 갱신 반영으로 간주

- 증상: 새 BR asset이 7월 29일에 수정됐지만 기존 `plan deploy`는 현재 JSON만 원격에 복사하므로 7월 13일 JSON 내용이 그대로 유지됐다.
- 결론: asset 변경 반영은 단순 deploy가 아니라 `asset parse → JSON 교체 → validation → deploy → Telegram test`의 전체 publish transaction이어야 한다.
- 다음에는 이렇게: asset 수정 후에는 `python main.py plan publish YEAR MONTH`를 사용한다. `deploy`는 이미 생성·검토된 JSON만 재배포할 때에만 사용한다.

## 2026-07-29 — import 순서를 확인하지 않고 patch context 작성

- 증상: `plan_parser.py`에 HWPX toggle을 추가하는 첫 patch가 실제 import 순서와 맞지 않아 적용되지 않았다.
- 결론: 기능 구간을 읽었더라도 patch 대상의 인접 줄은 실제 파일 그대로 사용해야 한다.
- 다음에는 이렇게: patch 직전에 변경할 시작·끝 구간을 짧게 다시 읽고, 확인된 인접 줄을 context로 사용한다.

## 2026-07-29 — 여러 파일 patch에 확인하지 않은 루트 문서 context 포함

- 증상: 코드와 여러 문서를 한 patch로 갱신하면서 루트 `RESOLVED.md`의 실제 첫 완료 항목을 확인하지 않아 전체 patch가 취소됐다.
- 결론: 여러 파일을 묶은 patch는 한 파일의 context 불일치로 전부 적용되지 않을 수 있다.
- 다음에는 이렇게: 프로젝트 파일과 workspace 루트 기록을 분리하고 각 파일의 실제 삽입 지점을 먼저 확인한다.

## 2026-07-29 — 여러 경로의 파일을 remote project root로 rsync

- 증상: `main.py tools/plan_parser.py tools/plan_manager.py`를 remote project root 하나로 전송해 tools 파일 두 개가 루트에 평탄화됐고, 실제 `tools/` 모듈은 이전 버전으로 남았다.
- 결론: 여러 source를 directory destination으로 보내면 원래 상대 경로가 자동 보존되지 않는다.
- 다음에는 이렇게: root 파일과 `tools/` 파일을 destination별로 나눠 전송하거나 검증된 `--relative` 방식을 사용하고, 즉시 checksum과 import smoke check를 실행한다.

## 2026-09-18 — 실제 CLI help 확인 없이 운영 smoke check

- 증상: 운영 동기화 확인 중 존재하지 않는 `plan status`를 호출했고, 이어 `prayer preview`에 지원하지 않는 주차 인자를 넘겨 argparse가 종료했다.
- 결론: 월별 상태 확인은 `plan validate YEAR MONTH`로 하며, 기도제목 preview는 인자 없이 최신 주차를 읽는다.
- 다음에는 이렇게: 각 중첩 CLI의 `--help`를 먼저 확인하고 실제로 표시된 인자만 사용한다.

## 2026-09-18 — RESOLVED 문서 제목을 확인하지 않고 patch

- 증상: `RESOLVED.md` 제목을 추측한 patch가 실제 underscore 표기와 달라 적용되지 않았다.
- 결론: 같은 프로젝트 기록 파일도 제목 표기가 서로 다를 수 있다.
- 다음에는 이렇게: 기록 파일의 첫 구간을 읽은 뒤 확인된 구분선이나 날짜 헤더를 patch 기준으로 사용한다.
