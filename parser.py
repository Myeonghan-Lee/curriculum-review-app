"""
교육과정 학점배당표 엑셀 파서 v4
- 다중 시트 자동 선택
- 병합 셀 해제 + forward-fill
- 헤더 키워드 정규화 (번호 접두사/줄바꿈 제거)
- 학기 헤더 자동 합성 ("1-1" ~ "3-2")
"""
from __future__ import annotations
import re
from io import BytesIO
from typing import Any
import openpyxl
from openpyxl.utils import get_column_letter


def _norm(v: Any) -> str:
    """헤더 비교용 정규화: 공백/줄바꿈/번호접두사/특수기호 제거"""
    if v is None:
        return ""
    s = str(v)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^[\(\[]?\d+[\)\]\.]\s*", "", s)
    return s


def _to_num(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return 0.0
    m = re.match(r"^\s*(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else 0.0


def _unmerge_and_fill(ws):
    """병합 셀 해제하고 좌상단 값을 모든 셀에 채워넣음"""
    ranges = list(ws.merged_cells.ranges)
    for mr in ranges:
        min_col, min_row, max_col, max_row = mr.min_col, mr.min_row, mr.max_col, mr.max_row
        val = ws.cell(min_row, min_col).value
        ws.unmerge_cells(str(mr))
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(r, c).value = val


def _score_sheet(ws) -> tuple[int, int]:
    """헤더 점수 계산 후 (best_score, best_row) 반환"""
    keywords = ["구분", "교과", "과목유형", "과목", "기준학점", "운영학점",
                "필수이수학점", "1학년", "2학년", "3학년", "비고"]
    best_score, best_row = 0, -1
    max_row = min(ws.max_row, 30)
    max_col = min(ws.max_column, 30)
    for r in range(1, max_row + 1):
        row_vals = [_norm(ws.cell(r, c).value) for c in range(1, max_col + 1)]
        score = 0
        for kw in keywords:
            if any(kw in v for v in row_vals if v):
                score += 1
        if score > best_score:
            best_score = score
            best_row = r
    return best_score, best_row


def _select_best_sheet(wb):
    """모든 시트 중 헤더 점수가 가장 높은 시트를 선택"""
    diag = {}
    best = (None, -1, -1)  # (name, score, row)
    for name in wb.sheetnames:
        ws = wb[name]
        # 임시로 병합 해제 (점수 계산용) - 원본 ws 객체에 영향 주지만 어차피 곧 본격 처리
        _unmerge_and_fill(ws)
        score, row = _score_sheet(ws)
        diag[name] = score
        if score > best[1]:
            best = (name, score, row)
    return best[0], best[1], best[2], diag


def _find_header_row(ws) -> tuple[int, int]:
    """헤더 행 범위 탐지 (시작행, 끝행)"""
    score, row = _score_sheet(ws)
    if row < 0 or score < 3:
        raise ValueError(
            f"헤더 행을 찾지 못했습니다. (최고 점수={score}, 행={row}) "
            f"엑셀 상단 30행 안에 '구분/교과/과목/학점/학년' 키워드가 충분히 들어있는지 확인하세요."
        )
    # 보조 헤더(학기) 행이 바로 아래 있는지 확인
    end = row
    next_row_vals = [_norm(ws.cell(row + 1, c).value) for c in range(1, ws.max_column + 1)]
    if any(re.match(r"^[1-3]학기?$", v) or v in {"1", "2"} or "학기" in v for v in next_row_vals if v):
        end = row + 1
    # 추가로 한 행 더 (예: 학년-학기 분리 헤더)
    if end < row + 2:
        third = [_norm(ws.cell(end + 1, c).value) for c in range(1, ws.max_column + 1)]
        if any(v in {"1", "2"} for v in third if v):
            end = end + 1
    return row, end


def _build_col_map(ws, h_start: int, h_end: int) -> dict[str, int]:
    """헤더 텍스트 -> 컬럼 번호 매핑"""
    max_col = ws.max_column
    # 각 컬럼에 대해 헤더 영역의 모든 값을 합쳐서 보관
    col_texts = {}
    for c in range(1, max_col + 1):
        parts = []
        for r in range(h_start, h_end + 1):
            v = ws.cell(r, c).value
            if v is not None and str(v).strip():
                parts.append(_norm(v))
        col_texts[c] = "|".join(parts)

    # 매핑 우선순위 (긴 키워드부터, 충돌 방지)
    rules = [
        ("필수이수학점", ["필수이수학점"]),
        ("기준학점",   ["기준학점"]),
        ("운영학점",   ["운영학점"]),
        ("교과영역",   ["교과영역"]),
        ("교과군",     ["교과(군)", "교과군"]),
        ("구분",       ["구분"]),
        ("과목유형",   ["과목유형"]),
        ("과목명",     ["과목"]),     # 과목유형 매핑 후에 처리
        ("비고",       ["비고"]),
    ]
    col_map = {}
    used = set()

    def find_col(keywords, exclude_keys=()):
        for c, txt in col_texts.items():
            if c in used or not txt:
                continue
            if any(ex in txt for ex in exclude_keys):
                continue
            if any(kw in txt for kw in keywords):
                return c
        return None

    for key, kws in rules:
        # 과목명을 찾을 때 '과목유형'은 배제
        exclude = ("과목유형",) if key == "과목명" else ()
        c = find_col(kws, exclude_keys=exclude)
        if c is not None:
            col_map[key] = c
            used.add(c)

    return col_map


def _build_semester_cols(ws, h_start: int, h_end: int, used_cols: set[int]) -> dict[str, int]:
    """학기 컬럼 매핑: '1-1', '1-2', ..., '3-2'"""
    max_col = ws.max_column
    sem_cols: dict[str, int] = {}

    # 헤더 행들에서 학년/학기 정보 추출
    grade_row = {}   # col -> 학년(1/2/3)
    sem_row = {}     # col -> 학기(1/2)
    for c in range(1, max_col + 1):
        for r in range(h_start, h_end + 1):
            v = ws.cell(r, c).value
            if v is None:
                continue
            s = str(v)
            m = re.search(r"([1-3])\s*학년", s)
            if m:
                grade_row[c] = int(m.group(1))
            sm = re.search(r"([1-2])\s*학기", s)
            if sm:
                sem_row[c] = int(sm.group(1))
            elif s.strip() in ("1", "2") and c not in sem_row:
                sem_row[c] = int(s.strip())

    # 학년만 있고 학기가 없는 경우: 학년 셀 범위 내에서 1,2 분배
    # grade_row의 값이 같은 연속 컬럼을 찾고, 그 안에서 학기 컬럼 2개를 1,2로 매핑
    if grade_row:
        # 학년별로 컬럼 그룹화
        grade_to_cols: dict[int, list[int]] = {}
        for c, g in sorted(grade_row.items()):
            grade_to_cols.setdefault(g, []).append(c)

        for g in (1, 2, 3):
            cols = sorted(grade_to_cols.get(g, []))
            cols = [c for c in cols if c not in used_cols]
            if not cols:
                continue
            # 이 학년 컬럼 안에서 학기 1, 2 찾기
            s1 = next((c for c in cols if sem_row.get(c) == 1), None)
            s2 = next((c for c in cols if sem_row.get(c) == 2), None)
            if s1 is None and s2 is None and len(cols) >= 2:
                s1, s2 = cols[0], cols[1]
            elif s1 is None and len(cols) >= 1:
                s1 = cols[0]
            elif s2 is None and len(cols) >= 2:
                # s1이 있고 s2가 없으면 s1 다음 컬럼을 s2로
                idx = cols.index(s1)
                if idx + 1 < len(cols):
                    s2 = cols[idx + 1]
            if s1:
                sem_cols[f"{g}-1"] = s1
            if s2:
                sem_cols[f"{g}-2"] = s2

    return sem_cols


def parse_excel(file: BytesIO | str) -> dict:
    """엑셀 파일을 받아 표준화된 dict 반환"""
    wb = openpyxl.load_workbook(file, data_only=True)

    # 1. 최적 시트 선택
    best_name, best_score, _, diag = _select_best_sheet(wb)
    if best_name is None or best_score < 3:
        raise ValueError(
            f"헤더 행을 찾지 못했습니다. 시트별 진단 점수={diag}. "
            f"엑셀 상단 30행 안에 '구분/교과/과목/학점/학년' 키워드가 충분히 들어있는지 확인하세요."
        )
    ws = wb[best_name]

    # 2. 헤더 행 탐지
    h_start, h_end = _find_header_row(ws)

    # 3. 컬럼 매핑
    col_map = _build_col_map(ws, h_start, h_end)
    used_cols = set(col_map.values())
    sem_cols = _build_semester_cols(ws, h_start, h_end, used_cols)
    semester_labels = sorted(sem_cols.keys())

    # 4. 데이터 영역 추출
    data_start = h_end + 1
    subjects = []
    summary_rows = []
    notes = []
    data_end = data_start

    name_col = col_map.get("과목명")
    if not name_col:
        raise ValueError("'과목명' 컬럼을 찾지 못했습니다. col_map=" + str(col_map))

    for r in range(data_start, ws.max_row + 1):
        # 한 행 전체 값
        row_vals = {c: ws.cell(r, c).value for c in range(1, ws.max_column + 1)}
        name = row_vals.get(name_col)
        name_s = "" if name is None else str(name).strip()

        # 빈 행이면 종료 판단
        if not any(v is not None and str(v).strip() != "" for v in row_vals.values()):
            continue

        # 요약 행 감지
        is_summary = False
        if name_s:
            for kw in ["소계", "합계", "총계", "창의적 체험활동", "창체",
                       "이수학점", "이수 학점", "최소이수", "과목수"]:
                if kw in name_s:
                    is_summary = True
                    break

        # 유의사항/비고 텍스트만 있는 행
        if not is_summary and name_s.startswith(("※", "*", "-", "·")):
            notes.append(name_s)
            continue

        subj = {
            "행번호": r,
            "교과영역": row_vals.get(col_map.get("교과영역")) if col_map.get("교과영역") else None,
            "교과군":   row_vals.get(col_map.get("교과군"))   if col_map.get("교과군") else None,
            "구분":     row_vals.get(col_map.get("구분"))     if col_map.get("구분") else None,
            "과목유형": row_vals.get(col_map.get("과목유형")) if col_map.get("과목유형") else None,
            "과목명":   name_s,
            "기준학점": _to_num(row_vals.get(col_map.get("기준학점"))) if col_map.get("기준학점") else 0.0,
            "운영학점": _to_num(row_vals.get(col_map.get("운영학점"))) if col_map.get("운영학점") else 0.0,
            "필수이수학점": _to_num(row_vals.get(col_map.get("필수이수학점"))) if col_map.get("필수이수학점") else 0.0,
            "비고":     row_vals.get(col_map.get("비고")) if col_map.get("비고") else None,
        }
        # 학기별 학점
        sem_data = {}
        for lbl in semester_labels:
            col = sem_cols[lbl]
            sem_data[lbl] = _to_num(row_vals.get(col))
        subj["학기별학점"] = sem_data
        subj["학기합계"] = sum(sem_data.values())

        # 운영학점이 0이면 학기합계로 보완
        if subj["운영학점"] == 0 and subj["학기합계"] > 0:
            subj["운영학점"] = subj["학기합계"]

        if is_summary:
            summary_rows.append(subj)
        else:
            if name_s:
                subjects.append(subj)
                data_end = r

    # 5. 메타데이터 (학교명, 입학년도)
    meta = {"학교명": "", "입학년도": "", "교육과정": ""}
    for r in range(1, min(h_start, 10)):
        for c in range(1, min(ws.max_column + 1, 30)):
            v = ws.cell(r, c).value
            if v is None:
                continue
            s = str(v)
            m = re.search(r"([가-힣]+(?:고등학교|여자고등학교|여고|중학교))", s)
            if m and not meta["학교명"]:
                meta["학교명"] = m.group(1)
            ym = re.search(r"(20\d{2})\s*학년도", s)
            if ym and not meta["입학년도"]:
                meta["입학년도"] = ym.group(1)
            if "2022" in s and "개정" in s and not meta["교육과정"]:
                meta["교육과정"] = "2022 개정"

    # 6. 유의사항 추가 수집 (데이터 종료 이후 행들)
    for r in range(data_end + 1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            v = ws.cell(r, c).value
            if v is None:
                continue
            s = str(v).strip()
            if not s:
                continue
            if s.startswith(("※", "*", "-", "·")) or "유의" in s:
                if s not in notes:
                    notes.append(s)

    return {
        "sheet_name": best_name,
        "sheet_diag": diag,
        "header_range": (h_start, h_end),
        "data_range": (data_start, data_end),
        "semester_labels": semester_labels,
        "col_map": col_map,
        "sem_cols": sem_cols,
        "메타데이터": meta,
        "subjects": subjects,
        "summary_rows": summary_rows,
        "notes": notes,
    }
