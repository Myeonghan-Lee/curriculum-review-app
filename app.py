"""
교육과정 편성 자율점검 도구 - Streamlit App
"""
import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from parser import parse_curriculum, extract_subject_records
from checker import CurriculumChecker

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="교육과정 편성 자율점검 도구",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.title("교육과정 점검 도구")
    st.caption("2022 개정 교육과정 기준")
    st.divider()

    st.subheader("사용 방법")
    st.markdown(
        "1. 학점 배당표 엑셀 파일 업로드\n"
        "2. 자동 점검 결과 확인\n"
        "3. 비고/유의사항 수동 검토\n"
        "4. 결과 CSV 다운로드"
    )

    st.divider()
    st.subheader("점검 항목")
    st.markdown(
        "- A. 학점 총량 (5개)\n"
        "- B. 학기별 배분 (3개)\n"
        "- C. 과목별 학점 (3개)\n"
        "- D. 교과군별 (2개)\n"
        "- E. 순서/위계 (2개)\n"
        "- F. 과목명/형식 (3개)\n"
        "- G. 정성적 점검 (3개)"
    )

    st.divider()
    st.caption("기준 문서:")
    st.caption("- 교육과정 편성 자율점검표")
    st.caption("- 2022 개정 국가 교육과정")

# ============================================================
# 메인
# ============================================================
st.title("교육과정 편성 자율점검 도구")
st.markdown(
    "2022 개정 교육과정 기준 **21개 자율점검 항목**을 자동/반자동으로 검증합니다."
)

uploaded = st.file_uploader(
    "학점 배당표 엑셀 파일 (.xlsx)",
    type=["xlsx"],
    help="단위학교 학점 배당표 엑셀 파일을 업로드하세요.",
)

if not uploaded:
    st.info("좌측에서 파일을 업로드하면 점검이 시작됩니다.")
    st.stop()

# 임시 파일로 저장 후 파싱
with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
    tmp.write(uploaded.getvalue())
    tmp_path = tmp.name

try:
    parsed = parse_curriculum(tmp_path)
    records = extract_subject_records(parsed)
except Exception as e:
    st.error(f"파일 파싱 실패: {e}")
    st.stop()

# ============================================================
# 메타데이터 표시
# ============================================================
meta = parsed["metadata"]
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("학교명", meta.get("school") or "미감지")
with col2:
    st.metric("입학년도", meta.get("year") or "미감지")
with col3:
    st.metric("과목 수", len(records))
with col4:
    total = sum(r["총학점"] for r in records)
    st.metric("교과 총학점", f"{total:.0f}")

st.divider()

# ============================================================
# 점검 실행
# ============================================================
checker = CurriculumChecker(parsed, records)
results = checker.run_all()

# 상태 집계
pass_n = sum(1 for r in results if r["상태"] == "PASS")
fail_n = sum(1 for r in results if r["상태"] == "FAIL")
check_n = sum(1 for r in results if r["상태"] == "CHECK")
info_n = sum(1 for r in results if r["상태"] in ("INFO", "N/A"))

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("PASS", pass_n, help="자동 검증 통과")
with col2:
    st.metric("FAIL", fail_n, help="기준 미달 (수정 필요)")
with col3:
    st.metric("CHECK", check_n, help="수동 확인 필요")
with col4:
    st.metric("INFO / N/A", info_n, help="참고 / 해당 없음")

# ============================================================
# 탭
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs(
    ["점검 결과", "과목별 데이터", "비고/유의사항", "원본 데이터"]
)

with tab1:
    st.subheader("21개 항목 점검 결과")

    df_results = pd.DataFrame(results)

    def style_status(val):
        colors = {
            "PASS": "background-color: #d1fae5; color: #065f46",
            "FAIL": "background-color: #fee2e2; color: #991b1b",
            "CHECK": "background-color: #fef3c7; color: #92400e",
            "INFO": "background-color: #dbeafe; color: #1e40af",
            "N/A": "background-color: #f3f4f6; color: #6b7280",
        }
        return colors.get(val, "")

    styled = df_results.style.applymap(style_status, subset=["상태"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    csv = df_results.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "점검 결과 CSV 다운로드",
        data=csv,
        file_name=f"점검결과_{meta.get('school','')}_{meta.get('year','')}.csv",
        mime="text/csv",
    )

with tab2:
    st.subheader("과목별 학점 데이터")
    rows = []
    for r in records:
        row = {
            "교과군": r["교과군"],
            "과목명": r["과목명"],
            "총학점": r["총학점"],
        }
        row.update(r["학기별"])
        rows.append(row)
    df_sub = pd.DataFrame(rows)
    st.dataframe(df_sub, use_container_width=True, hide_index=True)

    st.markdown("**교과(군)별 총학점 합계**")
    from checker import get_group
    from collections import defaultdict
    group_total = defaultdict(float)
    for r in records:
        g = get_group(r["과목명"]) or r["교과군"] or "기타"
        group_total[g] += r["총학점"]
    df_group = pd.DataFrame(
        [{"교과군": k, "총학점": v} for k, v in group_total.items()]
    ).sort_values("총학점", ascending=False)
    st.dataframe(df_group, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("비고 및 유의사항 (수동 점검 항목)")
    notes = parsed.get("notes", [])
    if not notes:
        st.info("추출된 비고/유의사항이 없습니다.")
    else:
        for i, note in enumerate(notes, 1):
            st.markdown(f"**{i}.** {note}")

with tab4:
    st.subheader("원본 엑셀 데이터")
    st.markdown(f"- 헤더 행: {parsed['header_row']}")
    st.markdown(f"- 요약 영역 시작: {parsed['summary_start']}")
    st.markdown(f"- 학기 컬럼: {', '.join(parsed['semester_cols'])}")

    with st.expander("전체 원본 보기"):
        st.dataframe(parsed["raw"], use_container_width=True)

# 임시 파일 삭제
Path(tmp_path).unlink(missing_ok=True)
