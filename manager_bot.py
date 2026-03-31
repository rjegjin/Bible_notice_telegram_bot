"""
Bible Notice Bot — 자체 관리 봇
TELEGRAM_TOKEN으로 상시 실행, 자기 채팅방 직접 관리.
- /start, /manage : 인라인 키보드
- /send, /summary, /run : 직접 트리거
- 매일 자동 발송 (기존 main.py run 모드 재사용)
"""
import asyncio
import logging
import os
import subprocess
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".secrets", ".env"))

TOKEN    = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ATTENDANCE_TELEGRAM_CHAT_ID", "5929322817"))
VENV_PY  = "/home/rjegj/projects/unified_venv/bin/python"
MAIN_PY  = os.path.join(BASE_DIR, "main.py")

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def _trigger(cmd: str):
    subprocess.Popen(
        [VENV_PY, MAIN_PY, cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return f"`{cmd}` 실행 시작됨"


def _menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 오늘 말씀 발송 (send)",   callback_data="bible:send")],
        [InlineKeyboardButton("📋 요약만 발송 (summary)",   callback_data="bible:summary")],
        [InlineKeyboardButton("🔄 스마트 모드 (run)",       callback_data="bible:run")],
    ])


async def cmd_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Bible Notice Bot*\n동작을 선택하세요:",
        parse_mode="Markdown", reply_markup=_menu()
    )

async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "send"))

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "summary"))

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "run"))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data.split(":")[-1]
    msg = await asyncio.to_thread(_trigger, cmd)
    await query.edit_message_text(
        f"📖 *Bible Notice Bot*\n{msg}",
        parse_mode="Markdown", reply_markup=_menu()
    )


async def daily_send(app: Application):
    log.info("일정 발송: send")
    await asyncio.to_thread(_trigger, "send")


async def post_init(app: Application):
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(daily_send, "cron", hour=6, minute=0, args=[app], id="bible_daily")
    scheduler.start()
    log.info("스케줄러 시작 — 매일 06:00 KST 자동 발송")


def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN 없음"); return
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",   cmd_manage))
    app.add_handler(CommandHandler("manage",  cmd_manage))
    app.add_handler(CommandHandler("send",    cmd_send))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("run",     cmd_run))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
