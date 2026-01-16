import os
import sqlite3
import re
from bs4 import BeautifulSoup, NavigableString

# --- 설정 ---
# [수정됨] 사용자 경로 적용 (경로 앞의 r은 필수입니다)
SOURCE_DIR = r"C:\Users\rjegj\OneDrive\Basic life\성경역본\mn_new"
DB_FILE = 'bible.db'
LANG_TABLE = 'bible_mn'

# 01~66 폴더 매핑
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

def update_mn_db():
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 오류: '{SOURCE_DIR}' 폴더가 없습니다. 경로를 확인해주세요.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 테이블 생성 및 초기화
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {LANG_TABLE} (
            book TEXT, chapter INTEGER, verse INTEGER, content TEXT
        )
    ''')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{LANG_TABLE} ON {LANG_TABLE} (book, chapter, verse)')
    
    # [선택] 기존 데이터 삭제 후 다시 넣기 (중복 방지)
    cursor.execute(f"DELETE FROM {LANG_TABLE}")
    print("🧹 기존 몽골어 데이터를 초기화했습니다.")

    print("🚀 몽골어 성경 데이터 통합 시작...")
    
    data_to_insert = []
    folders = sorted([d for d in os.listdir(SOURCE_DIR) if d in MN_BOOK_MAP])
    
    for foldername in folders:
        book_abbrev = MN_BOOK_MAP[foldername]
        folder_path = os.path.join(SOURCE_DIR, foldername)
        
        # 파일 정렬
        files = [f for f in os.listdir(folder_path) if f.endswith(('.htm', '.html'))]
        # 숫자 기준 정렬 (1.htm, 2.htm ...)
        files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
        
        print(f"   📂 {foldername} -> {book_abbrev} 처리 중...")

        for filename in files:
            try:
                chapter_num = int(re.search(r'\d+', filename).group())
                file_path = os.path.join(folder_path, filename)
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    
                    # --- [핵심 수정] WordProject 스타일 파싱 로직 ---
                    # 1. <span class="verse"> 태그를 우선 탐색
                    verse_spans = soup.find_all('span', class_='verse')
                    
                    if verse_spans:
                        # Case A: <span class="verse">1</span> 본문... 형식
                        for span in verse_spans:
                            try:
                                verse_num = int(span.get_text().strip())
                                content = ""
                                # span 바로 뒤에 있는 형제 노드들(텍스트)을 긁어모음
                                sibling = span.next_sibling
                                while sibling:
                                    # 다음 절(span class='verse')이 나오면 중단
                                    if sibling.name == 'span' and 'verse' in sibling.get('class', []):
                                        break
                                    
                                    if isinstance(sibling, NavigableString):
                                        content += str(sibling)
                                    elif sibling.name != 'script': # script 태그 등 제외
                                        content += sibling.get_text()
                                    
                                    sibling = sibling.next_sibling
                                
                                content = content.strip()
                                if content:
                                    data_to_insert.append((book_abbrev, chapter_num, verse_num, content))
                            except ValueError:
                                continue

                    else:
                        # Case B: 기존 로직 (<p><b>1</b> 본문...) - 예비용
                        for p in soup.find_all('p'):
                            b_tag = p.find('b')
                            if b_tag:
                                try:
                                    verse_num = int(b_tag.get_text().strip())
                                    b_tag.extract() # 태그 제거
                                    content = p.get_text().strip()
                                    if content:
                                        data_to_insert.append((book_abbrev, chapter_num, verse_num, content))
                                except:
                                    continue

            except Exception as e:
                # print(f"에러: {e}") # 디버깅 필요시 주석 해제
                continue

    if data_to_insert:
        cursor.executemany(f'INSERT INTO {LANG_TABLE} VALUES (?,?,?,?)', data_to_insert)
        conn.commit()
        print(f"\n🎉 대성공! 총 {len(data_to_insert)}개 구절이 '{LANG_TABLE}'에 저장되었습니다.")
    else:
        print("\n⚠️ 여전히 데이터를 찾지 못했습니다. HTML 구조가 예상과 다릅니다.")
    
    conn.close()

if __name__ == "__main__":
    update_mn_db()