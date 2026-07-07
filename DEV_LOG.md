# 📚 Bible_notice_telegram_bot Development Log
> *Auto-generated from system_core.db at 2026-03-17 23:45:08*

## [2026-07-06] manager_bot.py bot_common 마이그레이션
- **배경**: 워크스페이스 전역 `bot_common` 헬퍼 모듈(Vocab Bot, Bible Bot, Attendance Bot 통합) 도입.
- **완료 사항**:
  - `manager_bot.py`에서 직접 `Application.builder()` / `load_dotenv()` 제거
  - `from bot_common import load_secrets, require_env, run_bot` 도입
  - Telegram 부트스트랩을 `run_bot(TOKEN, handlers)` 한 줄로 단순화
  - `tools/gemini_parser.py` (269줄) 삭제 — `tools/plan_parser.py`로 완전 대체됨
- **상태**: 실제 발송은 계속 `mh_bot` systemd timer(`bible-daily-send.timer`)가 담당. manager_bot.py는 원격 제어용 웹 UI 역할.

## [2026-07-01] Gemini → OpenAI 리팩터링 + Provider 추상화 (CONTEXT DEAD_END)
- **배경**: 기존 사용 모델(`gemini-2.0-flash`)이 서비스 종료되어 파서가 동작하지 않음. 정확도·유지보수성 우선으로 OpenAI 기반 재작성 요청.
- **완료 사항**:
  - `ai/` 패키지 신설 (`interfaces.py`, `openai_provider.py`, `gemini_provider.py`, `provider.py`) — `ImageAnalysisProvider` 인터페이스로 벤더 추상화. `AI_PROVIDER` 환경변수로 전환(`openai` | `gemini`).
  - `tools/gemini_parser.py` → `tools/plan_parser.py`로 개명, Gemini SDK 직접 의존 제거. Structured Output은 `{"days":[{day, nt, ot, psalms, proverbs, qt}, ...]}` 스키마 사용 후 기존 `{"1": [...], ...}` 형태로 변환(OpenAI strict schema가 동적 dict 키 미지원이라 배열로 우회).
  - `tools/issue_to_plan.py`(GitHub Actions 이슈 파서)도 `ai.provider.get_provider()`로 전환, 프롬프트/스키마/후처리 로직은 `plan_parser.py`에서 공유.
  - `main.py`의 `datetime.utcnow()` → `datetime.now(ZoneInfo("Asia/Seoul"))`로 교체.
  - `requirements.txt` 정리: `openai`, `google-genai`(Gemini fallback용) 유지, 누락되어 있던 `google-api-python-client`/`google-auth`(Drive fallback에 실사용 중이었음) 추가.
- **비용 이슈로 인한 결정**: OpenAI API 키(`OPENAI_API_KEY`)에 결제수단 미등록 상태 → `insufficient_quota` 확인. OpenAI는 무료 티어가 없음. **`AI_PROVIDER` 기본값을 `gemini`로 설정**하여 Gemini 무료 티어(`gemini-2.5-flash`)로 우선 동작하도록 함. 추후 OpenAI 결제 등록 시 `.env`에 `AI_PROVIDER=openai`만 추가하면 전환됨(코드 변경 불필요).
- **검증**: `tools/plan_parser._extract_plan_from_images(2026, 7)` 및 `python main.py parse 2026 7` 실제 API 호출로 성공 확인(Gemini 경유). `data/plans/2026_07.json` 재생성됨.
- **발송(send) 테스트는 이 세션에서 수행하지 않음**: 매일 자동 발송은 **`mh_bot` systemd timer**(`bible-daily-send.timer`)가 전담 — 본 세션(샌드박스)은 `api.telegram.org` 아웃바운드가 막혀 있어 `python main.py`(전체 run) 실행 시 전송이 아닌 `httpx.ConnectError`만 확인됨. 실제 발송 여부는 `mh_bot` 쪽에서 확인할 것.
- **버그 수정**: `core/bible_sender.py`의 `broadcast_messages()`가 KO/EN/MN 3개 전송이 전부 실패해도 무조건 `return True`를 반환하여 개인 요약본 발송 단계로 잘못 진입하던 문제 확인 및 수정. `any_success` 플래그로 실제 전송 성공 여부를 추적하도록 변경(`return any_success`).
- **후속 논의**: Google Drive 이미지 폴더 주소 확인 및 텔레그램 봇을 통한 이미지 업로드 기능 검토(아래 항목 참고).

## [2026-03-17]
- GitHub Actions 중복 발송 버그 수정 및 플랜 파서 로직 검증
  
  ## 2026-03-02: 대규모 아키텍처 개편 및 로직 고도화 완료
  
  ### ✅ [NEW] 최종 완료 사항
- **통합 관리 명령어 완성**: `main.py`를 통해 `run`(스마트 실행), `parse`(AI 생성), `send`(전체 발송), `summary`(개인톡 요약), `check`(ID 확인) 명령어 체계 구축.
- **2개 이미지 동시 파싱**: 성경 읽기표와 QT 본문표 이미지를 각각 분석하여 데이터를 병합하는 고정밀 추출 로직(`IMAGE 1 & 2 CRITICAL`) 완성.
- **지능형 데이터 보정**: 신약/구약의 생략된 권수 상속 로직 및 QT 본문의 자동 약어화(풀네임 -> 약어) 기능 탑재.
- **개인 최적화 요약본**: 줄바꿈 문자(`\n`) 버그를 수정하고, 개인 대화방으로 3개 국어 요약본만 보낼 수 있는 기능 추가.
  
  ### 🏗️ 구조 및 시스템 최적화
- **디렉토리 체계화**: `core/`(핵심 로직), `data/`(DB 및 JSON), `tools/`(유틸리티)로 분리하여 코드 가독성 및 유지보수성 향상.
- **보안 중앙화**: 루트 폴더의 `/.secrets/.env`를 최우선 참조하도록 하여 보안 사고 예방 및 설정 단일화.
- **GitHub Actions 연동**: `requirements.txt` 복구 및 워크플로우 "스마트 모드" 적용으로 24/7 무중단 운영 보장.
  
  ---
  
  ## 2026-02-04
- Initialized documentation: README.md, GEMINI.md, DEV_LOG.md.
- Scanned project structure.
