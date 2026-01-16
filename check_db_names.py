import sqlite3

def check_db_content():
    conn = sqlite3.connect('bible.db')
    cursor = conn.cursor()
    
    # 1. 존재하는 테이블 목록 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"📂 발견된 테이블: {tables}")
    
    # 2. 각 테이블별 저장된 책 이름(book) 확인
    for table in tables:
        print(f"\n--- [{table}] 테이블 내부 책 이름 목록 ---")
        try:
            # 책 이름 종류만 중복 없이 가져오기
            cursor.execute(f"SELECT DISTINCT book FROM {table}")
            books = [row[0] for row in cursor.fetchall()]
            print(books)
        except Exception as e:
            print(f"에러: {e}")

    conn.close()

if __name__ == "__main__":
    check_db_content()