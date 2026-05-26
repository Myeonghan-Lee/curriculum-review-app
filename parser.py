"""
parser.py
2022 개정 고등학교 교육과정 학점배당표 엑셀 파서
- 병합셀 해제 → forward-fill
- 동적 헤더/경계 탐지 (2~3행 병합 헤더 지원)
- 과목별 17개 필드 추출
"""
import re
import pandas as pd
from openpyxl import load_workbook


def unmerge_and_fill(ws):
    """병합셀을 해제하고 상위 값으로 채움"""
    merged_ranges = list(ws.merged_cells.ranges)
    for mr in merged_ranges:
        min_row, min_col, max_row, max_col = mr.min_row, mr.min_col, mr.max_row, mr.max_col
        top_value = ws.cell(min_row, min_col).value
        ws.unmerge_cells(str(mr))
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(r, c).value = top_value
    return ws


def sheet_to_dataframe(ws):
    data = []
    for row in ws.iter_rows(values_only=True):
        data.append(list(row))
    return pd.DataFrame(data)


def find_header_rows(df):
    """헤더 시작/끝 행 탐지. 헤더는 2~3행에 걸칠 수 있음."""
    header_start = None
    for idx, row in df.iterrows():
        cells = [str(c) for c in row if c is not None]
        joined = " ".join(cells)
        if ("교과" in joined or "과목" in joined) and ("학점" in joined or "단위" in joined or "학기" in joined or "학년" in joined):
            header_start = idx
            break
    if header_start is None:
        return None, None

    # 헤더 종료: 아래 행에 "학기" 또는 단순 "1학기"/"1") 등 추가 헤더 텍스트가 있으면 포함
    header_end = header_start
    for offset in range(1, 4):
        if header_start + offset >= len(df):
            break
        row_text = " ".join(str(c) for c in df.iloc[header_start + offset] if c is not None)
        if "학기" in row_text or "1학기" in row_text or "2학기" in row_text:
            header_end = header_start + offset
        else:
            # 다음 행이 데이터 행처럼 보이는지 확인 (숫자/과목명 시작)
            break
    return header_start, header_end


def build_column_map(df, h_start, h_end):
    """헤더 구간(여러 행)을 합성하여 컬럼명 생성"""
    n_cols = df.shape[1]
    cols = []
    for i in range(n_cols):
        parts = []
        year_part = None
        sem_part = None
        for r in range(h_start, h_end + 1):
            v = df.iat[r, i]
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            s = str(v).strip().replace("\n", " ")
            if not s or s in parts:
                continue
            # 연도/학기 추출
            my = re.search(r"(\d)\s*학년", s)
            ms = re.search(r"(\d)\s*학기", s)
            if my:
                year_part = my.group(1)
                continue
            if ms:
                sem_part = ms.group(1)
                continue
            parts.append(s)

        if year_part and sem_part:
            col = f"{year_part}-{sem_part}"
        elif sem_part and parts:
            # 학기만 있는 경우 (학년이 상위 행에 있음) - 위치로 추론
            col = "-".join(parts) + f"_{sem_part}학기"
        else:
            col = " ".join(parts) if parts else f"col{i}"
        cols.append(col)

    # 중복 컬럼명 처리
    seen = {}
    final = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            final.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            final.append(c)

    # 학기 컬럼 재정렬: "1-1" 형식이 아닌데 학기 정보만 있는 경우 추가 후처리
    # 1학년/2학년/3학년 패턴이 학기와 다른 행에 있을 때 위치 기반으로 재구성
    final = _post_fix_semester_cols(df, h_start, h_end, final)
    return final


def _post_fix_semester_cols(df, h_start, h_end, cols):
    """학기 컬럼명이 1-1,1-2 형식으로 만들어지지 않은 경우 위치 기반 재구성"""
    # 학기 표시("1학기", "2학기") 위치 찾기
    sem_positions = []
    for i, c in enumerate(cols):
        if re.match(r"^[123]-[12]$", c):
            sem_positions.append((i, c))
    if len(sem_positions) >= 6:
        return cols  # 이미 정상

    # 위치별로 학년 헤더와 학기 헤더 추적
    n_cols = df.shape[1]
    year_at_col = {}
    sem_at_col = {}
    for r in range(h_start, h_end + 1):
        cur_year = None
        for i in range(n_cols):
            v = df.iat[r, i]
            if v is None:
                continue
            s = str(v).strip()
            my = re.search(r"(\d)\s*학년", s)
            ms = re.search(r"(\d)\s*학기", s)
            if my:
                year_at_col[i] = my.group(1)
            if ms:
                sem_at_col[i] = ms.group(1)

    # 학년 forward-fill
    if year_at_col:
        sorted_years = sorted(year_at_col.items())
        for i in range(n_cols):
            if i in sem_at_col and i not in year_at_col:
                # 자기보다 작은 위치에서 가장 가까운 학년
                yr = None
                for yi, yv in sorted_years:
                    if yi <= i:
                        yr = yv
                if yr:
                    year_at_col[i] = yr

    new_cols = list(cols)
    for i in range(n_cols):
        if i in sem_at_col and i in year_at_col:
            new_cols[i] = f"{year_at_col[i]}-{sem_at_col[i]}"
    # 중복 해소
    seen = {}
    final = []
    for c in new_cols:
        if c in seen:
            seen[c] += 1
            final.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            final.append(c)
    return final


