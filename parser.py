"""
교육과정 학점 배당표 엑셀 파일 파서
- 병합셀 해제, 헤더 동적 탐지, 데이터/요약 영역 분리
"""
import re
from copy import copy

import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter


def unmerge_and_fill(ws):
    """병합된 셀을 해제하고 좌상단 값으로 채움"""
    merged_ranges = list(ws.merged_cells.ranges)
    for merged_range in merged_ranges:
        min_col, min_row, max_col, max_row = (
            merged_range.min_col, merged_range.min_row,
            merged_range.max_col, merged_range.max_row,
        )
        top_left_value = ws.cell(row=min_row, column=min_col).value
        ws.unmerge_cells(str(merged_range))
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                ws.cell(row=row, column=col).value = top_left_value
    return ws


def ws_to_df(ws):
    """워크시트를 DataFrame으로 변환"""
    data = []
    for row in ws.iter_rows(values_only=True):
        data.append(list(row))
    df = pd.DataFrame(data)
    return df


def find_header_row(df):
    """헤더 행(교과, 과목명 등이 포함된 행) 탐지"""
    keywords = ["교과", "과목", "학년", "학기"]
    for idx, row in df.iterrows():
        row_str = " ".join(str(v) for v in row.values if v is not None)
        hit = sum(1 for kw in keywords if kw in row_str)
        if hit >= 3:
            return idx
    return None


def find_summary_start(df, header_row):
    """하단 요약/유의사항 시작 행 탐지"""
    keywords = ["합계", "소계", "창의적", "유의사항", "총계", "이수학점"]
    for idx in range(header_row + 1, len(df)):
        row_str = " ".join(str(v) for v in df.iloc[idx].values if v is not None)
        for kw in keywords:
            if kw in row_str:
                return idx
    return len(df)


def build_column_names(df, header_row):
    """2행 병합 헤더를 합성하여 컬럼명 생성"""
    row1 = df.iloc[header_row].fillna("").astype(str).tolist()
    row2 = df.iloc[header_row + 1].fillna("").astype(str).tolist() if header_row + 1 < len(df) else [""] * len(row1)

    columns = []
    for i in range(len(row1)):
        c1, c2 = row1[i].strip(), row2[i].strip()
        # 학년-학기 헤더 처리
        year_match = re.search(r"([1-3])\s*학년", c1)
        sem_match = re.search(r"([1-2])\s*학기", c2)
        if year_match and sem_match:
            columns.append(f"{year_match.group(1)}-{sem_match.group(1)}")
        elif c1 and c2 and c1 != c2:
            columns.append(f"{c1}_{c2}")
        elif c2:
            columns.append(c2)
        else:
            columns.append(c1 if c1 else f"col_{i}")
    return columns


def to_numeric_safe(v):
    """학점 값을 숫자로 변환 (괄호, 텍스트 처리)"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0
    s = str(v).strip()
    if s == "" or s in ("-", "·"):
        return 0
    # "12(택4)" 같은 형식에서 첫 숫자 추출
    m = re.match(r"^(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1))
    return 0


def parse_curriculum(file_path):
    """엑셀 파일을 파싱하여 구조화된 결과 반환"""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    # 1. 병합셀 해제
    ws = unmerge_and_fill(ws)

    # 2. DataFrame 변환
    df_raw = ws_to_df(ws)

    # 3. 메타정보 추출 (상단 텍스트)
    metadata = {"school": "", "year": "", "title": ""}
    for idx in range(min(5, len(df_raw))):
        row_str = " ".join(str(v) for v in df_raw.iloc[idx].values if v is not None)
        if "고등학교" in row_str and not metadata["school"]:
            school_match = re.search(r"([가-힣]+(?:여자|남자)?(?:고등학교|고))", row_str)
            if school_match:
                metadata["school"] = school_match.group(1)
        year_match = re.search(r"(20\d{2})학년도", row_str)
        if year_match and not metadata["year"]:
            metadata["year"] = year_match.group(1)
        if "학점 배당" in row_str and not metadata["title"]:
            metadata["title"] = row_str.strip()

    # 4. 헤더 행 탐지
    header_row = find_header_row(df_raw)
    if header_row is None:
        raise ValueError("헤더 행을 찾을 수 없습니다. 엑셀 형식을 확인하세요.")

    # 5. 컬럼명 생성
    columns = build_column_names(df_raw, header_row)

    # 6. 요약 영역 시작 탐지
    summary_start = find_summary_start(df_raw, header_row)

    # 7. 데이터 영역 추출
    data_start = header_row + 2
    df_data = df_raw.iloc[data_start:summary_start].copy()
    df_data.columns = columns
    df_data = df_data.reset_index(drop=True)
    df_data = df_data.dropna(how="all").reset_index(drop=True)

    # 8. 요약 영역 추출
    df_summary = df_raw.iloc[summary_start:].copy()
    df_summary.columns = columns + [f"extra_{i}" for i in range(len(df_summary.columns) - len(columns))] if len(df_summary.columns) > len(columns) else columns[:len(df_summary.columns)]
    df_summary = df_summary.reset_index(drop=True)

    # 9. 학기 컬럼 식별 (1-1 ~ 3-2)
    semester_cols = [c for c in columns if re.match(r"^[1-3]-[1-2]$", c)]

    # 10. 비고 텍스트 추출
    notes_text = []
    note_cols = [c for c in df_data.columns if "비고" in str(c) or "유의" in str(c) or "참고" in str(c)]
    if note_cols:
        for col in note_cols:
            for v in df_data[col].dropna().unique():
                if str(v).strip():
                    notes_text.append(str(v).strip())

    # 하단 요약영역의 유의사항 텍스트
    for idx, row in df_summary.iterrows():
        for v in row.values:
            if v is None:
                continue
            s = str(v).strip()
            if len(s) > 15 and any(k in s for k in ["이수", "선택", "운영", "편성", "유의", "교차"]):
                if s not in notes_text:
                    notes_text.append(s)

    return {
        "metadata": metadata,
        "raw": df_raw,
        "data": df_data,
        "summary": df_summary,
        "columns": columns,
        "semester_cols": semester_cols,
        "header_row": header_row,
        "summary_start": summary_start,
        "notes": notes_text,
    }


def extract_subject_records(parsed):
    """과목별 레코드를 표준화된 형식으로 추출"""
    df = parsed["data"].copy()
    semester_cols = parsed["semester_cols"]

    # 과목명 컬럼 추정
    subject_col = None
    for c in df.columns:
        cs = str(c)
        if "과목" in cs and ("명" in cs or cs.endswith("과목")):
            subject_col = c
            break
    if subject_col is None:
        for c in df.columns:
            if "과목" in str(c):
                subject_col = c
                break

    # 교과군 컬럼 추정
    group_col = None
    for c in df.columns:
        cs = str(c)
        if "교과" in cs and "군" in cs:
            group_col = c
            break
    if group_col is None:
        for c in df.columns:
            if "교과" in str(c) and "과목" not in str(c):
                group_col = c
                break

    records = []
    for _, row in df.iterrows():
        if subject_col is None:
            break
        name = str(row[subject_col]).strip() if pd.notna(row[subject_col]) else ""
        if not name or name in ("nan", "None"):
            continue

        sem_credits = {}
        total = 0
        for sc in semester_cols:
            v = to_numeric_safe(row.get(sc))
            sem_credits[sc] = v
            total += v

        records.append({
            "교과군": str(row[group_col]).strip() if group_col and pd.notna(row.get(group_col)) else "",
            "과목명": name,
            "학기별": sem_credits,
            "총학점": total,
        })

    return records
