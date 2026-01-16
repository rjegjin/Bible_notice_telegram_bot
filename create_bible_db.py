import sqlite3
import re
import os

# --- 설정 ---
TXT_FILE = '개역한글판성경.txt'
DB_FILE = 'bible.db'

def create_db():
    if not os.path.exists(TXT_FILE):
        print(f"❌ 오류: '{TXT_FILE}' 파일을 찾을 수 없습니다.")
        return

    # 기존 DB가 있다면 삭제하고 새로 생성 (초기화)
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 테이블 생성 (책, 장, 절, 본문)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bible (
            book TEXT,
            chapter INTEGER,
            verse INTEGER,
            content TEXT
        )
    ''')
    # 검색 속도를 위한 인덱스 생성
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bible ON bible (book, chapter, verse)')

    print("📖 텍스트 파일 읽는 중...")
    
    # 정규표현식: "창1:1 태초에..." 또는 "시23:1 여호와는..."
    # 패턴: (책이름)(장):(절) (본문)
    pattern = re.compile(r"^([가-힣]+)(\d+):(\d+)\s+(.+)")

    count = 0
    data_to_insert = []

    # [수정된 부분] encoding='utf-8' -> 'cp949'로 변경
    try:
        f = open(TXT_FILE, 'r', encoding='cp949')
    except:
        # 만약 cp949도 아니면 utf-8-sig 등으로 재시도 (안전장치)
        f = open(TXT_FILE, 'r', encoding='utf-8-sig')

    with f:
        for line in f:
            line = line.strip()
            if not line: continue

            match = pattern.match(line)
            if match:
                book, chapter, verse, content = match.groups()
                data_to_insert.append((book, int(chapter), int(verse), content))
                count += 1
            
            # 1000개 단위로 커밋 (속도 향상)
            if len(data_to_insert) >= 1000:
                cursor.executemany('INSERT INTO bible VALUES (?,?,?,?)', data_to_insert)
                data_to_insert = []

    # 남은 데이터 저장
    if data_to_insert:
        cursor.executemany('INSERT INTO bible VALUES (?,?,?,?)', data_to_insert)

    conn.commit()
    conn.close()
    
    print(f"✅ 변환 완료! 총 {count}개 구절이 '{DB_FILE}'에 저장되었습니다.")

if __name__ == "__main__":
    create_db()