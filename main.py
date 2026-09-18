import os
import sys
import argparse
import asyncio
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# [보안 & 편의] 중앙 .env 로드 로직 (root/.secrets/.env 우선)
def load_env_centralized():
    central_secrets = Path(BASE_DIR).parent / ".secrets" / ".env"
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
    from tools.plan_parser import (
        generate_monthly_plan,
        is_hwpx_parsing_enabled,
        set_hwpx_parsing_enabled,
    )
    from core.bible_sender import broadcast_messages, deliver_daily, send_only_summaries
    from core.recipient_config import resolve_owner_recipient
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    sys.exit(1)

def check_plan_exists(year, month):
    plan_path = os.path.join(BASE_DIR, 'data', 'plans', f"{int(year):04d}_{int(month):02d}.json")
    return os.path.exists(plan_path)

async def run_smart_mode(year, month, kst_now, owner_chat_id=None):
    """데이터가 없으면 자동 생성 후 발송하는 스마트 모드"""
    if not check_plan_exists(year, month):
        print(f"ℹ️ {month}월 데이터가 없습니다. AI 파싱을 먼저 시도합니다...")
        generate_monthly_plan(year, month)
    
    if check_plan_exists(year, month):
        print(f"🚀 {year}년 {month}월 본문 발송을 시작합니다...")
        success = await deliver_daily(kst_now, owner_chat_id)
        if not success:
            print(f"⚠️ 단체방 발송이 취소/실패하여 개인 요약본도 발송하지 않습니다.")
    else:
        print(f"❌ 데이터를 찾거나 생성할 수 없습니다. assets/ 폴더의 파일명을 확인해주세요.")
    await send_prayers_if_due()


async def send_prayers_if_due():
    """기존 일일 실행에 주간 기도 발송을 붙인다. 실패해도 성경 발송은 되돌리지 않는다."""
    from tools.prayer_manager import send_oat_today, send_today

    try:
        count = await asyncio.to_thread(send_today)
        if count:
            print(f"🙏 주간 기도제목 {count}명 발송 완료")
        oat_count = await asyncio.to_thread(send_oat_today)
        if oat_count:
            print(f"🙏 OAT 기도제목 {oat_count}명 발송 완료")
    except Exception as e:
        print(f"❌ 주간 기도제목 발송 실패: {e}")

