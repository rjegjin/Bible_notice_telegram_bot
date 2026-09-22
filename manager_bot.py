"""
Bible Notice Bot — 자체 관리 봇
TELEGRAM_TOKEN으로 상시 실행, 자기 채팅방 직접 관리.
- /start, /manage : 인라인 키보드
- /send, /summary, /run, /chatid : 직접 트리거
- 매일 자동 발송은 mh_bot systemd timer(bible-daily-send.timer)가 담당
"""
import asyncio
import logging
import os
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from bot_common import load_secrets, require_env, run_bot
from core.recipient_config import build_room_send_args, build_trigger_args

load_secrets()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN    = require_env("TELEGRAM_TOKEN")
VENV_PY  = os.path.join(os.path.dirname(BASE_DIR), "unified_venv", "bin", "python")
MAIN_PY  = os.path.join(BASE_DIR, "main.py")

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)
_PLAN_ALBUMS = {}
_PRAYER_DAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5}


def _parse_plan_captions(caption: str):
    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    matches = [re.fullmatch(r"/(qt|br)\s+(\d{4})\s+(\d{1,2})", line, re.IGNORECASE) for line in lines]
    if not matches or not all(matches):
        return []
    return [(match.group(1).upper(), match.group(2), match.group(3)) for match in matches]


def _message_media(message):
    return message.photo[-1] if message.photo else message.document


def _send_command_args(args):
    if len(args) > 2:
        raise ValueError("사용법: /send [YYYY-MM-DD] [all|ko|en|mn|owner]")
    target = "all"
    day = None
    for value in args:
        if value in {"all", "ko", "en", "mn", "owner"}:
            target = value
        else:
            day = date.fromisoformat(value).isoformat()
    command = build_room_send_args(target)
    if day:
        command += ["--date", day]
    return command


def _resolve_prayer_day(value, today=None):
    key = value.removesuffix("요일")
    if key not in _PRAYER_DAYS:
        raise ValueError("요일은 월, 화, 수, 목, 금, 토 중 하나로 입력해주세요.")
    current = today or datetime.now(ZoneInfo("Asia/Seoul")).date()
    sunday = current - timedelta(days=(current.weekday() + 1) % 7)
    return sunday + timedelta(days=_PRAYER_DAYS[key] + 1)


def _album_result_message(commands, outputs):
    if outputs and "✅ standby 생성:" in outputs[-1]:
        saved = "\n".join(f"✅ {kind} 저장 완료" for kind, _, _ in commands)
        return f"{saved}\n✅ standby JSON 생성 및 월 전체 validation 통과\n⏸ 운영 반영 안 됨 · 검토 후 plan publish 필요"
    return f"❌ standby 생성 실패\n{outputs[-1] if outputs else '처리 결과 없음'}"


async def _reply_chunks(message, text, limit=3500):
    while text:
        split_at = text.rfind("\n", 0, limit)
        if split_at < 1:
            split_at = min(limit, len(text))
        await message.reply_text(text[:split_at])
        text = text[split_at:].lstrip("\n")


def _trigger(cmd: str, chat_id=None, target=None):
    if cmd == "send":
        command_args = build_room_send_args(target or "all")
    else:
        command_args = build_trigger_args(cmd, chat_id)
    subprocess.Popen(
        [VENV_PY, MAIN_PY, *command_args],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if cmd == "send":
        destination = "설정된 그룹 전문" if target in (None, "all") else f"{target.upper()}방 전문"
    else:
        destination = "현재 대화방" if chat_id is not None and cmd in ("summary", "run") else "등록된 수신처"
    return f"`{cmd}` 실행 시작됨 · 수신처: {destination}"


def _menu_inline():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇰🇷 KO방 전문", callback_data="bible:send:ko"),
            InlineKeyboardButton("🇬🇧 EN방 전문", callback_data="bible:send:en"),
            InlineKeyboardButton("🇲🇳 MN방 전문", callback_data="bible:send:mn"),
        ],
        [InlineKeyboardButton("🏠 내 방 요약", callback_data="bible:summary")],
        [InlineKeyboardButton("📤 그룹 전문 + 내 방 요약", callback_data="bible:send:all")],
        [InlineKeyboardButton("🔄 그룹 전문 + 이 대화방 요약", callback_data="bible:run")],
        [InlineKeyboardButton("📖 오늘 말씀 재전송", callback_data="bible:today:all")],
        [
            InlineKeyboardButton(f"🙏 {day}", callback_data=f"bible:prayer:{index}")
            for index, day in enumerate(_PRAYER_DAYS)
        ],
        [
            InlineKeyboardButton(f"OAT {day}", callback_data=f"bible:oat:{index}")
            for index, day in enumerate(_PRAYER_DAYS)
        ],
    ])

