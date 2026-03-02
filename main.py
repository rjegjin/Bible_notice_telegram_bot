import os
import sys
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'tools'))

# 기존 모듈 임포트 (경로 문제 해결)
try:
    from tools.gemini_parser import generate_monthly_plan
except ImportError:
    try:
        from gemini_parser import generate_monthly_plan
    except ImportError:
        print("❌ gemini_parser 모듈을 찾을 수 없습니다.")
        sys.exit(1)

try:
    from send_bible_passage_all import broadcast_messages
except ImportError:
    print("❌ send_bible_passage_all 모듈을 찾을 수 없습니다.")
    sys.exit(1)

def check_plan_exists(year, month):
    plan_path = os.path.join(BASE_DIR, 'plans', f"{str(month).zfill(2)}.json")
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
    parse_p.add_argument("year", type=int, help="연도")
    parse_p.add_argument("month", type=int, help="월")
    
    # send: 발송만
    send_p = subparsers.add_parser("send", help="메시지만 발송")
    
    # 인자 없이 실행할 경우를 대비해 기본값 처리
    if len(sys.argv) == 1:
        args = parser.parse_args(["run"])
    else:
        args = parser.parse_args()
    
    now = datetime.now()
    year = args.year if hasattr(args, 'year') and args.year else now.year
    month = args.month if hasattr(args, 'month') and args.month else now.month
    
    if args.command == "parse":
        generate_monthly_plan(args.year, args.month)
    elif args.command == "send":
        await broadcast_messages()
    elif args.command == "run":
        await run_smart_mode(year, month)

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("
👋 프로그램을 종료합니다.")