async def start():
    parser = argparse.ArgumentParser(description="📖 성경 알림 봇 통합 관리자")
    subparsers = parser.add_subparsers(dest="command", help="명령어 목록")
    
    # run: 스마트 자동 실행 (기본값)
    run_p = subparsers.add_parser("run", help="스마트 실행 (데이터 없으면 생성 후 발송)")
    run_p.add_argument("--year", type=int, help="연도 (기본: 올해)")
    run_p.add_argument("--month", type=int, help="월 (기본: 이번 달)")
    run_p.add_argument("--owner-chat-id", help="개인 요약을 받을 대화방 ID")
    
    # parse: 데이터 생성만
    parse_p = subparsers.add_parser("parse", help="데이터(JSON)만 생성")
    parse_p.add_argument("year", type=int, nargs='?', help="연도 (생략 시 다음 달)")
    parse_p.add_argument("month", type=int, nargs='?', help="월 (생략 시 다음 달)")
    hwpx_toggle = parse_p.add_mutually_exclusive_group()
    hwpx_toggle.add_argument(
        "--enable-hwpx",
        action="store_true",
        help="HWPX parsing을 켜고 종료",
    )
    hwpx_toggle.add_argument(
        "--disable-hwpx",
        action="store_true",
        help="HWPX parsing을 끄고 종료",
    )
    hwpx_toggle.add_argument(
        "--hwpx-status",
        action="store_true",
        help="현재 HWPX parsing 상태를 표시하고 종료",
    )
    
    # send: 발송만
    send_p = subparsers.add_parser("send", help="메시지만 발송")
    send_p.add_argument(
        "--target",
        choices=("all", "ko", "en", "mn", "owner"),
        default="all",
        help="all=설정된 그룹 전문+owner 요약, ko/en/mn=그룹 전문, owner=개인 요약",
    )
    send_p.add_argument("--date", type=date.fromisoformat, help="발송 날짜 (YYYY-MM-DD)")

    # summary: 개인톡 요약본 발송
    summary_p = subparsers.add_parser("summary", help="개인 대화방으로 3개 국어 요약본만 발송")
    summary_p.add_argument("--chat-id", help="요약을 받을 대화방 ID")
    
    # check: 채팅방 ID 확인
    check_p = subparsers.add_parser("check", help="최근 도착한 메시지의 채팅방 ID 확인")

    # plan: 월별 JSON 조회/수정/검증/배포 UI
    plan_p = subparsers.add_parser(
        "plan",
        help="월별 말씀 plan 관리 UI",
        add_help=False,
    )
    plan_p.add_argument("-h", "--help", action="store_true", dest="plan_help")
    plan_p.add_argument("plan_args", nargs=argparse.REMAINDER)

    prayer_p = subparsers.add_parser(
        "prayer",
        help="주간 기도제목 이미지 OCR/발송",
        add_help=False,
    )
    prayer_p.add_argument("-h", "--help", action="store_true", dest="prayer_help")
    prayer_p.add_argument("prayer_args", nargs=argparse.REMAINDER)
    
    if len(sys.argv) == 1:
        args = parser.parse_args(["run"])
    else:
        args = parser.parse_args()
    
    # [중요] 모든 작업의 기준이 되는 한국 시간 (KST) 고정
    kst_now = datetime.now(ZoneInfo("Asia/Seoul"))
    
    if args.command == "plan":
        from tools.plan_manager import main as plan_manager_main

        plan_args = ["--help"] if args.plan_help else args.plan_args
        result = plan_manager_main(plan_args)
        if result:
            raise SystemExit(result)
    elif args.command == "prayer":
        from tools.prayer_manager import main as prayer_manager_main

        prayer_args = ["--help"] if args.prayer_help else args.prayer_args
        result = prayer_manager_main(prayer_args)
        if result:
            raise SystemExit(result)
    elif args.command == "parse":
        if args.enable_hwpx or args.disable_hwpx:
            enabled = bool(args.enable_hwpx)
            set_hwpx_parsing_enabled(enabled)
            print(f"⚙️ HWPX parsing: {'ON' if enabled else 'OFF'}")
            return
        if args.hwpx_status:
            enabled = is_hwpx_parsing_enabled()
            print(f"⚙️ HWPX parsing: {'ON' if enabled else 'OFF'}")
            return
        if args.year and args.month:
            generate_monthly_plan(args.year, args.month)
        else:
            from tools.plan_parser import get_next_month
            nxt_y, nxt_m = get_next_month()
            print(f"📅 연/월 생략됨. 자동으로 다음 달({nxt_y}년 {nxt_m}월) 데이터를 생성합니다.")
            generate_monthly_plan(nxt_y, nxt_m)
    elif args.command == "send":
        send_time = (
            datetime.combine(args.date, time(), ZoneInfo("Asia/Seoul"))
            if args.date
            else kst_now
        )
        if args.target == "all":
            await deliver_daily(send_time)
            if not args.date:
                await send_prayers_if_due()
        elif args.target == "owner":
            recipient, source = resolve_owner_recipient()
            print(f"💌 MydailyBibleBot owner 요약 수신처: {source}")
            await send_only_summaries(recipient, send_time)
        else:
            await broadcast_messages(send_time, target=args.target)
    elif args.command == "summary":
        recipient, source = resolve_owner_recipient(args.chat_id)
        print(f"💌 MydailyBibleBot 개인 요약 수신처: {source}")
        await send_only_summaries(recipient, kst_now)
    elif args.command == "check":
        from tools.check_chat_ids import check_telegram_ids
        check_telegram_ids()
    elif args.command == "run":
        year = args.year if args.year else kst_now.year
        month = args.month if args.month else kst_now.month
        await run_smart_mode(year, month, kst_now, args.owner_chat_id)

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