def _menu_reply():
    """하단에 항상 상주하는 메뉴 키보드"""
    return ReplyKeyboardMarkup([
        ["🇰🇷 KO방 전문", "🇬🇧 EN방 전문", "🇲🇳 MN방 전문"],
        ["🏠 내 방 요약"],
        ["📤 그룹 전문 + 내 방 요약"],
        ["🔄 그룹 전문 + 이 대화방 요약"]
    ], resize_keyboard=True)


HELP_TEXT = """📖 Bible Notice Bot

━━ 이미지로 등록하기 (owner 개인방에서만) ━━

🙏 주간기도제목
  사진 1장을 보내면서 caption에 `/prayer`
  → OCR 결과가 정확히 13명일 때만 저장된다
  `/prayerpreview` 로 검토 → `/prayerapprove` 로 승인

📅 월간 QT·BR 계획표
  QT·BR 사진 2장을 **한 앨범으로** 보내고 caption에 두 줄:
      /qt 2026 10
      /br 2026 10
  · caption 줄 순서 = 사진 순서
  · 한 앨범에 같은 연월의 /qt 와 /br 을 하나씩
  · 한 장만 보낼 때는 caption 한 줄 (`/qt 2026 10`)
  → standby JSON 생성 + 월 전체 검증까지만 한다.
    **운영에는 반영되지 않는다.** 반영하려면 터미널에서:
      python main.py plan publish 2026 10

━━ 발송 ━━
/send [YYYY-MM-DD] [all|ko|en|mn|owner]
    말씀 발송 (인자 없으면 오늘·전체)
/summary      내 방으로 3개 국어 요약본
/run          그룹 전문 + 이 방 요약
/prayerday 월|화|수|목|금|토    그 요일 기도제목 재호출
/oatday    월|화|수|목|금|토    그 요일 OAT 재호출

━━ 기타 ━━
/prayerpreview  저장된 기도제목 검토
/prayerapprove  기도제목 승인
/manage         버튼 메뉴
/chatid         이 대화방 ID
/help           이 도움말"""


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


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
    try:
        command = _send_command_args(context.args)
    except ValueError as error:
        await update.message.reply_text(str(error))
        return
    subprocess.Popen(
        [VENV_PY, MAIN_PY, *command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    await update.message.reply_text(f"`{' '.join(command)}` 실행 시작됨", parse_mode="Markdown")


async def _send_prayer_day(message, chat_id, value, *, oat=False):
    owner_chat_id = os.getenv("BIBLE_OWNER_CHAT_ID") or os.getenv("EN_CHAT_ID")
    if not owner_chat_id or str(chat_id) != str(owner_chat_id):
        await message.reply_text("이 기능은 owner 개인방에서만 사용할 수 있습니다.")
        return
    try:
        day = _resolve_prayer_day(value)
    except ValueError as error:
        await message.reply_text(str(error))
        return
    result = await asyncio.to_thread(
        subprocess.run,
        [
            VENV_PY, MAIN_PY, "prayer", "oat-send" if oat else "send",
            "--date", day.isoformat(),
            "--force", "--chat-id", str(chat_id),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (result.stdout if result.returncode == 0 else result.stderr).strip()
    await message.reply_text(output or "기도제목 재호출 결과가 없습니다.")


async def cmd_prayerday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("사용법: /prayerday 월|화|수|목|금|토")
        return
    await _send_prayer_day(update.message, update.effective_chat.id, context.args[0])


async def cmd_oatday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("사용법: /oatday 월|화|수|목|금|토")
        return
    await _send_prayer_day(
        update.message,
        update.effective_chat.id,
        context.args[0],
        oat=True,
    )

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        await asyncio.to_thread(_trigger, "summary", update.effective_chat.id)
    )

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        await asyncio.to_thread(_trigger, "run", update.effective_chat.id)
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"`{update.effective_chat.id}`", parse_mode="Markdown")


async def cmd_prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "주간기도제목 이미지를 사진으로 보내면서 caption에 /prayer 를 입력해주세요. "
        "OCR 결과가 정확히 13명일 때만 저장됩니다. 전체 절차는 /help 참고."
    )


async def cmd_plan_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "사진 caption을 `/qt 2026 10` 또는 `/br 2026 10`처럼 입력해주세요. "
        "두 이미지가 모두 모이면 검증된 standby JSON을 만듭니다. 전체 절차는 /help 참고.",
        parse_mode="Markdown",
    )


