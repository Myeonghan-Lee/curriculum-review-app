"""
parser.py - 2022 개정 교육과정 학점배당표 엑셀 파서 (v3)

주요 개선:
- 헤더 키워드 정규화 (줄바꿈/공백/번호 접두사 제거 후 매칭)
- 헤더 탐지를 다단계로 수행 (엄격 → 완화 → 부분문자열)
- 2행/3행 병합 헤더 모두 자동 인식
- 학년/학기 컬럼을 위치 기반으로도 추정 (보조 로직)
"""
import re
import io
import copy
from typing import Optional, Dict, List, Any, Tuple
import openpyxl
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np


def _norm(v) -> str:
    """셀 값을 비교 가능한 형태로 정규화."""
    if v is None:
        return ""
    s = str(v)
    # 줄바꿈/탭/공백을 모두 제거
    s = re.sub(r"\s+", "", s)
    # "1)", "2.", "①" 등 접두사 제거
    s = re.sub(r"^[\(\[]?\d+[\)\]\.]\s*", "", s)
    s = re.sub(r"^[①-⑳]", "", s)
    return s


def _unmerge_and_fill(ws) -> None:
    """병합셀을 해제하고 좌상단 값을 전체 영역에 복사."""
    merged = [str(r) for r in ws.merged_cells.ranges]
    for rng in merged:
        ws.unmerge_cells(rng)
    for rng in merged:
        # rng 형식: "A1:C2"
        m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", rng)
        if not m:
            continue
        from openpyxl.utils import column_index_from_string
        c1 = column_index_from_string(m.group(1))
        r1 = int(m.group(2))
        c2 = column_index_from_string(m.group(3))
        r2 = int(m.group(4))
        v = ws.cell(r1, c1).value
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if r == r1 and c == c1:
                    continue
                ws.cell(r, c).value = v


# 헤더 키워드 (정규화 후 비교)
HEADER_KEYS = {
    "구분": ["구분"],
    "교과군": ["교과군", "교과", "교과(군)"],
    "과목유형": ["과목유형"],
    "과목명": ["과목", "과목명"],
    "기준학점": ["기준학점"],
    "운영학점": ["운영학점"],
    "학년1": ["1학년"],
    "학년2": ["2학년"],
    "학년3": ["3학년"],
    "비고": ["비고"],
    "이수학점": ["이수학점"],
    "필수이수학점": ["필수이수학점"],
}


