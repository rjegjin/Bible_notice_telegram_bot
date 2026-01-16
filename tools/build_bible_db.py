import os
import sqlite3
import re
import sys
from bs4 import BeautifulSoup, NavigableString

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================

# 프로젝트 루트 및 DB 경로
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'bible.db')

# 몽골어 성경 폴더 경로 (사용자 환경에 맞게 수정)
MN_SOURCE_DIR = r"C:\Users\rjegj\OneDrive\Basic life\성경역본\mn_new"

# 몽골어 책 이름 매핑 (폴더명 -> DB저장명)
MN_BOOK_MAP = {
    "01": "Эхл", "02": "Гэт", "03": "Лев", "04": "Тоо", "05": "Дэд",
    "06": "Иош", "07": "Шүү", "08": "Рут", "09": "1Сам", "10": "2Сам",
    "11": "1Хаа", "12": "2Хаа", "13": "1Шас", "14": "2Шас", "15": "Езр",
    "16": "Нех", "17": "Ест", "18": "Иов", "19": "Дуу", "20": "Сур",
    "21": "Ном", "22": "Доо", "23": "Иса", "24": "Иер", "25": "Гаш",
    "26": "Езе", "27": "Дан", "28": "Хос", "29": "Иое", "30": "Амо",
    "31": "Оба", "32": "Ион", "33": "Мик", "34": "Нах", "35": "Хаб",
    "36": "Зеф", "37": "Хаг", "38": "Зех", "39": "Мал",
    "40": "Мат", "41": "Марк", "42": "Лук", "43": "Иох", "44": "Үйл",
    "45": "Ром", "46": "1Кор", "47": "2Кор", "48": "Гал", "49": "Еф",
    "50": "Фил", "51": "Кол", "52": "1Тес", "53": "2Тес", "54": "1Тим",
    "55": "2Тим", "56": "Тит", "57": "Филм", "58": "Евр", "59": "Иак",
    "60": "1Пет", "61": "2Пет", "62": "1Иох", "63": "2Иох", "64": "3Иох",
    "65": "Иуд", "66": "Илч"
}

# ==========================================
# 🛠️ 핵심 클래스 (Core Classes)
# ==========================================

class BibleDB:
    """데이터베이스 연결 및 테이블 관리를 담당하는 클래스"""
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print("🔒 DB 연결 종료")

    def reset_table(self, table_name):
        """테이블을 삭제하고 재생성"""
        print(f"\n🧹 [{table_name}] 테이블 초기화 중...")
        self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.cursor.execute(f'''
            CREATE TABLE {table_name} (
                book TEXT,
                chapter INTEGER,
                verse INTEGER,
                content TEXT
            )
        ''')
        self.cursor.execute(f'CREATE INDEX idx_{table_name} ON {table_name} (book, chapter, verse)')

    def insert_data(self, table_name, data_list):
        """데이터 일괄 삽입"""
        if not data_list:
            print(f"⚠️ [{table_name}] 삽입할 데이터가 없습니다.")
            return
        
        self.cursor.executemany(f'INSERT INTO {table_name} VALUES (?,?,?,?)', data_list)
        self.conn.commit()
        print(f"✅ [{table_name}] {len(data_list)}개 구절 저장 완료")

    def clean_unused_tables(self, keep_tables):
        """지정된 테이블 외의 모든 테이블 삭제 (청소)"""
        print("\n🧹 DB 청소(불필요한 테이블 삭제) 시작...")
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in self.cursor.fetchall()]
        
        count = 0
        for table in all_tables:
            # sqlite 내부 테이블이나 유지할 테이블은 삭제하지 않음
            if table not in keep_tables and not table.startswith('sqlite_'):
                self.cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"   🗑️ 삭제됨: {table}")
                count += 1
        
        if count == 0:
            print("   ✨ 삭제할 불필요한 테이블이 없습니다.")
        else:
            self.conn.commit()
            print(f"   ✅ 총 {count}개의 구형 테이블을 정리했습니다.")

class TextImporter:
    """텍스트 파일(.txt) 기반 성경 파서 (한글, 영어 등)"""
    def __init__(self, file_path, encoding, pattern):
        self.file_path = file_path
        self.encoding = encoding
        self.pattern = pattern

    def parse(self):
        if not os.path.exists(self.file_path):
            print(f"❌ 파일 없음: {self.file_path}")
            return []

        print(f"📖 파일 읽는 중: {os.path.basename(self.file_path)}")
        data = []
        
        try:
            f = open(self.file_path, 'r', encoding=self.encoding)
        except:
            print(f"⚠️ {self.encoding} 인코딩 실패, utf-8-sig로 재시도...")
            f = open(self.file_path, 'r', encoding='utf-8-sig')

        with f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                match = self.pattern.match(line)
                if match:
                    book, ch, v, content = match.groups()
                    data.append((book.strip(), int(ch), int(v), content.strip()))
        
        return data


