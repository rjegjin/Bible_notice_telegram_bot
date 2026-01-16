import sqlite3
import re
import os

# --- 설정 ---
# 1. 추가할 파일명 (예: bible_en.txt)
TXT_FILE = 'ESV.txt' 
# 2. 저장할 테이블 이름 (영어: bible_en, 몽골어: bible_mn)
LANG_TABLE = 'bible_en' 

DB_FILE = 'bible.db'

def add_language_to_db():
    if not os.path.exists(TXT_FILE):
        print(f"❌ '{TXT_FILE}' 파일이 없습니다.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 테이블 생성 (테이블 이름이 동적이므로 f-string 사용)
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {LANG_TABLE} (
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            content TEXT
        )
    ''')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{LANG_TABLE} ON {LANG_TABLE} (book, chapter, verse)')

    print(f"📖 {TXT_FILE} 읽는 중...")
    
    # [주의] 외국어 성경 포맷에 맞춰 정규식 수정 필요할 수 있음
    # 예: "Gen 1:1 In the beginning..." -> r"^([A-Za-z\s]+)(\d+):(\d+)\s+(.+)"
    # 현재는 한국어 txt와 같은 포맷이라고 가정:
    pattern = re.compile(r"^([^\d]+)(\d+):(\d+)\s+(.+)")

    data = []
    with open(TXT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                book, ch, v, content = match.groups()
                # 약어 통일 작업 필요 (예: Gen -> 창, 혹은 Gen 그대로 쓰고 매핑)
                # 여기서는 일단 그대로 넣습니다.
                data.append((book.strip(), int(ch), int(v), content))

    if data:
        cursor.executemany(f'INSERT INTO {LANG_TABLE} VALUES (?,?,?,?)', data)
        conn.commit()
        print(f"✅ {len(data)}개 구절이 '{LANG_TABLE}' 테이블에 추가되었습니다.")
    else:
        print("⚠️ 데이터를 찾지 못했습니다. 텍스트 파일 형식을 확인하세요.")

    conn.close()

if __name__ == "__main__":
    add_language_to_db()