def find_data_end(df, start_row):
    end_keywords = ["소계", "합계", "총계", "창의적 체험활동", "창의적체험활동",
                    "유의사항", "비고사항", "필수이수", "이수단위계"]
    for idx in range(start_row, len(df)):
        first_cells = " ".join(str(c) for c in df.iloc[idx, :3] if c is not None)
        for kw in end_keywords:
            if kw in first_cells:
                return idx
    return len(df)


def extract_summary_rows(df, data_end):
    summary = {}
    for idx in range(data_end, len(df)):
        row = df.iloc[idx]
        first_cells = " ".join(str(c) for c in row.iloc[:5] if c is not None)
        if "소계" in first_cells:
            summary.setdefault("소계", []).append(row.tolist())
        elif "합계" in first_cells or "총계" in first_cells:
            summary.setdefault("합계", []).append(row.tolist())
        elif "창의적" in first_cells:
            summary.setdefault("창의적체험활동", []).append(row.tolist())
        elif "유의" in first_cells or "비고" in first_cells:
            summary.setdefault("유의사항", []).append(row.tolist())
        elif "필수이수" in first_cells or "이수단위" in first_cells:
            summary.setdefault("필수이수", []).append(row.tolist())
    return summary


def to_num(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        if pd.isna(v):
            return 0
        return float(v)
    s = str(v).strip()
    if not s or s == "nan":
        return 0
    m = re.match(r"^\s*(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else 0


def _looks_like_header_text(row):
    """행이 헤더 잔재인지 판별 (대부분 셀이 한글 라벨)"""
    n_text = 0
    n_num = 0
    for v in row:
        if v is None:
            continue
        if isinstance(v, (int, float)) and not pd.isna(v):
            n_num += 1
        else:
            s = str(v).strip()
            if s and not s.replace(".", "").isdigit():
                n_text += 1
    return n_text >= 5 and n_num == 0


def parse_excel(filepath, sheet_name=0):
    wb = load_workbook(filepath, data_only=True)
    ws = wb[wb.sheetnames[sheet_name]] if isinstance(sheet_name, int) else wb[sheet_name]
    unmerge_and_fill(ws)
    df = sheet_to_dataframe(ws)

    # 메타데이터
    metadata = {"학교명": None, "입학년도": None, "교육과정": "2022 개정"}
    for idx in range(min(8, len(df))):
        text = " ".join(str(c) for c in df.iloc[idx] if c is not None)
        m_school = re.search(r"([가-힣]+(?:고등학교|여고|남고))", text)
        if m_school and not metadata["학교명"]:
            metadata["학교명"] = m_school.group(1)
        m_year = re.search(r"(20\d{2})\s*학년도", text)
        if m_year and not metadata["입학년도"]:
            metadata["입학년도"] = int(m_year.group(1))

    h_start, h_end = find_header_rows(df)
    if h_start is None:
        raise ValueError("헤더 행을 찾지 못했습니다.")
    columns = build_column_map(df, h_start, h_end)
    df.columns = columns

    # 데이터 영역
    data_start = h_end + 1
    # 헤더 잔재 행 추가 스킵
    while data_start < len(df) and _looks_like_header_text(df.iloc[data_start]):
        data_start += 1

    data_end = find_data_end(df, data_start)
    subjects = df.iloc[data_start:data_end].reset_index(drop=True)
    subjects = subjects.dropna(how="all").reset_index(drop=True)

    semester_cols = [c for c in columns if re.match(r"^[123]-[12]$", str(c))]
    for sc in semester_cols:
        subjects[sc + "_num"] = subjects[sc].apply(to_num)

    # 운영학점 컬럼이 있으면 그것을 우선 사용
    op_col = None
    for c in columns:
        sc = str(c).replace(" ", "").replace("\n", "")
        if "운영학점" in sc or "운영단위" in sc:
            op_col = c
            break

    if op_col is not None:
        subjects["운영학점_계산"] = subjects[op_col].apply(to_num)
    elif semester_cols:
        subjects["운영학점_계산"] = subjects[[sc + "_num" for sc in semester_cols]].sum(axis=1)
    else:
        subjects["운영학점_계산"] = 0

    summary = extract_summary_rows(df, data_end)

    return {
        "subjects": subjects,
        "summary": summary,
        "metadata": metadata,
        "semester_cols": semester_cols,
        "columns": columns,
        "raw": df,
        "header_rows": (h_start, h_end),
        "data_range": (data_start, data_end),
    }