class HtmlImporter:
    """HTML 파일 폴더 기반 성경 파서 (몽골어 등)"""
    def __init__(self, source_dir, book_map):
        self.source_dir = source_dir
        self.book_map = book_map

    def parse(self):
        if not os.path.exists(self.source_dir):
            print(f"❌ 폴더 없음: {self.source_dir}")
            return []

        print(f"🚀 HTML 파싱 시작: {self.source_dir}")
        data = []
        folders = sorted([d for d in os.listdir(self.source_dir) if d in self.book_map])

        for foldername in folders:
            book_abbrev = self.book_map[foldername]
            folder_path = os.path.join(self.source_dir, foldername)
            
            # 파일 정렬 (숫자 기준)
            files = [f for f in os.listdir(folder_path) if f.endswith(('.htm', '.html'))]
            files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
            
            print(f"   📂 {foldername} -> {book_abbrev} ({len(files)} chapters)")

            for filename in files:
                self._parse_file(folder_path, filename, book_abbrev, data)
        
        return data

    def _parse_file(self, folder_path, filename, book_abbrev, data_list):
        try:
            chapter_num = int(re.search(r'\d+', filename).group())
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                
                # WordProject 스타일 파싱
                verse_spans = soup.find_all('span', class_='verse')
                
                if verse_spans:
                    for span in verse_spans:
                        try:
                            verse_num = int(span.get_text().strip())
                            content = ""
                            sibling = span.next_sibling
                            while sibling:
                                if sibling.name == 'span' and 'verse' in sibling.get('class', []):
                                    break
                                if isinstance(sibling, NavigableString):
                                    content += str(sibling)
                                elif sibling.name != 'script':
                                    content += sibling.get_text()
                                sibling = sibling.next_sibling
                            
                            if content.strip():
                                data_list.append((book_abbrev, chapter_num, verse_num, content.strip()))
                        except ValueError:
                            continue
                else:
                    # Fallback logic
                    for p in soup.find_all('p'):
                        b_tag = p.find('b')
                        if b_tag:
                            try:
                                verse_num = int(b_tag.get_text().strip())
                                b_tag.extract()
                                content = p.get_text().strip()
                                if content:
                                    data_list.append((book_abbrev, chapter_num, verse_num, content))
                            except:
                                continue
        except Exception as e:
            pass

# ==========================================
# 🚀 메인 실행 로직 (Main Execution)
# ==========================================

def run():
    db = BibleDB(DB_FILE)
    db.connect()

    while True:
        print("\n" + "="*40)
        print("      ✝️  Bible DB Builder Tool")
        print("="*40)
        print("1. [전체] 모든 언어 DB 생성 (TXT 기반)")
        print("2. [한글] 개역한글 (bible_ko_KRV)")
        print("3. [영어] ESV (bible_en_ESV)")
        print("4. [몽골] MUV (bible_mn_MUV - TXT)")
        print("5. [정리] 미사용 구형 테이블 삭제")
        print("6. [몽골] MUV (HTML 원본 폴더 파싱 - 느림)")
        print("0. 종료")
        print("="*40)
        
        choice = input("선택 > ").strip()

        if choice == '0':
            break

        # --- 1. 한글 (Text) ---
        if choice in ['1', '2']:
            importer = TextImporter(
                file_path=os.path.join(BASE_DIR, '개역한글판성경.txt'),
                encoding='cp949',
                pattern=re.compile(r"^([가-힣]+)(\d+):(\d+)\s+(.+)")
            )
            data = importer.parse()
            db.reset_table('bible_ko_KRV')
            db.insert_data('bible_ko_KRV', data)

        # --- 2. 영어 (Text) ---
        if choice in ['1', '3']:
            importer = TextImporter(
                file_path=os.path.join(BASE_DIR, 'ESV.txt'),
                encoding='utf-8',
                # [수정] 숫자로 시작하는 책 이름(1 Kings 등)도 허용하는 패턴으로 변경
                pattern=re.compile(r"^(.+?)\s*(\d+):(\d+)\s+(.+)")
            )
            data = importer.parse()
            db.reset_table('bible_en_ESV')
            db.insert_data('bible_en_ESV', data)

        # --- 3. 몽골어 (TXT) ---
        if choice in ['1', '4']:
            importer = TextImporter(
                file_path=os.path.join(BASE_DIR, 'bible_mn_MUV.txt'),
                encoding='utf-8',
                # [패턴] 책이름 장:절 본문 (예: Эхл 1:1 ...)
                pattern=re.compile(r"^(.+?)\s*(\d+):(\d+)\s+(.+)")
            )
            data = importer.parse()
            db.reset_table('bible_mn_MUV')
            db.insert_data('bible_mn_MUV', data)

        # --- 6. 몽골어 (HTML) ---
        if choice == '6':
            importer = HtmlImporter(
                source_dir=MN_SOURCE_DIR,
                book_map=MN_BOOK_MAP
            )
            data = importer.parse()
            db.reset_table('bible_mn_MUV')
            db.insert_data('bible_mn_MUV', data)

        # --- 5. 정리 (Cleanup) ---
        if choice == '5':
            active_tables = ['bible_ko_KRV', 'bible_en_ESV', 'bible_mn_MUV']
            db.clean_unused_tables(active_tables)

    db.close()
    print("\n👋 프로그램을 종료합니다.")

if __name__ == "__main__":
    run()