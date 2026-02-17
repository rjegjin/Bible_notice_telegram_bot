import sqlite3
import os
import re

# DB 파일 경로
DB_FILE = os.path.join(os.path.dirname(__file__), 'bible.db')

# --- [이동] 성경 약어 매핑 (이곳에서 통합 관리해야 QT 파싱 때 씁니다) ---
BIBLE_MAP = {
    '창': {'EN': 'Gen', 'MN': 'Эхл'}, '출': {'EN': 'Exod', 'MN': 'Гэт'},
    '레': {'EN': 'Lev', 'MN': 'Лев'}, '민': {'EN': 'Num', 'MN': 'Тоо'},
    '신': {'EN': 'Deut', 'MN': 'Дэд'}, '수': {'EN': 'Josh', 'MN': 'Иош'},
    '삿': {'EN': 'Judg', 'MN': 'Шүү'}, '룻': {'EN': 'Ruth', 'MN': 'Рут'},
    '삼상': {'EN': '1Sam', 'MN': '1Сам'}, '삼하': {'EN': '2Sam', 'MN': '2Сам'},
    '왕상': {'EN': '1Kgs', 'MN': '1Хаа'}, '왕하': {'EN': '2Kgs', 'MN': '2Хаа'},
    '대상': {'EN': '1Chr', 'MN': '1Шас'}, '대하': {'EN': '2Chr', 'MN': '2Шас'},
    '스': {'EN': 'Ezra', 'MN': 'Езр'}, '느': {'EN': 'Neh', 'MN': 'Нех'},
    '에': {'EN': 'Esth', 'MN': 'Ест'}, '욥': {'EN': 'Job', 'MN': 'Иов'},
    '시': {'EN': 'Ps', 'MN': 'Дуу'}, '잠': {'EN': 'Prov', 'MN': 'Сур'},
    '전': {'EN': 'Eccl', 'MN': 'Ном'}, '아': {'EN': 'Song', 'MN': 'Доо'},
    '사': {'EN': 'Isa', 'MN': 'Иса'}, '렘': {'EN': 'Jer', 'MN': 'Иер'},
    '애': {'EN': 'Lam', 'MN': 'Гаш'}, '겔': {'EN': 'Ezek', 'MN': 'Езе'},
    '단': {'EN': 'Dan', 'MN': 'Дан'}, '호': {'EN': 'Hos', 'MN': 'Хос'},
    '욜': {'EN': 'Joel', 'MN': 'Иое'}, '암': {'EN': 'Amos', 'MN': 'Амо'},
    '옵': {'EN': 'Obad', 'MN': 'Оба'}, '욘': {'EN': 'Jonah', 'MN': 'Ион'},
    '미': {'EN': 'Mic', 'MN': 'Мик'}, '나': {'EN': 'Nah', 'MN': 'Нах'},
    '합': {'EN': 'Hab', 'MN': 'Хаб'}, '습': {'EN': 'Zeph', 'MN': 'Зеф'},
    '학': {'EN': 'Hag', 'MN': 'Хаг'}, '슥': {'EN': 'Zech', 'MN': 'Зех'},
    '말': {'EN': 'Mal', 'MN': 'Мал'},
    '마': {'EN': 'Matt', 'MN': 'Мат'}, '막': {'EN': 'Mark', 'MN': 'Марк'},
    '눅': {'EN': 'Luke', 'MN': 'Лук'}, '요': {'EN': 'John', 'MN': 'Иох'},
    '행': {'EN': 'Acts', 'MN': 'Үйл'}, '롬': {'EN': 'Rom', 'MN': 'Ром'},
    '고전': {'EN': '1Cor', 'MN': '1Кор'}, '고후': {'EN': '2Cor', 'MN': '2Кор'},
    '갈': {'EN': 'Gal', 'MN': 'Гал'}, '엡': {'EN': 'Eph', 'MN': 'Еф'},
    '빌': {'EN': 'Phil', 'MN': 'Фил'}, '골': {'EN': 'Col', 'MN': 'Кол'},
    '살전': {'EN': '1Thess', 'MN': '1Тес'}, '살후': {'EN': '2Thess', 'MN': '2Тес'},
    '딤전': {'EN': '1Tim', 'MN': '1Тим'}, '딤후': {'EN': '2Tim', 'MN': '2Тим'},
    '딛': {'EN': 'Titus', 'MN': 'Тит'}, '몬': {'EN': 'Phlm', 'MN': 'Филм'},
    '히': {'EN': 'Heb', 'MN': 'Евр'}, '약': {'EN': 'Jas', 'MN': 'Иак'},
    '벧전': {'EN': '1Pet', 'MN': '1Пет'}, '벧후': {'EN': '2Pet', 'MN': '2Пет'},
    '요일': {'EN': '1John', 'MN': '1Иох'}, '요이': {'EN': '2John', 'MN': '2Иох'},
    '요삼': {'EN': '3John', 'MN': '3Иох'}, '유': {'EN': 'Jude', 'MN': 'Иуд'},
    '계': {'EN': 'Rev', 'MN': 'Илч'}
}

