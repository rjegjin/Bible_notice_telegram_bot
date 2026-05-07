"""
Bible Notice Bot — 자체 관리 봇
TELEGRAM_TOKEN으로 상시 실행, 자기 채팅방 직접 관리.
- /start, /manage : 인라인 키보드
- /send, /summary, /run : 직접 트리거
- 매일 자동 발송은 mh_bot systemd timer(bible-daily-send.timer)가 담당
"""
import asyncio
import logging
import os
import subprocess
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), ".secrets", ".env"))

TOKEN    = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ATTENDANCE_TELEGRAM_CHAT_ID", "5929322817"))
VENV_PY  = os.path.join(os.path.dirname(BASE_DIR), "unified_venv", "bin", "python")
MAIN_PY  = os.path.join(BASE_DIR, "main.py")

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def _trigger(cmd: str):
    subprocess.Popen(
        [VENV_PY, MAIN_PY, cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return f"`{cmd}` 실행 시작됨"


def _menu_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 오늘 말씀 발송 (send)",   callback_data="bible:send")],
        [InlineKeyboardButton("📋 요약만 발송 (summary)",   callback_data="bible:summary")],
        [InlineKeyboardButton("🔄 스마트 모드 (run)",       callback_data="bible:run")],
    ])

def _menu_reply():
    """하단에 항상 상주하는 메뉴 키보드"""
    return ReplyKeyboardMarkup([
        ["📤 말씀 발송", "📋 요약만 발송"],
        ["🔄 스마트 모드"]
    ], resize_keyboard=True)


async def cmd_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Bible Notice Bot*\n메뉴를 선택하세요:",
        parse_mode="Markdown", reply_markup=_menu_reply()
    )
    await update.message.reply_text(
        "원하시는 작업을 선택하세요:",
        reply_markup=_menu_inline()
    )

async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "send"))

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "summary"))

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(_trigger, "run"))

async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """하단 상주 메뉴 버튼 클릭 처리"""
    text = update.message.text

    if text == "📤 말씀 발송":
        msg = await asyncio.to_thread(_trigger, "send")
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")
    elif text == "📋 요약만 발송":
        msg = await asyncio.to_thread(_trigger, "summary")
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")
    elif text == "🔄 스마트 모드":
        msg = await asyncio.to_thread(_trigger, "run")
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data.split(":")[-1]
    msg = await asyncio.to_thread(_trigger, cmd)
    await query.edit_message_text(
        f"📖 *Bible Notice Bot*\n{msg}",
        parse_mode="Markdown", reply_markup=_menu_inline()
    )


def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN 없음"); return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_manage))
    app.add_handler(CommandHandler("manage",  cmd_manage))
    app.add_handler(CommandHandler("send",    cmd_send))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("run",     cmd_run))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
