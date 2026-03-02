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
    # 1. 최상위 .secrets/.env 확인
    central_secrets = Path("/home/rjegj/projects/.secrets/.env")
    if central_secrets.exists():
        load_dotenv(central_secrets)
        # print(f"🔐 Loaded central secrets from {central_secrets}")
        return True
    
    # 2. 프로젝트 로컬 .env 확인 (Fallback)
    local_env = os.path.join(BASE_DIR, '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)
        # print(f"📝 Loaded local .env from {local_env}")
        return True
    
    return False

# 실행 전 환경 변수 로드
load_env_centralized()

# 신규 구조에 맞춘 임포트
try:
    from tools.gemini_parser import generate_monthly_plan
    from core.bible_sender import broadcast_messages
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def check_plan_exists(year, month):
    # data/plans 폴더 내 데이터 확인
    plan_path = os.path.join(BASE_DIR, 'data', 'plans', f"{str(month).zfill(2)}.json")
    return os.path.exists(plan_path)

async def run_smart_mode(year, month):
    """데이터가 없으면 자동 생성 후 발송하는 스마트 모드"""
    if not check_plan_exists(year, month):
        print(f"ℹ️ {month}월 데이터가 없습니다. AI 파싱을 먼저 시도합니다...")
        generate_monthly_plan(year, month)
    
    if check_plan_exists(year, month):
        print(f"🚀 {year}년 {month}월 본문 발송을 시작합니다...")
        await broadcast_messages()
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
    
    # check: 채팅방 ID 확인 (추가)
    check_p = subparsers.add_parser("check", help="최근 도착한 메시지의 채팅방 ID 확인")
    
    # 인자 없이 실행할 경우를 대비해 기본값 처리
    if len(sys.argv) == 1:
        args = parser.parse_args(["run"])
    else:
        args = parser.parse_args()
    
    now = datetime.now()
    
    if args.command == "parse":
        if args.year and args.month:
            generate_monthly_plan(args.year, args.month)
        else:
            # 다음 달 자동 계산 (기존 gemini_parser 로직 활용)
            from tools.gemini_parser import get_next_month
            nxt_y, nxt_m = get_next_month()
            print(f"📅 연/월 생략됨. 자동으로 다음 달({nxt_y}년 {nxt_m}월) 데이터를 생성합니다.")
            generate_monthly_plan(nxt_y, nxt_m)
    elif args.command == "send":
        await broadcast_messages()
    elif args.command == "check":
        from tools.check_chat_ids import check_telegram_ids
        check_telegram_ids()
    elif args.command == "run":
        year = args.year if args.year else now.year
        month = args.month if args.month else now.month
        await run_smart_mode(year, month)

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