# 테이블 및 버전 정보 매핑 (공통 사용)
TABLE_MAP = {'KO': 'bible_ko_KRV', 'EN': 'bible_en_ESV', 'MN': 'bible_mn_MUV'}
META_INFO = {
    'KO': {'ver': '개역한글'}, 'EN': {'ver': 'ESV'}, 'MN': {'ver': 'Ariun Bibl'}
}

def translate_citation(text, lang_code):
    """한글 약어(예: 마1-4)를 타 언어(Matt 1-4)로 변환 (표시용)"""
    if lang_code == 'KO' or not text: return text
    match = re.match(r"([가-힣]+)\s*(.*)", text)
    if match:
        book_ko = match.group(1)
        rest = match.group(2)
        if book_ko in BIBLE_MAP:
            book_trans = BIBLE_MAP[book_ko].get(lang_code, book_ko)
            return f"{book_trans} {rest}".strip()
    return text

def get_chapter_text(book_abbrev, chapter_str, lang_code='KO'):
    """(기존 기능) 시편/잠언처럼 '장' 전체를 가져올 때 사용"""
    if not os.path.exists(DB_FILE): return None
    
    # DB 검색용 이름 변환 (시->Psalms 등)
    # 몽골어/영어 DB에 저장된 실제 책 이름으로 매핑
    search_book = book_abbrev
    if lang_code != 'KO' and book_abbrev in BIBLE_MAP:
        search_book = BIBLE_MAP[book_abbrev].get(lang_code, book_abbrev)

    target_table = TABLE_MAP.get(lang_code, TABLE_MAP['KO'])

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            sql = f"SELECT verse, content FROM {target_table} WHERE book=? AND chapter=? ORDER BY verse ASC"
            cursor.execute(sql, (search_book, int(chapter_str)))
            rows = cursor.fetchall()
            
            if not rows: return None

            ver_name = META_INFO[lang_code]['ver']
            lines = [f"({search_book} {chapter_str} / {ver_name})"]
            for v, c in rows:
                lines.append(f"{v}. {c}")
            return "\n".join(lines)
    except Exception:
        return None

def get_qt_text(citation_str, lang_code='KO'):
    """
    [신규 기능] '삼상 8:1-22' 같은 문자열을 파싱해서 해당 범위의 본문을 가져옵니다.
    """
    if not os.path.exists(DB_FILE) or not citation_str: return None

    # 1. 파싱: "삼상", "8", "1", "22" 분리
    # 정규식 패턴: (책이름) (장):(시작절)-(끝절) 또는 (책이름) (장)
    pattern = r"([가-힣]+)\s*(\d+)[:장]?\s*(\d+)?[-~]?(\d+)?"
    match = re.search(pattern, citation_str)
    
    if not match: return None
    
    book_ko, chapter, start_v, end_v = match.groups()
    chapter = int(chapter)
    
    # 2. 언어별 책 이름 변환 (DB 검색용)
    search_book = book_ko
    if lang_code != 'KO' and book_ko in BIBLE_MAP:
        search_book = BIBLE_MAP[book_ko].get(lang_code, book_ko)
        
    target_table = TABLE_MAP.get(lang_code, TABLE_MAP['KO'])

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # 3. 쿼리 생성
            if start_v and end_v: # 범위 검색 (예: 1-22)
                sql = f"SELECT verse, content FROM {target_table} WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse ASC"
                cursor.execute(sql, (search_book, chapter, int(start_v), int(end_v)))
            elif start_v: # 시작절만 있는 경우 (예: 1절만)
                sql = f"SELECT verse, content FROM {target_table} WHERE book=? AND chapter=? AND verse=? ORDER BY verse ASC"
                cursor.execute(sql, (search_book, chapter, int(start_v)))
            else: # 장 전체 (예: 잠언 14장)
                sql = f"SELECT verse, content FROM {target_table} WHERE book=? AND chapter=? ORDER BY verse ASC"
                cursor.execute(sql, (search_book, chapter))
            
            rows = cursor.fetchall()
            if not rows: return None

            # 4. 결과 포맷팅
            ver_name = META_INFO[lang_code]['ver']
            # 표시용 범위 문자열 (예: 8:1-22)
            range_str = f"{chapter}"
            if start_v: range_str += f":{start_v}"
            if end_v: range_str += f"-{end_v}"

            lines = [f"({search_book} {range_str} / {ver_name})"]
            for v, c in rows:
                lines.append(f"{v}. {c}")
            
            return "\n".join(lines)

    except Exception as e:
        print(f"⚠️ QT Error ({lang_code}): {e}")
        return None

def split_text_for_telegram(text, limit=4000):
    if not text: return []
    if len(text) <= limit: return [text]
    parts = []
    while len(text) > limit:
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1: split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].strip()
    if text: parts.append(text)
    return parts