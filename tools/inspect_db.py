import sqlite3
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == 'tools':
    BASE_DIR = os.path.dirname(current_dir)
else:
    BASE_DIR = current_dir
DB_FILE = os.path.join(BASE_DIR, 'bible.db')

def inspect():
    if not os.path.exists(DB_FILE):
        print(f"❌ DB 파일이 없습니다: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"🔍 DB 검사: {DB_FILE}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print("   ⚠️ 테이블이 없습니다.")
        return

    for table in tables:
        print(f"\n📂 테이블: [{table}]")
        
        # 행 개수
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   - 총 구절 수: {count}")
        
        # 책 목록
        try:
            cursor.execute(f"SELECT DISTINCT book FROM {table}")
            books = [row[0] for row in cursor.fetchall()]
            print(f"   - 포함된 책({len(books)}권): {', '.join(books)}")
        except:
            print("   - 책 목록 조회 실패")

    conn.close()

if __name__ == "__main__":
    inspect()