"""Validated monthly QT plan -> one tab in the existing application-sheet Doc.

Authentication reuses the existing service account; never creates documents.
Requires Docs API enabled and Editor sharing on DOCUMENT_ID.
"""

from __future__ import annotations

import calendar
from datetime import date

from tools.plan_parser import validate_monthly_plan

DOCUMENT_ID = '1v4qG2b2jKL8j2JUhqCIWJbNTSctCnp10vQo4y7rUv3s'
HEADERS = ['날짜', '요일', '본문', '중심구절', '제목', '적용', '체크']
WIDTHS = [12, 9, 22, 18, 33, 27, 7]
ROW_HEIGHTS = ((21, 28), (20.5, 28.34645669291339))
TITLE_SPACE_BELOW = (22.6771653543, 11.3385826772)


def _pt(mm):
    return {'magnitude': mm * 72 / 25.4, 'unit': 'PT'}


def _points(value):
    return {'magnitude': value, 'unit': 'PT'}


def _text(element):
    if 'paragraph' in element:
        return ''.join(e.get('textRun', {}).get('content', '')
                       for e in element['paragraph'].get('elements', []))
    return ''.join(_text(e) for e in element.get('content', []))


def _tabs(tabs):
    for tab in tabs:
        yield tab
        yield from _tabs(tab.get('childTabs', []))


def _body(tab):
    return tab['documentTab']['body']['content']


def _tables(tab):
    return [e for e in _body(tab) if 'table' in e]


def _range(tab_id, start, end):
    return {'tabId': tab_id, 'startIndex': start, 'endIndex': end}


def _service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from tools.gdrive_parser import SERVICE_KEY_PATH

    credentials = Credentials.from_service_account_file(
        SERVICE_KEY_PATH, scopes=['https://www.googleapis.com/auth/documents'])
    return build('docs', 'v1', credentials=credentials)


def month_rows(plan, year, month):
    validate_monthly_plan(plan, year, month)
    import holidays

    public_holidays = holidays.country_holidays('KR', years=year, language='ko')
    rows = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        current = date(year, month, day)
        color = ({'red': 1} if current.weekday() == 6 or current in public_holidays
                 else {'blue': 1} if current.weekday() == 5 else {})
        rows.append(([f'{month}/{day}', '월화수목금토일'[current.weekday()],
                      str(plan[str(day)][4]), '', '', '', '☐'], color))
    return rows


def _check_shape(tab, count):
    tables = _tables(tab)
    if len(tables) != 2 or [t['table']['rows'] for t in tables] != [16, count - 14]:
        raise RuntimeError('월 탭의 두 표/날짜 행 구조가 다릅니다. 기존 내용을 보존하고 중단합니다.')
    if any(t['table']['columns'] != 7 for t in tables):
        raise RuntimeError('월 탭은 7열이어야 합니다.')
    return tables


def _fill_requests(tab, rows, year, month, fresh):
    tab_id = tab['tabProperties']['tabId']
    tables = _check_shape(tab, len(rows))
    edits = []
    title = f'{year}년 {month}월 Quiet Time 적용 시트'
    page_titles = [title, f'{title} (16일 ~ {len(rows)}일)']
    titles = [e for e in _body(tab) if 'Quiet Time' in _text(e)]
    if len(titles) != 2:
        raise RuntimeError('월 탭의 페이지 제목 2개를 확인할 수 없습니다.')
    for element, value in zip(titles, page_titles):
        if not _text(element).startswith(f'{year}년 {month}월 '):
            raise RuntimeError('같은 월 이름에 다른 연도/월 내용이 있습니다. 덮어쓰지 않습니다.')
        edits.append((element['startIndex'], element['endIndex'] - 1, value))
    offset = 0
    for table in tables:
        for ri, row in enumerate(table['table']['tableRows']):
            values = HEADERS if ri == 0 else rows[offset][0]
            for ci, cell in enumerate(row['tableCells']):
                if not fresh and ri and ci >= 3 and not (ci == 6 and not _text(cell).strip()):
                    continue  # Handwritten/user-entered application fields belong to the user.
                content = cell['content']
                if len(content) != 1 or 'paragraph' not in content[0]:
                    raise RuntimeError('자동 입력 칸에 복합 구조가 있습니다. 보존하고 중단합니다.')
                paragraph = content[0]
                if any(set(e) - {'startIndex', 'endIndex', 'textRun'}
                       for e in paragraph['paragraph'].get('elements', [])):
                    raise RuntimeError('자동 입력 칸에 텍스트 이외 요소가 있습니다.')
                edits.append((paragraph['startIndex'], paragraph['endIndex'] - 1, values[ci]))
            if ri:
                offset += 1
    requests = []
    for start, end, value in sorted(edits, reverse=True):
        if end > start:
            requests.append({'deleteContentRange': {'range': _range(tab_id, start, end)}})
        if value:
            requests.append({'insertText': {'location': {'index': start, 'tabId': tab_id}, 'text': value}})
    return requests


