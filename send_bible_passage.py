import json
import os
import asyncio
import schedule
import time
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

# --- 설정 영역 ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # 봇 토큰을 환경변수에서 불러오기
CHAT_ID = os.getenv('KO_CHAT_ID')
SEND_TIME = "07:00"

# 언어 설정: 'KO' (한국어), 'EN' (영어), 'MN' (몽골어)
LANGUAGE_SETTING = 'KO' 

# --- 통합 데이터베이스 (날짜: [신약, 시편, 잠언, QT]) ---
# 이미지 데이터 기반: 1월 1일~31일 분량
def load_plan():
    if os.path.exists('bible_plan.json'):
        with open('bible_plan.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# --- 언어별 사전 (Translations) ---
translations = {
    'KO': {
        'title': "🌟 오늘의 묵상 알림",
        'qt': "📖 [오늘의 QT 본문]",
        'reading': "📚 [성경 읽기 진도]",
        'nt': "신약", 'ps': "시편", 'pr': "잠언",
        'unit_ps': "편", 'unit_pr': "장", 'none': "주일(개인독서)",
        'slogan': "그리스도의 형상을 닮고 그의 형상을 닮게 하라"
    },
    'EN': {
        'title': "🌟 Daily Meditation",
        'qt': "📖 [Today's QT Passage]",
        'reading': "📚 [Bible Reading Plan]",
        'nt': "New Testament", 'ps': "Psalms", 'pr': "Proverbs",
        'unit_ps': "", 'unit_pr': "", 'none': "Sunday(Personal)",
        'slogan': "Be formed in the image of Christ."
    },
    'MN': {
        'title': "🌟 Өдрийн бясалгал",
        'qt': "📖 [Өнөөдрийн QT]",
        'reading': "📚 [Библи унших төлөвлөгөө]",
        'nt': "Шинэ Гэрээ", 'ps': "Дуулал", 'pr': "Сургаалт үгс",
        'unit_ps': "-р бүлэг", 'unit_pr': "-р бүлэг", 'none': "Ням гараг",
        'slogan': "Христийн дүр төрхийг дуурайж, Түүний дүр төрхтэй адил болтугай"
    }
}

async def send_message():
    bot = Bot(token=TELEGRAM_TOKEN)
    now = datetime.now()
    day_str = str(now.day) # JSON 키는 문자열로 저장됨
    lang = translations.get(LANGUAGE_SETTING, translations['KO'])

    plan = load_plan()
    
    if day_str not in plan:
        print(f"{day_str}일자 데이터를 찾을 수 없습니다.")
        return

    nt, ps, pr, qt = plan[day_str]

    # 메시지 조립
    msg = (
        f"{lang['title']} ({now.year}/{now.month}/{day_str})\n\n"
        f"{lang['qt']}\n👉 {qt}\n\n"
            f"{lang['reading']}\n"
            f"▫️ {lang['nt']}: {nt if nt else lang['none']}\n"
            f"▫️ {lang['ps']}: {ps}{lang['unit_ps']}\n"
            f"▫️ {lang['pr']}: {pr}{lang['unit_pr']}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"\"{lang['slogan']}\""
        )
    await bot.send_message(chat_id=CHAT_ID, text=msg)

def job(): asyncio.run(send_message())

schedule.every().day.at(SEND_TIME).do(job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)