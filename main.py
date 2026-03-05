import os
import sys
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# [보안 & 편의] 중앙 .env 로드 로직 (root/.secrets/.env 우선)
def load_env_centralized():
    central_secrets = Path("/home/rjegj/projects/.secrets/.env")
    if central_secrets.exists():
        load_dotenv(central_secrets)
        return True
    local_env = os.path.join(BASE_DIR, '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)
        return True
    return False

# 실행 전 환경 변수 로드
load_env_centralized()

# 신규 구조에 맞춘 임포트
try:
    from tools.gemini_parser import generate_monthly_plan
    from core.bible_sender import broadcast_messages, send_only_summaries
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def check_plan_exists(year, month):
    plan_path = os.path.join(BASE_DIR, 'data', 'plans', f"{str(month).zfill(2)}.json")
    return os.path.exists(plan_path)

async def run_smart_mode(year, month, kst_now):
    """데이터가 없으면 자동 생성 후 발송하는 스마트 모드"""
    if not check_plan_exists(year, month):
        print(f"ℹ️ {month}월 데이터가 없습니다. AI 파싱을 먼저 시도합니다...")
        generate_monthly_plan(year, month)
    
    if check_plan_exists(year, month):
        print(f"🚀 {year}년 {month}월 본문 발송을 시작합니다...")
        # 단체방 발송 시도
        success = await broadcast_messages(kst_now)
        
        # [수정] 단체방 발송이 성공(True)했을 때만 개인 요약본 발송
        if success:
            print(f"💌 개인방(Mydailybot)으로 3개 국어 요약본을 발송합니다...")
            await send_only_summaries("5929322817", kst_now)
        else:
            print(f"⚠️ 단체방 발송이 취소/실패하여 개인 요약본도 발송하지 않습니다.")
    else:
        print(f"❌ 데이터를 찾거나 생성할 수 없습니다. assets/ 폴더의 파일명을 확인해주세요.")

async def start():
    parser = argparse.ArgumentParser(description="📖 성경 알림 봇 통합 관리자")
    subparsers = parser.add_subparsers(dest="command", help="명령어 목록")
    
    # run: 스마트 자동 실행 (기본값)
    run_p = subparsers.add_parser("run", help="스마트 실행 (데이터 없으면 생성 후 발송)")
    run_p.add_argument("--year", type=int, help="연도 (기본: 올해)")
    run_p.add_argument("--month", type=int, help="월 (기본: 이번 달)")
    
    # parse: 데이터 생성만
    parse_p = subparsers.add_parser("parse", help="데이터(JSON)만 생성")
    parse_p.add_argument("year", type=int, nargs='?', help="연도 (생략 시 다음 달)")
    parse_p.add_argument("month", type=int, nargs='?', help="월 (생략 시 다음 달)")
    
    # send: 발송만
    send_p = subparsers.add_parser("send", help="메시지만 발송")

    # summary: 개인톡 요약본 발송
    summary_p = subparsers.add_parser("summary", help="개인 대화방으로 3개 국어 요약본만 발송")
    
    # check: 채팅방 ID 확인
    check_p = subparsers.add_parser("check", help="최근 도착한 메시지의 채팅방 ID 확인")
    
    if len(sys.argv) == 1:
        args = parser.parse_args(["run"])
    else:
        args = parser.parse_args()
    
    # [중요] 모든 작업의 기준이 되는 한국 시간 (KST) 고정
    from datetime import timedelta
    kst_now = datetime.utcnow() + timedelta(hours=9)
    
    if args.command == "parse":
        if args.year and args.month:
            generate_monthly_plan(args.year, args.month)
        else:
            from tools.gemini_parser import get_next_month
            nxt_y, nxt_m = get_next_month()
            print(f"📅 연/월 생략됨. 자동으로 다음 달({nxt_y}년 {nxt_m}월) 데이터를 생성합니다.")
            generate_monthly_plan(nxt_y, nxt_m)
    elif args.command == "send":
        await broadcast_messages(kst_now)
    elif args.command == "summary":
        # 사용자 개인 ID (5929322817)로 발송
        await send_only_summaries("5929322817", kst_now)
    elif args.command == "check":
        from tools.check_chat_ids import check_telegram_ids
        check_telegram_ids()
    elif args.command == "run":
        year = args.year if args.year else kst_now.year
        month = args.month if args.month else kst_now.month
        await run_smart_mode(year, month, kst_now)

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