def _style_requests(tab, rows):
    tid = tab['tabProperties']['tabId']
    end = _body(tab)[-1]['endIndex'] - 1
    whole = _range(tid, 1, end)
    requests = []
    def style(kind, target, value):
        field = {'updateTextStyle': 'textStyle', 'updateParagraphStyle': 'paragraphStyle',
                 'updateSectionStyle': 'sectionStyle', 'updateTableRowStyle': 'tableRowStyle',
                 'updateTableCellStyle': 'tableCellStyle'}[kind]
        requests.append({kind: {**target, field: value, 'fields': ','.join(value)}})

    requests.append({'updateDocumentStyle': {'tabId': tid, 'documentStyle': {
        'pageSize': {'width': _pt(148), 'height': _pt(203)},
        'marginTop': _pt(12), 'marginBottom': _pt(5)},
        'fields': 'pageSize,marginTop,marginBottom'}})
    style('updateTextStyle', {'range': whole}, {
        'weightedFontFamily': {'fontFamily': 'Noto Sans KR'},
        'fontSize': {'magnitude': 7.5, 'unit': 'PT'}})
    style('updateParagraphStyle', {'range': whole}, {
        'spaceAbove': _pt(0), 'spaceBelow': _pt(0), 'lineSpacing': 100})
    titles = [e for e in _body(tab) if 'Quiet Time' in _text(e)]
    for i, element in enumerate(titles):
        target = {'range': _range(tid, element['startIndex'], element['endIndex'])}
        style('updateTextStyle', target, {'bold': True, 'fontSize': {
            'magnitude': 11.34 if i == 0 else 8.5, 'unit': 'PT'}})
        style('updateParagraphStyle', target, {
            'alignment': 'CENTER', 'spaceBelow': _points(TITLE_SPACE_BELOW[i]), 'lineSpacing': 100})
        style('updateSectionStyle', target, {'marginLeft': _pt(15 if i == 0 else 5),
                                             'marginRight': _pt(5 if i == 0 else 15)})
    for element in _body(tab):
        if 'paragraph' in element and (not _text(element).strip() or 'SNU-B Team' in _text(element)):
            style('updateTextStyle', {'range': _range(tid, element['startIndex'], element['endIndex'])},
                  {'fontSize': {'magnitude': 5.5 if 'SNU-B Team' in _text(element) else 1, 'unit': 'PT'}})
    offset = 0
    for page, table in enumerate(_tables(tab)):
        loc = {'tabId': tid, 'index': table['startIndex']}
        for ci, width in enumerate(WIDTHS):
            requests.append({'updateTableColumnProperties': {'tableStartLocation': loc,
                'columnIndices': [ci], 'tableColumnProperties': {'widthType': 'FIXED_WIDTH', 'width': _pt(width)},
                'fields': 'widthType,width'}})
        style('updateTableCellStyle', {'tableStartLocation': loc}, {
            'paddingTop': _pt(1.5), 'paddingBottom': _pt(1.5),
            'paddingLeft': _pt(2), 'paddingRight': _pt(2), 'contentAlignment': 'MIDDLE'})
        data_count = table['table']['rows'] - 1
        header_height, row_height = ROW_HEIGHTS[page]
        style('updateTableRowStyle', {'tableStartLocation': loc, 'rowIndices': [0]}, {'minRowHeight': _points(header_height)})
        style('updateTableRowStyle', {'tableStartLocation': loc, 'rowIndices': list(range(1, data_count + 1))},
              {'minRowHeight': _points(row_height)})
        for ri, row in enumerate(table['table']['tableRows']):
            for ci, cell in enumerate(row['tableCells']):
                if ri and ci >= 3:
                    continue
                p = cell['content'][0]
                target = {'range': _range(tid, p['startIndex'], p['endIndex'])}
                style('updateTextStyle', target, {'bold': ri == 0})
                if ri:
                    style('updateTextStyle', target, {'foregroundColor': {'color': {'rgbColor': rows[offset][1]}}})
            if ri:
                offset += 1
    return requests


