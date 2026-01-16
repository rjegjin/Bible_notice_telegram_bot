import json
import os
import asyncio
import re
from datetime import datetime, timedelta  # [수정] timedelta 추가
from telegram import Bot
from dotenv import load_dotenv

# [필수] bible_common.py가 같은 폴더에 있어야 합니다.
from bible_common import get_chapter_text, split_text_for_telegram

load_dotenv()

# --- 설정 영역 ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

RECIPIENTS = {
    'KO': os.getenv('KO_CHAT_ID'),
    'EN': os.getenv('EN_CHAT_ID'),
    'MN': os.getenv('MN_CHAT_ID')
}

# --- 성경 약어 변환 사전 (Full List) ---
BIBLE_MAP = {
    # --- 구약 (Old Testament) ---
    # 모세오경
    '창': {'EN': 'Gen', 'MN': 'Эхл'},
    '출': {'EN': 'Exod', 'MN': 'Гэт'},
    '레': {'EN': 'Lev', 'MN': 'Лев'},
    '민': {'EN': 'Num', 'MN': 'Тоо'},
    '신': {'EN': 'Deut', 'MN': 'Дэд'},
    
    # 역사서
    '수': {'EN': 'Josh', 'MN': 'Иош'},
    '삿': {'EN': 'Judg', 'MN': 'Шүү'},
    '룻': {'EN': 'Ruth', 'MN': 'Рут'},
    '삼상': {'EN': '1Sam', 'MN': '1Сам'},
    '삼하': {'EN': '2Sam', 'MN': '2Сам'},
    '왕상': {'EN': '1Kgs', 'MN': '1Хаа'},
    '왕하': {'EN': '2Kgs', 'MN': '2Хаа'},
    '대상': {'EN': '1Chr', 'MN': '1Шас'},
    '대하': {'EN': '2Chr', 'MN': '2Шас'},
    '스': {'EN': 'Ezra', 'MN': 'Езр'},
    '느': {'EN': 'Neh', 'MN': 'Нех'},
    '에': {'EN': 'Esth', 'MN': 'Ест'},
    
    # 시가서
    '욥': {'EN': 'Job', 'MN': 'Иов'},
    '시': {'EN': 'Ps', 'MN': 'Дуу'},
    '잠': {'EN': 'Prov', 'MN': 'Сур'},
    '전': {'EN': 'Eccl', 'MN': 'Ном'},
    '아': {'EN': 'Song', 'MN': 'Доо'},
    
    # 대선지서
    '사': {'EN': 'Isa', 'MN': 'Иса'},
    '렘': {'EN': 'Jer', 'MN': 'Иер'},
    '애': {'EN': 'Lam', 'MN': 'Гаш'},
    '겔': {'EN': 'Ezek', 'MN': 'Езе'},
    '단': {'EN': 'Dan', 'MN': 'Дан'},
    
    # 소선지서
    '호': {'EN': 'Hos', 'MN': 'Хос'},
    '욜': {'EN': 'Joel', 'MN': 'Иое'},
    '암': {'EN': 'Amos', 'MN': 'Амо'},
    '옵': {'EN': 'Obad', 'MN': 'Оба'},
    '욘': {'EN': 'Jonah', 'MN': 'Ион'},
    '미': {'EN': 'Mic', 'MN': 'Мик'},
    '나': {'EN': 'Nah', 'MN': 'Нах'},
    '합': {'EN': 'Hab', 'MN': 'Хаб'},
    '습': {'EN': 'Zeph', 'MN': 'Зеф'},
    '학': {'EN': 'Hag', 'MN': 'Хаг'},
    '슥': {'EN': 'Zech', 'MN': 'Зех'},
    '말': {'EN': 'Mal', 'MN': 'Мал'},

    # --- 신약 (New Testament) ---
    # 복음서
    '마': {'EN': 'Matt', 'MN': 'Мат'},
    '막': {'EN': 'Mark', 'MN': 'Марк'},
    '눅': {'EN': 'Luke', 'MN': 'Лук'},
    '요': {'EN': 'John', 'MN': 'Иох'},
    
    # 역사서
    '행': {'EN': 'Acts', 'MN': 'Үйл'},
    
    # 바울서신
    '롬': {'EN': 'Rom', 'MN': 'Ром'},
    '고전': {'EN': '1Cor', 'MN': '1Кор'},
    '고후': {'EN': '2Cor', 'MN': '2Кор'},
    '갈': {'EN': 'Gal', 'MN': 'Гал'},
    '엡': {'EN': 'Eph', 'MN': 'Еф'},
    '빌': {'EN': 'Phil', 'MN': 'Фил'},
    '골': {'EN': 'Col', 'MN': 'Кол'},
    '살전': {'EN': '1Thess', 'MN': '1Тес'},
    '살후': {'EN': '2Thess', 'MN': '2Тес'},
    '딤전': {'EN': '1Tim', 'MN': '1Тим'},
    '딤후': {'EN': '2Tim', 'MN': '2Тим'},
    '딛': {'EN': 'Titus', 'MN': 'Тит'},
    '몬': {'EN': 'Phlm', 'MN': 'Филм'},
    
    # 일반서신
    '히': {'EN': 'Heb', 'MN': 'Евр'},
    '약': {'EN': 'Jas', 'MN': 'Иак'},
    '벧전': {'EN': '1Pet', 'MN': '1Пет'},
    '벧후': {'EN': '2Pet', 'MN': '2Пет'},
    '요일': {'EN': '1John', 'MN': '1Иох'},
    '요이': {'EN': '2John', 'MN': '2Иох'},
    '요삼': {'EN': '3John', 'MN': '3Иох'},
    '유': {'EN': 'Jude', 'MN': 'Иуд'},
    
    # 예언서
    '계': {'EN': 'Rev', 'MN': 'Илч'}
}