def _find_header_row(ws) -> Tuple[int, int]:
    """
    헤더 행 위치를 찾는다.
    반환: (header_start_row, header_end_row)  - 1-based
    """
    max_scan = min(ws.max_row, 20)
    best_row = -1
    best_score = 0
    for r in range(1, max_scan + 1):
        row_norm = [_norm(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        score = 0
        for key_list in HEADER_KEYS.values():
            for k in key_list:
                if any(k in cell for cell in row_norm if cell):
                    score += 1
                    break
        if score > best_score:
            best_score = score
            best_row = r
    if best_row < 0 or best_score < 4:
        raise ValueError(
            f"헤더 행을 찾지 못했습니다. (최고 점수={best_score}, 행={best_row}) "
            f"엑셀 상단 20행 안에 '구분/교과/과목/학점/학년' 키워드가 충분히 들어있는지 확인하세요."
        )
    # 헤더 다음 행에 '1학기/2학기'가 있으면 2행 헤더
    next_row_norm = [_norm(ws.cell(best_row + 1, c).value) for c in range(1, ws.max_column + 1)]
    has_semester = any("학기" in cell for cell in next_row_norm if cell)
    if has_semester:
        return best_row, best_row + 1
    return best_row, best_row


def _build_column_map(ws, h_start: int, h_end: int) -> Dict[str, int]:
    """헤더 행을 읽어 컬럼 인덱스(1-based) 매핑을 만든다."""
    col_map: Dict[str, int] = {}
    semester_cols: List[Tuple[int, str]] = []  # (col, '1-1' 등)

    # 컬럼별 정규화 값 수집
    col_norm: Dict[int, str] = {}
    for c in range(1, ws.max_column + 1):
        col_norm[c] = _norm(ws.cell(h_start, c).value)

    # 우선순위가 높은 키부터 매핑 (긴 키, 더 구체적인 키 먼저)
    priority_order = [
        "필수이수학점", "이수학점", "기준학점", "운영학점",
        "과목유형", "과목명",
        "교과군", "구분", "비고",
    ]
    used_cols = set()

    for key in priority_order:
        variants = HEADER_KEYS.get(key, [])
        for c in range(1, ws.max_column + 1):
            if c in used_cols:
                continue
            top = col_norm[c]
            if not top:
                continue
            matched = False
            for v in variants:
                vn = _norm(v)
                if not vn:
                    continue
                # 정확 일치 또는 짧은 변형 일치
                if vn == top:
                    matched = True
                    break
                # '과목명'을 찾을 때 '과목유형'은 배제
                if key == "과목명" and "과목유형" in top:
                    continue
                # '교과군'을 찾을 때 '교과(군)' 같은 변형 허용 (4자 이내)
                if vn in top and len(top) <= len(vn) + 3:
                    matched = True
                    break
            if matched:
                col_map[key] = c
                used_cols.add(c)
                break

    # 2단계: 학년+학기 결합
    for c in range(1, ws.max_column + 1):
        top = col_norm[c]
        sub = _norm(ws.cell(h_end, c).value) if h_end > h_start else ""
        if "1학년" in top:
            if "1학기" in sub:
                semester_cols.append((c, "1-1"))
            elif "2학기" in sub:
                semester_cols.append((c, "1-2"))
        elif "2학년" in top:
            if "1학기" in sub:
                semester_cols.append((c, "2-1"))
            elif "2학기" in sub:
                semester_cols.append((c, "2-2"))
        elif "3학년" in top:
            if "1학기" in sub:
                semester_cols.append((c, "3-1"))
            elif "2학기" in sub:
                semester_cols.append((c, "3-2"))

    # 보조 로직: 헤더 행에 '1학년/2학년/3학년'만 있고 하위 학기가 비어있는 경우
    # 인접 컬럼 2개씩 묶어 1학기/2학기로 추정
    if len(semester_cols) < 6:
        semester_cols = []
        grade_cols = []
        for c in range(1, ws.max_column + 1):
            top = _norm(ws.cell(h_start, c).value)
            if "1학년" in top:
                grade_cols.append((c, 1))
            elif "2학년" in top:
                grade_cols.append((c, 2))
            elif "3학년" in top:
                grade_cols.append((c, 3))
        # 같은 학년이 2칸이면 1학기/2학기로 분배
        from collections import defaultdict
        g2c = defaultdict(list)
        for c, g in grade_cols:
            g2c[g].append(c)
        for g, cols in g2c.items():
            cols = sorted(cols)
            if len(cols) >= 2:
                semester_cols.append((cols[0], f"{g}-1"))
                semester_cols.append((cols[1], f"{g}-2"))
            elif len(cols) == 1:
                semester_cols.append((cols[0], f"{g}-1"))

    for c, label in semester_cols:
        col_map[label] = c

    return col_map


def _extract_metadata(ws) -> Dict[str, Any]:
    """상단 1~2행에서 학교명, 학년도 등을 추출."""
    meta = {"school": None, "year": None, "title": None, "raw_header": []}
    for r in range(1, 4):
        for c in range(1, ws.max_column + 1):
            v = ws.cell(r, c).value
            if v and isinstance(v, str):
                meta["raw_header"].append(v)
                # 학교명
                if "학교" in v and meta["school"] is None:
                    m = re.search(r"([가-힣A-Za-z0-9]+(?:고등학교|중학교|학교))", v)
                    if m:
                        meta["school"] = m.group(1)
                # 학년도
                if "학년도" in v and meta["year"] is None:
                    m = re.search(r"(\d{4})\s*학년도", v)
                    if m:
                        meta["year"] = int(m.group(1))
                if meta["title"] is None and ("배당표" in v or "교육과정" in v):
                    meta["title"] = v
    return meta


def _detect_summary_keywords() -> List[str]:
    return [
        "합계", "소계", "총계", "교과 합계", "교과합계",
        "창의적 체험활동", "창의적체험활동", "창체",
        "총 이수", "총이수", "필수 이수", "필수이수",
        "학기당", "학기 당", "과목 수", "과목수",
        "이수학점", "이수 학점",
    ]


def _is_summary_row(row_text: str) -> bool:
    norm = _norm(row_text)
    for kw in _detect_summary_keywords():
        if _norm(kw) in norm:
            return True
    return False


def _to_num(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        # "12(택4)" 같은 경우 12만 추출
        m = re.match(r"\s*(\d+(?:\.\d+)?)", s)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
    return None


def parse_excel(source) -> Dict[str, Any]:
    """
    엑셀 파일을 파싱해 정형화된 dict로 반환.
    source: 파일 경로 또는 BytesIO
    반환 키:
      - meta: 학교명, 학년도 등
      - col_map: 헤더 컬럼 매핑
      - subjects: 과목별 데이터 (list of dict)
      - summary: 하단 요약 행 (list of dict)
      - notes: 유의사항 텍스트 (list of str)
      - dataframe: pandas DataFrame
    """
    wb = openpyxl.load_workbook(source, data_only=True)
    # 시트 선택: 이름에 '입학' 또는 '학점' 포함된 시트 우선, 없으면 첫번째
    ws = None
    for sn in wb.sheetnames:
        if any(k in sn for k in ["입학", "학점", "배당"]):
            ws = wb[sn]
            break
    if ws is None:
        ws = wb[wb.sheetnames[0]]

    # 병합셀 해제
    _unmerge_and_fill(ws)

    # 메타데이터
    meta = _extract_metadata(ws)
    meta["sheet_name"] = ws.title

    # 헤더 탐지
    h_start, h_end = _find_header_row(ws)
    col_map = _build_column_map(ws, h_start, h_end)

    # 필수 컬럼 확인 (과목명 또는 운영학점 중 최소 하나)
    if "과목명" not in col_map and "운영학점" not in col_map:
        raise ValueError(
            f"필수 컬럼(과목명/운영학점)을 찾지 못했습니다. 헤더 매핑: {col_map}"
        )

    sem_labels = [f"{g}-{s}" for g in (1, 2, 3) for s in (1, 2)]

    subjects: List[Dict[str, Any]] = []
    summary: List[Dict[str, Any]] = []
    notes: List[str] = []

    data_start = h_end + 1
    for r in range(data_start, ws.max_row + 1):
        row_vals = {c: ws.cell(r, c).value for c in range(1, ws.max_column + 1)}
        # 행 전체가 비어있으면 스킵
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in row_vals.values()):
            continue

        # 행 텍스트로 요약/유의사항 판별
        joined = " ".join(str(v) for v in row_vals.values() if v is not None)
        norm_joined = _norm(joined)

        # 유의사항 (긴 텍스트, 한 셀에 문장)
        if ("유의사항" in joined or "유의 사항" in joined or
            (len(joined) > 60 and "학점" in joined and "과목" not in joined[:20])):
            notes.append(joined.strip())
            continue

        # 과목명 셀 추출
        sname = None
        if "과목명" in col_map:
            sname = ws.cell(r, col_map["과목명"]).value
            sname = sname.strip() if isinstance(sname, str) else sname

        # 요약 행
        is_summary = False
        first_two = " ".join(str(row_vals.get(c, "")) for c in [1, 2, 3, 4] if row_vals.get(c))
        if _is_summary_row(first_two) or _is_summary_row(joined[:80]):
            is_summary = True
        # 과목명이 비어있고 운영학점/이수학점이 있으면 요약
        if not sname:
            op = _to_num(ws.cell(r, col_map["운영학점"]).value) if "운영학점" in col_map else None
            tot = _to_num(ws.cell(r, col_map["이수학점"]).value) if "이수학점" in col_map else None
            sem_sum = sum((_to_num(ws.cell(r, col_map[s]).value) or 0) for s in sem_labels if s in col_map)
            if (op or tot or sem_sum) and any(_to_num(v) for v in row_vals.values()):
                is_summary = True

        rec: Dict[str, Any] = {
            "row": r,
            "구분": ws.cell(r, col_map["구분"]).value if "구분" in col_map else None,
            "교과군": ws.cell(r, col_map["교과군"]).value if "교과군" in col_map else None,
            "과목유형": ws.cell(r, col_map["과목유형"]).value if "과목유형" in col_map else None,
            "과목명": sname,
            "기준학점": _to_num(ws.cell(r, col_map["기준학점"]).value) if "기준학점" in col_map else None,
            "운영학점": _to_num(ws.cell(r, col_map["운영학점"]).value) if "운영학점" in col_map else None,
            "비고": ws.cell(r, col_map["비고"]).value if "비고" in col_map else None,
            "이수학점": _to_num(ws.cell(r, col_map["이수학점"]).value) if "이수학점" in col_map else None,
            "필수이수학점": _to_num(ws.cell(r, col_map["필수이수학점"]).value) if "필수이수학점" in col_map else None,
        }
        for sl in sem_labels:
            rec[sl] = _to_num(ws.cell(r, col_map[sl]).value) if sl in col_map else None
        rec["학기합"] = sum((rec[sl] or 0) for sl in sem_labels)

        if is_summary:
            rec["label"] = (sname or first_two or "").strip()
            summary.append(rec)
        elif sname:
            subjects.append(rec)

    df = pd.DataFrame(subjects)

    return {
        "meta": meta,
        "col_map": col_map,
        "subjects": subjects,
        "summary": summary,
        "notes": notes,
        "dataframe": df,
        "semester_labels": sem_labels,
    }