def verify_tab(tab, rows, year, month):
    if tab['tabProperties']['title'] != f'{month}월':
        raise RuntimeError('Docs readback: 월 탭 제목 불일치')
    tables = _check_shape(tab, len(rows))
    actual = [[_text(c).strip().replace('–', '-') for c in r['tableCells'][:3]]
              for t in tables for r in t['table']['tableRows'][1:]]
    expected = [[s.replace('–', '-') for s in row[0][:3]] for row in rows]
    if actual != expected:
        raise RuntimeError('Docs readback: 날짜/요일/QT 본문 불일치')
    title = f'{year}년 {month}월 Quiet Time 적용 시트'
    expected_titles = {title, f'{title} (16일 ~ {len(rows)}일)'}
    if {_text(e).strip() for e in _body(tab) if 'Quiet Time' in _text(e)} != expected_titles:
        raise RuntimeError('Docs readback: 페이지 제목 불일치')
    if not any(e.get('sectionBreak', {}).get('sectionStyle', {}).get('sectionType') == 'NEXT_PAGE'
               for e in _body(tab)):
        raise RuntimeError('Docs readback: NEXT_PAGE section break 누락')


def upsert_quiet_time_tab(plan, year, month, *, service=None, document_id=DOCUMENT_ID):
    """Validate before touching Docs; every write targets this tab and revision.

    Existing application entries are retained. A failed write/readback raises and
    stops publish. Retrying addresses the same tab, never creates another Doc.
    """
    rows = month_rows(plan, year, month)
    try:
        api = (service or _service()).documents()
        document = api.get(documentId=document_id, includeTabsContent=True).execute()
        revision = document['revisionId']

        def write(requests):
            nonlocal revision
            result = api.batchUpdate(documentId=document_id, body={
                'writeControl': {'requiredRevisionId': revision}, 'requests': requests}).execute()
            revision = result['writeControl']['requiredRevisionId']

        def read():
            result = api.get(documentId=document_id, includeTabsContent=True).execute()
            if result['revisionId'] != revision:
                raise RuntimeError('Google Docs가 다른 편집자에 의해 변경됐습니다. 재실행하세요.')
            return next(t for t in _tabs(result['tabs']) if t['tabProperties']['tabId'] == tid)

        matches = [t for t in _tabs(document['tabs']) if t['tabProperties']['title'] == f'{month}월']
        if len(matches) > 1:
            raise RuntimeError('같은 월 탭이 여러 개여서 대상을 확정할 수 없습니다.')
        if not matches:
            write([{'addDocumentTab': {'tabProperties': {'title': f'{month}월'}}}])
            document = api.get(documentId=document_id, includeTabsContent=True).execute()
            if document['revisionId'] != revision:
                raise RuntimeError('Google Docs revision 충돌')
            matches = [t for t in _tabs(document['tabs']) if t['tabProperties']['title'] == f'{month}월']
        tab = matches[0]
        tid = tab['tabProperties']['tabId']
        fresh = not _tables(tab) and not any(_text(e).strip() for e in _body(tab))
        if fresh:
            title = f'{year}년 {month}월 Quiet Time 적용 시트'
            location = {'index': 1, 'tabId': tid}
            # Reverse construction: second page first, then first page before it.
            write([
                {'insertTable': {'rows': len(rows) - 14, 'columns': 7, 'location': location}},
                {'insertText': {'text': title + '\n', 'location': location}},
                {'insertSectionBreak': {'sectionType': 'NEXT_PAGE', 'location': location}},
                {'insertTable': {'rows': 16, 'columns': 7, 'location': location}},
                {'insertText': {'text': title + '\nSNU-B Team\n', 'location': location}},
            ])
            tab = read()
        write(_fill_requests(tab, rows, year, month, fresh))
        tab = read()
        if fresh:
            write(_style_requests(tab, rows))
        verify_tab(read(), rows, year, month)
        return f'https://docs.google.com/document/d/{document_id}/edit?tab={tid}'
    except Exception as error:
        from googleapiclient.errors import HttpError
        if isinstance(error, HttpError):
            raise RuntimeError(
                f'Google Docs HTTP {error.resp.status}: Docs API 활성화, 대상 문서의 service account '
                '편집자 공유, revision 충돌을 확인하세요. mh_bot 배포는 중단됩니다.'
            ) from None
        raise
