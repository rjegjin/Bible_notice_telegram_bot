import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'bible.db')

def get_chapter_text(book_abbrev, chapter_str, lang_code='KO'):
    """
    DB에서 언어별(KO/EN/MN) 테이블을 조회하여 본문을 가져옵니다.
    """
    if not os.path.exists(DB_FILE):
        return None

    # [수정 1] 실제 DB에 존재하는 테이블 이름으로 연결
    # 초기 생성시 'bible'로 만들었으므로 KO는 'bible'로 매핑
    table_map = {
        'KO': 'bible_ko_KRV',
        'EN': 'bible_en_ESV',
        'MN': 'bible_mn_MUV'
    }
    
    # [수정 2] '시', '잠'을 각 DB에 저장된 실제 책 이름으로 변환 (DB Mapping)
    # * 중요: 사용자가 가진 txt 파일에 'Psalms'라고 되어 있으면 'Psalms', 'Ps'면 'Ps'로 맞춰야 함
    # 아래는 일반적인 txt 파일 기준 예시입니다.
    db_book_name_map = {
        'KO': {'시': '시', '잠': '잠'},
        'EN': {'시': 'Ps', '잠': 'Prov'},
        'MN': {'시': 'Дуу', '잠': 'Сур'}
    }

    # 출력용 제목 (헤더) 설정
    meta_info = {
        'KO': {'ver': '개역한글', 'full_name': {'시': '시편', '잠': '잠언'}},
        'EN': {'ver': 'ESV',      'full_name': {'시': 'Psalms', '잠': 'Proverbs'}},
        'MN': {'ver': 'MUV',      'full_name': {'시': 'Дуулал', '잠': 'Сургаалт үгс'}}
    }

    target_table = table_map.get(lang_code, 'bible_ko_KRV')
    
    # 해당 언어의 매핑이 없으면 기본값(한글) 사용
    lang_map = db_book_name_map.get(lang_code, db_book_name_map['KO'])
    # DB 검색용 책 이름 (예: '시' -> 'Psalms')
    search_book_name = lang_map.get(book_abbrev, book_abbrev)

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 테이블 존재 여부 확인
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{target_table}'")
        if not cursor.fetchone():
            conn.close()
            return None 

        # 3. 쿼리 실행 (search_book_name 사용)
        chapter = int(chapter_str)
        
        # SQL: book 컬럼이 'Psalms'이고 chapter가 '1'인 것 조회
        sql = f"SELECT verse, content FROM {target_table} WHERE book=? AND chapter=? ORDER BY verse ASC"
        cursor.execute(sql, (search_book_name, chapter))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            # 디버깅용 로그 (나중에 삭제 가능)
            print(f"⚠️ 데이터 없음: {lang_code} 테이블({target_table})에서 책='{search_book_name}', 장='{chapter}' 검색 실패")
            return None

        # 4. 결과 포맷팅
        info = meta_info.get(lang_code, meta_info['KO'])
        display_book_name = info['full_name'].get(book_abbrev, book_abbrev)
        version_name = info['ver']
        
        lines = [f"({display_book_name} {chapter} / {version_name})"]
        for verse, content in rows:
            lines.append(f"{verse}. {content}")
        
        return "\n".join(lines)

    except Exception as e:
        print(f"⚠️ DB Error ({lang_code}): {e}")
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