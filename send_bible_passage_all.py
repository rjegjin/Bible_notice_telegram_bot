import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Bot
from dotenv import load_dotenv

# [필수] bible_common.py가 같은 폴더에 있어야 합니다.
from bible_common import get_chapter_text, get_qt_text, split_text_for_telegram, translate_citation

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# --- [핵심 수정 1] 수신처 설정 (Key: 방ID, Value: 언어 리스트/문자열) ---
# .env에서 ID를 못 읽어오면 Key가 None이 될 수 있으므로, 아래 루프에서 예외 처리함
RECIPIENTS = {
    os.getenv('KO_CHAT_ID'): 'KO',
    os.getenv('EN_CHAT_ID'): 'EN',
    os.getenv('MN_CHAT_ID'): 'MN',
}

# --- 언어별 메시지 템플릿 ---
translations = {
    'KO': {
        'title': "🌟 오늘의 묵상 알림",
        'qt_label': "📖 [오늘의 QT 본문]",
        'rd_label': "📚 [성경 읽기 진도]",
        'nt': "신약", 'ps': "시편", 'pr': "잠언",
        'unit_ps': "편", 'unit_pr': "장", 'none': "주일(개인독서)",
        'slogan': "그리스도의 형상을 닮고 그의 형상을 닮게 하라"
    },
    'EN': {
        'title': "🌟 Daily Meditation",
        'qt_label': "📖 [Today's QT Passage]",
        'rd_label': "📚 [Bible Reading Plan]",
        'nt': "NT", 'ps': "Psalms", 'pr': "Proverbs",
        'unit_ps': "", 'unit_pr': "", 'none': "Sunday (Personal)",
        'slogan': "Be Like Christ, Make Like Christ."
    },
    'MN': {
        'title': "🌟 Өдрийн бясалгал",
        'qt_label': "📖 [Өнөөдрийн QT]",
        'rd_label': "📚 [Библи унших төлөвлөгөө]",
        'nt': "Шинэ Гэрээ", 'ps': "Дуулал", 'pr': "Сургаалт үгс",
        'unit_ps': "-р бүлэг", 'unit_pr': "-р бүлэг", 'none': "Ням гараг",
        'slogan': "Христ шиг байж, Христ шиг болгоцгооё." 
    }
}

def load_monthly_plan(month):
    # plans 폴더 내의 "01.json", "02.json" 형식 파일을 읽음
    filename = f"{month:02d}.json"
    file_path = os.path.join(os.path.dirname(__file__), 'plans', filename)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

async def broadcast_messages():
    if not TELEGRAM_TOKEN:
        print("❌ 설정 오류: TELEGRAM_TOKEN 없음")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    
    # --- [핵심 수정 2] KST 시간 계산 ---
    # GitHub Actions 서버(UTC)에서도 한국 시간으로 정확히 계산
    kst_now = datetime.utcnow() + timedelta(hours=9)
    current_month = kst_now.month
    day_str = str(kst_now.day)
    
    # 테스트용 (필요시 주석 해제)
    # current_month = 2
    # day_str = "15"

    plan = load_monthly_plan(current_month)
    if day_str not in plan:
        print(f"ℹ️ 데이터 없음: {current_month}월 {day_str}일")
        return

    # JSON 데이터 구조: [신약, 시편, 잠언, QT]
    raw_nt, raw_ps, raw_pr, raw_qt = plan[day_str]

    print(f"🚀 {kst_now.strftime('%Y-%m-%d')} (KST) 발송 시작...")

    # --- [핵심 수정 3] 발송 루프 개선 (단일/다중 언어 처리) ---
    for chat_id, lang_info in RECIPIENTS.items():
        if not chat_id: continue # ID가 없는 경우 건너뜀 (None 체크)

        # lang_info가 리스트(['KO','EN'])면 그대로, 문자열('KO')이면 리스트로 변환
        target_langs = lang_info if isinstance(lang_info, list) else [lang_info]

        print(f"📤 Chat ID {chat_id} -> {target_langs} 발송 중...")

        for lang_code in target_langs:
            try:
                lang_pack = translations.get(lang_code, translations['KO'])
                
                # 1. 텍스트 번역 (원어 -> 해당 언어)
                qt_display = translate_citation(raw_qt, lang_code)
                nt_display = translate_citation(raw_nt, lang_code)
                ps_display = translate_citation(raw_ps, lang_code)
                pr_display = translate_citation(raw_pr, lang_code)

                # 2. 요약 메시지 전송
                summary_msg = (
                    f"{lang_pack['title']} ({kst_now.strftime('%Y/%m/%d')})\n\n"
                    f"{lang_pack['qt_label']}\n👉 {qt_display}\n\n"
                    f"{lang_pack['rd_label']}\n"
                    f"▫️ {lang_pack['nt']}: {nt_display}\n"
                    f"▫️ {lang_pack['ps']}: {ps_display}{lang_pack['unit_ps']}\n"
                    f"▫️ {lang_pack['pr']}: {pr_display}{lang_pack['unit_pr']}\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"\"{lang_pack['slogan']}\""
                )
                await bot.send_message(chat_id=chat_id, text=summary_msg)
                await asyncio.sleep(0.5)

                # 3. QT 본문 전송
                qt_text = get_qt_text(raw_qt, lang_code)
                if qt_text:
                    for part in split_text_for_telegram(qt_text):
                        await bot.send_message(chat_id=chat_id, text=part)
                        await asyncio.sleep(0.3)
                
                # 4. 시편/잠언 본문 전송
                for book_abbr, raw_chap in [('시', raw_ps), ('잠', raw_pr)]:
                    if not raw_chap: continue
                    
                    text = get_chapter_text(book_abbr, raw_chap, lang_code)
                    if text:
                        for part in split_text_for_telegram(text):
                            await bot.send_message(chat_id=chat_id, text=part)
                            await asyncio.sleep(0.3)

                print(f"   ✅ [{lang_code}] 전송 성공")

            except Exception as e:
                print(f"   ❌ [{lang_code}] 전송 실패: {e}")

    print("🏁 전체 발송 완료")

if __name__ == "__main__":
    asyncio.run(broadcast_messages())