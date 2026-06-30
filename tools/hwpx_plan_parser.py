import glob
import os
import re
import xml.etree.ElementTree as ET
import zipfile

from core.bible_scripture_resolver import BIBLE_MAP

HWPX_NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}

FULL_TO_ABBR = {
    "시편": "시", "잠언": "잠", "마태복음": "마", "마가복음": "막", "누가복음": "눅",
    "요한복음": "요", "사도행전": "행", "로마서": "롬", "고린도전서": "고전",
    "고린도후서": "고후", "갈라디아서": "갈", "에베소서": "엡", "빌립보서": "빌",
    "골로새서": "골", "데살로니가전서": "살전", "데살로니가후서": "살후",
    "디모데전서": "딤전", "디모데후서": "딤후", "디도서": "딛", "빌레몬서": "몬",
    "히브리서": "히", "야고보서": "약", "베드로전서": "벧전", "베드로후서": "벧후",
    "요한일서": "요일", "요한이서": "요이", "요한삼서": "요삼", "유다서": "유",
    "요한계시록": "계", "창세기": "창", "출애굽기": "출", "레위기": "레",
    "민수기": "민", "신명기": "신", "여호수아": "수", "사사기": "삿", "룻기": "룻",
    "사무엘상": "삼상", "사무엘하": "삼하", "열왕기상": "왕상", "열왕기하": "왕하",
    "역대상": "대상", "역대하": "대하", "에스라": "스", "느헤미야": "느",
    "에스더": "에", "욥기": "욥", "전도서": "전", "아가": "아", "이사야": "사",
    "예레미야": "렘", "예레미야애가": "애", "애가": "애", "에스겔": "겔",
    "다니엘": "단", "호세아": "호", "요엘": "욜", "아모스": "암", "오바댜": "옵",
    "요나": "욘", "미가": "미", "나훔": "나", "하박국": "합", "스바냐": "습",
    "학개": "학", "스가랴": "슥", "말라기": "말",
}

BOOK_PATTERN = re.compile(
    r"(" + "|".join(sorted((re.escape(book) for book in BIBLE_MAP.keys()), key=len, reverse=True)) + r")(?=\d)"
)


def find_hwpx_file(assets_dir, year, month, prefix):
    year_str = str(int(year))
    month_pad = f"{int(month):02d}"
    month_plain = str(int(month))

    patterns = [
        f"{year_str}년_{month_pad}월_{prefix}_passage*.hwpx",
        f"{year_str}년_{month_plain}월_{prefix}_passage*.hwpx",
        f"{year_str}년_{month_pad}월 {prefix}_passage*.hwpx",
        f"{year_str}년_{month_plain}월 {prefix}_passage*.hwpx",
        f"{year_str}년_{month_pad}월*{prefix}*passage*.hwpx",
        f"{year_str}년_{month_plain}월*{prefix}*passage*.hwpx",
    ]

    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(assets_dir, pattern)))
        if matches:
            return matches[0]
    return None


def find_hwpx_sources(assets_dir, year, month):
    return {
        "BR": find_hwpx_file(assets_dir, year, month, "BR"),
        "QT": find_hwpx_file(assets_dir, year, month, "QT"),
    }


def _extract_cell_text(cell):
    parts = []
    for text_node in cell.findall(".//hp:t", HWPX_NS):
        text = "".join(text_node.itertext()).strip()
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _load_section_rows(hwpx_path):
    rows = {}
    with zipfile.ZipFile(hwpx_path) as archive:
        section_names = [name for name in archive.namelist() if re.fullmatch(r"Contents/section\d+\.xml", name)]
        for section_name in sorted(section_names):
            root = ET.fromstring(archive.read(section_name))
            for cell in root.findall(".//hp:tc", HWPX_NS):
                addr = cell.find("hp:cellAddr", HWPX_NS)
                if addr is None:
                    continue
                row_addr = int(addr.attrib["rowAddr"])
                col_addr = int(addr.attrib["colAddr"])
                rows.setdefault(row_addr, {})[col_addr] = _extract_cell_text(cell)
    return rows


def _normalize_text(text):
    text = (text or "").strip()
    if not text:
        return ""
    text = text.replace("–", "-").replace("—", "-").replace("〜", "-")
    for full, abbr in sorted(FULL_TO_ABBR.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(full, abbr)
    text = BOOK_PATTERN.sub(r"\1 ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_ps_pr(text, prefix):
    text = _normalize_text(text)
    if not text:
        return ""
    return text if text.startswith(prefix) else f"{prefix} {text}"


def parse_br_hwpx(hwpx_path):
    rows = _load_section_rows(hwpx_path)
    plan = {}

    for row_idx in sorted(rows):
        row = rows[row_idx]
        for base in (0, 7):
            day = str(row.get(base, "")).strip()
            if not day.isdigit():
                continue

            plan[day] = [
                _normalize_text(row.get(base + 3, "")),
                _normalize_text(row.get(base + 4, "")),
                _normalize_ps_pr(row.get(base + 5, ""), "시"),
                _normalize_ps_pr(row.get(base + 6, ""), "잠"),
            ]

    return plan


def _looks_like_date_row(values):
    digit_count = 0
    for value in values:
        value = str(value).strip()
        if not value:
            continue
        if not value.isdigit():
            return False
        digit_count += 1
    return digit_count > 0


def parse_qt_hwpx(hwpx_path):
    rows = _load_section_rows(hwpx_path)
    plan = {}

    sorted_rows = sorted(rows)
    for index, row_idx in enumerate(sorted_rows[:-1]):
        date_row = rows[row_idx]
        passage_row = rows[sorted_rows[index + 1]]

        date_values = [str(date_row.get(col, "")).strip() for col in range(7)]
        if not _looks_like_date_row(date_values):
            continue

        passage_values = [str(passage_row.get(col, "")).strip() for col in range(7)]
        for day, passage in zip(date_values, passage_values):
            if day.isdigit():
                plan[day] = _normalize_text(passage)

    return plan


def merge_monthly_plan(br_plan=None, qt_plan=None, fallback_plan=None):
    br_plan = br_plan or {}
    qt_plan = qt_plan or {}
    fallback_plan = fallback_plan or {}

    all_days = set(fallback_plan) | set(br_plan) | set(qt_plan)
    merged = {}

    for day in sorted(all_days, key=lambda value: int(value)):
        fallback_row = fallback_plan.get(day, ["", "", "", "", ""])
        br_row = br_plan.get(day)
        qt_value = qt_plan.get(day)

        merged[day] = [
            *(br_row if br_row is not None else fallback_row[:4]),
            qt_value if qt_value is not None else fallback_row[4],
        ]

    return merged
