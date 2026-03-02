# Development Log - Bible Notice Telegram Bot

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
