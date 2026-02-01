import os
import re
from bs4 import BeautifulSoup, NavigableString

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================

# 프로젝트 루트 경로 (결과 파일 저장 위치)
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == 'tools':
    BASE_DIR = os.path.dirname(current_dir)
else:
    BASE_DIR = current_dir
OUTPUT_FILE = os.path.join(BASE_DIR, 'bible_mn_MUV.txt')

# 몽골어 성경 원본 폴더 (build_bible_db.py와 동일)
SOURCE_DIR = r"C:\Users\rjegj\OneDrive\Basic life\성경역본\mn_new"

# 책 이름 매핑
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

def convert():
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 폴더 없음: {SOURCE_DIR}")
        return

    print(f"🚀 몽골어 HTML -> TXT 변환 시작...")
    print(f"   원본: {SOURCE_DIR}")
    print(f"   대상: {OUTPUT_FILE}")

    folders = sorted([d for d in os.listdir(SOURCE_DIR) if d in MN_BOOK_MAP])
    total_verses = 0

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for foldername in folders:
            book_abbrev = MN_BOOK_MAP[foldername]
            folder_path = os.path.join(SOURCE_DIR, foldername)
            
            # 파일 정렬 (숫자 기준)
            files = [f for f in os.listdir(folder_path) if f.endswith(('.htm', '.html'))]
            files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
            
            print(f"   📂 {foldername} -> {book_abbrev} ({len(files)} chapters)")

            for filename in files:
                try:
                    chapter_num = int(re.search(r'\d+', filename).group())
                    file_path = os.path.join(folder_path, filename)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                        soup = BeautifulSoup(f_in, 'html.parser')
                        
                        # WordProject 스타일 파싱 (build_bible_db.py와 동일 로직)
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
                                    
                                    content = content.strip()
                                    if content:
                                        # TXT 포맷: 책이름 장:절 본문
                                        # 예: Эхл 1:1 태초에...
                                        line = f"{book_abbrev} {chapter_num}:{verse_num} {content}\n"
                                        f_out.write(line)
                                        total_verses += 1
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
                                            line = f"{book_abbrev} {chapter_num}:{verse_num} {content}\n"
                                            f_out.write(line)
                                            total_verses += 1
                                    except:
                                        continue
                except Exception as e:
                    print(f"⚠️ 에러 ({filename}): {e}")

    print(f"\n✅ 변환 완료! 총 {total_verses}개 구절이 저장되었습니다.")
    print(f"👉 파일 위치: {OUTPUT_FILE}")

if __name__ == "__main__":
    convert()