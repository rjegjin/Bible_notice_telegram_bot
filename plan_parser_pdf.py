import pdfplumber
import json
import re

def clean_text(text):
    """텍스트에서 불필요한 공백과 줄바꿈 제거"""
    if not text:
        return ""
    return text.replace("\n", " ").strip()

def parse_bible_plan(pdf_path):
    final_data = {} # {날짜: [신약, 시편, 잠언, QT]}

    with pdfplumber.open(pdf_path) as pdf:
        # ---------------------------
        # 1. 첫 번째 페이지: 성경 읽기표 (Bible Reading)
        # ---------------------------
        page1 = pdf.pages[0]
        # extract_table은 PDF의 표를 2차원 리스트로 변환해줍니다.
        tables = page1.extract_tables()

        for table in tables:
            for row in table:
                # 행의 길이가 충분한지 확인 (빈 행 제외)
                # 예상 구조: [날짜, 신약, 시/잠, ..., 날짜, 신약, 시/잠] (좌우 2단 구성일 가능성 높음)
                
                # 데이터 정제 및 날짜 추출 로직
                # 좌측 컬럼 (1일~16일)
                if len(row) > 2 and row[0]: 
                    try:
                        day_txt = clean_text(row[0])
                        # '1 목' 처럼 요일이 섞여 있을 수 있으므로 숫자만 추출
                        day_match = re.search(r'(\d+)', day_txt)
                        if day_match:
                            day = int(day_match.group(1))
                            nt = clean_text(row[1]) # 신약
                            ps_pr = clean_text(row[2]) # 시편/잠언 (예: "34 1")
                            
                            # 시편/잠언 분리 (공백이나 줄바꿈으로 구분된 경우)
                            parts = ps_pr.split()
                            ps = parts[0] if len(parts) > 0 else ""
                            pr = parts[1] if len(parts) > 1 else ""
                            
                            final_data[day] = [nt, ps, pr, ""] # QT는 아직 비워둠
                    except Exception as e:
                        pass # 헤더나 빈 칸은 패스

                # 우측 컬럼 (17일~31일) - 테이블 구조에 따라 인덱스 조정 필요
                # 보통 좌우 대칭이면 인덱스 4, 5, 6 정도에 위치함
                if len(row) > 5 and row[4]:
                    try:
                        day_txt = clean_text(row[4])
                        day_match = re.search(r'(\d+)', day_txt)
                        if day_match:
                            day = int(day_match.group(1))
                            nt = clean_text(row[5])
                            ps_pr = clean_text(row[6])
                            
                            parts = ps_pr.split()
                            ps = parts[0] if len(parts) > 0 else ""
                            pr = parts[1] if len(parts) > 1 else ""
                            
                            final_data[day] = [nt, ps, pr, ""]
                    except:
                        pass

        # ---------------------------
        # 2. 두 번째 페이지: QT 달력 (Quiet Time)
        # ---------------------------
        if len(pdf.pages) > 1:
            page2 = pdf.pages[1]
            # 달력도 테이블 형태로 추출 시도
            qt_tables = page2.extract_tables()
            
            for table in qt_tables:
                for row in table:
                    for cell in row:
                        # 달력 셀 하나: "4\n시28편\n2장..." 형식
                        cell_text = clean_text(cell)
                        if not cell_text:
                            continue
                        
                        # 셀 안에서 날짜 찾기 (보통 맨 앞에 숫자)
                        # 예: "4 시28편..." -> 4일을 찾음
                        day_match = re.match(r'^(\d+)', cell_text)
                        if day_match:
                            day = int(day_match.group(1))
                            
                            # QT 본문 추출 로직
                            # 날짜 숫자를 제외한 나머지 텍스트를 가져옴
                            content = cell_text[len(day_match.group(0)):].strip()
                            
                            # 데이터 병합 (1페이지 데이터가 있으면 합치고, 없으면 새로 생성)
                            if day in final_data:
                                final_data[day][3] = content
                            else:
                                # 1페이지에 없는 날짜(혹은 파싱 실패)라면 QT만이라도 넣음
                                final_data[day] = ["", "", "", content]

    # 결과 검증 및 저장
    # 정렬하여 저장
    sorted_data = {k: final_data[k] for k in sorted(final_data)}
    
    with open('bible_plan.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=4)
    
    print(f"총 {len(sorted_data)}일 치 데이터 추출 완료.")
    print("bible_plan.json 파일을 확인해주세요.")

if __name__ == "__main__":
    # PDF 파일명 수정 필요
    parse_bible_plan("png2pdf.pdf")