# --- 데이터 로드 ---
def load_plan():
    file_path = os.path.join(os.path.dirname(__file__), 'bible_plan.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# --- 성경 구절 번역 함수 ---
def translate_citation(text, lang_code):
    """
    예: '마1-4' (KO) -> 'Matt 1-4' (EN) / 'Мат 1-4' (MN) 변환
    """
    if lang_code == 'KO' or not text:
        return text

    # 정규식으로 '한글성경명'과 '나머지(장절)' 분리
    match = re.match(r"([가-힣]+)\s*(.*)", text)
    
    if match:
        book_ko = match.group(1)
        numbers = match.group(2)
        
        # 사전에 있는 책이면 번역
        if book_ko in BIBLE_MAP:
            book_trans = BIBLE_MAP[book_ko].get(lang_code, book_ko)
            return f"{book_trans} {numbers}".strip()
            
    return text

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

async def broadcast_messages():
    if not TELEGRAM_TOKEN:
        print("❌ 설정 오류: TELEGRAM_TOKEN이 없습니다.")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    
    # --- [수정된 부분] 날짜 계산 로직 ---
    # GitHub 서버(UTC) 기준이 아닌 한국 시간(KST = UTC+9) 기준으로 오늘 날짜 계산
    kst_now = datetime.utcnow() + timedelta(hours=9)
    day_str = str(kst_now.day)
    # -----------------------------------
    
    # 테스트용 (필요시 주석 해제)
    # day_str = "15"

    plan = load_plan()
    
    if day_str not in plan:
        print(f"ℹ️ {day_str}일자 데이터가 없습니다.")
        return

    # JSON 원본 데이터 (한글 기준) 로드
    raw_nt, raw_ps, raw_pr, raw_qt = plan[day_str]

    print(f"🚀 {kst_now.year}-{kst_now.month}-{day_str} (KST) 발송 프로세스 시작...")

    for lang_code, chat_id in RECIPIENTS.items():
        if not chat_id:
            continue
            
        try:
            lang_pack = translations.get(lang_code, translations['KO'])
            
            # 1. 약어 번역 (예: 마 -> Matt)
            nt_trans = translate_citation(raw_nt, lang_code)
            ps_trans = translate_citation(raw_ps, lang_code) 
            pr_trans = translate_citation(raw_pr, lang_code)
            qt_trans = translate_citation(raw_qt, lang_code)

            # 2. 요약 메시지 전송
            # 날짜 표시에 now 대신 kst_now 사용
            summary_msg = (
                f"{lang_pack['title']} ({kst_now.year}/{kst_now.month}/{day_str})\n\n"
                f"{lang_pack['qt_label']}\n"
                f"👉 {qt_trans}\n\n"
                f"{lang_pack['rd_label']}\n"
                f"▫️ {lang_pack['nt']}: {nt_trans if nt_trans else lang_pack['none']}\n"
                f"▫️ {lang_pack['ps']}: {ps_trans}{lang_pack['unit_ps']}\n"
                f"▫️ {lang_pack['pr']}: {pr_trans}{lang_pack['unit_pr']}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"\"{lang_pack['slogan']}\""
            )
            
            await bot.send_message(chat_id=chat_id, text=summary_msg)
            await asyncio.sleep(0.5)

            # 3. 본문 전송 (DB에서 조회)
            # bible_common.py를 통해 해당 언어 DB에서 본문 가져오기
            
            # (A) 시편 본문
            ps_text = get_chapter_text('시', raw_ps, lang_code)
            if ps_text:
                for part in split_text_for_telegram(ps_text):
                    await bot.send_message(chat_id=chat_id, text=part)
                    await asyncio.sleep(0.3)
            
            # (B) 잠언 본문
            pr_text = get_chapter_text('잠', raw_pr, lang_code)
            if pr_text:
                for part in split_text_for_telegram(pr_text):
                    await bot.send_message(chat_id=chat_id, text=part)
                    await asyncio.sleep(0.3)

            print(f"✅ [{lang_code}] 전송 완료")
            
        except Exception as e:
            print(f"❌ [{lang_code}] 전송 실패: {e}")

if __name__ == "__main__":
    asyncio.run(broadcast_messages())