async def cmd_prayerapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_chat_id = os.getenv("BIBLE_OWNER_CHAT_ID") or os.getenv("EN_CHAT_ID")
    if not owner_chat_id or str(update.effective_chat.id) != str(owner_chat_id):
        await update.message.reply_text("이 기능은 owner 개인방에서만 사용할 수 있습니다.")
        return
    result = await asyncio.to_thread(
        subprocess.run,
        [VENV_PY, MAIN_PY, "prayer", "approve"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (result.stdout if result.returncode == 0 else result.stderr).strip()
    await update.message.reply_text(output or "기도제목 승인 결과가 없습니다.")


async def cmd_prayerpreview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_chat_id = os.getenv("BIBLE_OWNER_CHAT_ID") or os.getenv("EN_CHAT_ID")
    if not owner_chat_id or str(update.effective_chat.id) != str(owner_chat_id):
        await update.message.reply_text("이 기능은 owner 개인방에서만 사용할 수 있습니다.")
        return
    result = await asyncio.to_thread(
        subprocess.run,
        [VENV_PY, MAIN_PY, "prayer", "preview"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (result.stdout if result.returncode == 0 else result.stderr).strip()
    await _reply_chunks(update.message, output or "기도제목 검토 결과가 없습니다.")


async def _run_plan_photo(photo, kind, year, month):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temporary:
        image_path = Path(temporary.name)
    try:
        telegram_file = await photo.get_file()
        await telegram_file.download_to_drive(image_path)
        result = await asyncio.to_thread(
            subprocess.run,
            [VENV_PY, MAIN_PY, "plan", "stage-image", year, month, kind, str(image_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "stage-image 실행 실패")
        return result.stdout.strip()
    finally:
        image_path.unlink(missing_ok=True)


async def _finish_plan_album(media_group_id):
    await asyncio.sleep(1)
    album = _PLAN_ALBUMS.pop(media_group_id, None)
    if not album:
        return
    message = album["message"]
    photos = [photo for _, photo in sorted(album["photos"])]
    commands = album["commands"]
    if len(photos) != len(commands):
        await message.reply_text(f"❌ 앨범 사진 {len(photos)}장과 caption 명령 {len(commands)}개의 수가 다릅니다.")
        return
    if len({(year, month) for _, year, month in commands}) != 1 or {kind for kind, _, _ in commands} != {"BR", "QT"}:
        await message.reply_text("❌ 한 앨범에는 같은 연월의 /br과 /qt를 하나씩 입력해주세요.")
        return
    try:
        outputs = []
        for photo, (kind, year, month) in zip(photos, commands):
            if not 1 <= int(month) <= 12:
                raise ValueError("월은 1~12로 입력해주세요.")
            outputs.append(await _run_plan_photo(photo, kind, year, month))
        await message.reply_text(_album_result_message(commands, outputs)[-3500:])
    except subprocess.TimeoutExpired:
        await message.reply_text("❌ 이미지 분석 시간이 초과되었습니다. 다시 시도해주세요.")
    except Exception as error:
        await message.reply_text(f"❌ 이미지 처리 실패: {error}")


async def handle_prayer_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (update.message.caption or "").strip()
    plan_commands = _parse_plan_captions(caption)
    media_group_id = update.message.media_group_id
    if caption != "/prayer" and not plan_commands and media_group_id not in _PLAN_ALBUMS:
        return
    owner_chat_id = os.getenv("BIBLE_OWNER_CHAT_ID") or os.getenv("EN_CHAT_ID")
    if not owner_chat_id or str(update.effective_chat.id) != str(owner_chat_id):
        await update.message.reply_text("이 기능은 owner 개인방에서만 사용할 수 있습니다.")
        return

    if media_group_id and (plan_commands or media_group_id in _PLAN_ALBUMS):
        album = _PLAN_ALBUMS.setdefault(
            media_group_id,
            {"photos": [], "commands": [], "message": update.message, "scheduled": False},
        )
        album["photos"].append((update.message.message_id, _message_media(update.message)))
        if plan_commands:
            album["commands"] = plan_commands
            album["message"] = update.message
        if not album["scheduled"]:
            album["scheduled"] = True
            context.application.create_task(_finish_plan_album(media_group_id), update=update)
        return

    if plan_commands:
        kind, year, month = plan_commands[0]
        if not 1 <= int(month) <= 12:
            await update.message.reply_text("월은 1~12로 입력해주세요.")
            return
        await update.message.reply_text(f"🔍 {year}년 {int(month)}월 {kind} 이미지를 처리하고 있습니다...")
        try:
            output = await _run_plan_photo(_message_media(update.message), kind, year, month)
            await update.message.reply_text(output[-3500:] or "이미지 처리 결과가 없습니다.")
        except subprocess.TimeoutExpired:
            await update.message.reply_text("❌ 이미지 분석 시간이 초과되었습니다. 다시 시도해주세요.")
        return
    else:
        await update.message.reply_text("🔍 주간기도제목 13명을 추출하고 있습니다...")
        command = [VENV_PY, MAIN_PY, "prayer", "import"]
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temporary:
        image_path = Path(temporary.name)
    try:
        telegram_file = await _message_media(update.message).get_file()
        await telegram_file.download_to_drive(image_path)
        result = await asyncio.to_thread(
            subprocess.run,
            [*command, str(image_path), "--replace"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (result.stdout if result.returncode == 0 else result.stderr).strip()
        await _reply_chunks(update.message, output or "기도제목 처리 결과가 없습니다.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ 이미지 분석 시간이 초과되었습니다. 다시 시도해주세요.")
    finally:
        image_path.unlink(missing_ok=True)


async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """하단 상주 메뉴 버튼 클릭 처리"""
    text = update.message.text

    if text == "📤 그룹 전문 + 내 방 요약":
        msg = await asyncio.to_thread(_trigger, "send", None, "all")
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")
    elif text in {"🇰🇷 KO방 전문", "🇬🇧 EN방 전문", "🇲🇳 MN방 전문"}:
        target = {
            "🇰🇷 KO방 전문": "ko",
            "🇬🇧 EN방 전문": "en",
            "🇲🇳 MN방 전문": "mn",
        }[text]
        msg = await asyncio.to_thread(_trigger, "send", None, target)
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")
    elif text == "🏠 내 방 요약":
        msg = await asyncio.to_thread(_trigger, "summary", update.effective_chat.id)
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")
    elif text == "🔄 그룹 전문 + 이 대화방 요약":
        msg = await asyncio.to_thread(_trigger, "run", update.effective_chat.id)
        await update.message.reply_text(f"📖 *Bible Notice Bot*\n{msg}", parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    cmd = parts[1]
    if cmd == "today":
        today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        command = _send_command_args([today, parts[2]])
        subprocess.Popen(
            [VENV_PY, MAIN_PY, *command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        await query.edit_message_text(
            f"📖 *Bible Notice Bot*\n`{' '.join(command)}` 실행 시작됨",
            parse_mode="Markdown",
            reply_markup=_menu_inline(),
        )
        return
    if cmd == "prayer":
        day_name = tuple(_PRAYER_DAYS)[int(parts[2])]
        await _send_prayer_day(query.message, update.effective_chat.id, day_name)
        return
    if cmd == "oat":
        day_name = tuple(_PRAYER_DAYS)[int(parts[2])]
        await _send_prayer_day(
            query.message,
            update.effective_chat.id,
            day_name,
            oat=True,
        )
        return
    target = parts[2] if len(parts) > 2 else None
    chat_id = update.effective_chat.id if cmd in ("summary", "run") else None
    msg = await asyncio.to_thread(_trigger, cmd, chat_id, target)
    await query.edit_message_text(
        f"📖 *Bible Notice Bot*\n{msg}",
        parse_mode="Markdown", reply_markup=_menu_inline()
    )


async def post_init(app):
    """"/" 만 쳐도 Telegram이 명령 목록을 띄우게 한다."""
    from telegram import BotCommand
    try:
        await app.bot.set_my_commands([
            BotCommand("help", "명령어와 이미지 등록 절차"),
            BotCommand("send", "말씀 발송 (/send [날짜] [all|ko|en|mn|owner])"),
            BotCommand("summary", "내 방으로 3개 국어 요약"),
            BotCommand("run", "그룹 전문 + 이 방 요약"),
            BotCommand("prayer", "주간기도제목 이미지 등록 안내"),
            BotCommand("qt", "월간 QT 계획표 이미지 등록 안내"),
            BotCommand("br", "월간 BR 계획표 이미지 등록 안내"),
            BotCommand("prayerpreview", "저장된 기도제목 검토"),
            BotCommand("prayerapprove", "기도제목 승인"),
            BotCommand("prayerday", "요일 기도제목 재호출"),
            BotCommand("oatday", "요일 OAT 재호출"),
            BotCommand("manage", "버튼 메뉴"),
            BotCommand("chatid", "이 대화방 ID"),
        ])
    except Exception:
        log.exception("명령 목록 등록 실패 — 봇 동작에는 영향 없음")


def main():
    handlers = [
        CommandHandler("start",   cmd_manage),
        CommandHandler("manage",  cmd_manage),
        CommandHandler("help",    cmd_help),
        CommandHandler("send",    cmd_send),
        CommandHandler("summary", cmd_summary),
        CommandHandler("run",     cmd_run),
        CommandHandler("chatid",  cmd_chatid),
        CommandHandler("prayer",  cmd_prayer),
        CommandHandler("qt", cmd_plan_image),
        CommandHandler("br", cmd_plan_image),
        CommandHandler("prayerapprove", cmd_prayerapprove),
        CommandHandler("prayerpreview", cmd_prayerpreview),
        CommandHandler("prayerday", cmd_prayerday),
        CommandHandler("oatday", cmd_oatday),
        CallbackQueryHandler(handle_callback),
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_prayer_image),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_menu),
    ]
    run_bot(TOKEN, handlers, post_init=post_init)

if __name__ == "__main__":
    main()
