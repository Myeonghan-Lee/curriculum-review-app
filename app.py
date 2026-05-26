"""
app.py - Streamlit 교육과정 점검 앱
"""
import io
import traceback
import pandas as pd
import streamlit as st

from parser import parse_excel
from checker import CurriculumChecker


st.set_page_config(
    page_title="교육과정 편성 자율점검",
    page_icon=None,
    layout="wide",
)


STATUS_COLORS = {
    "PASS":   ("#16a34a", "#dcfce7"),
    "FAIL":   ("#dc2626", "#fee2e2"),
    "CHECK":  ("#d97706", "#fef3c7"),
    "MANUAL": ("#2563eb", "#dbeafe"),
    "N/A":    ("#6b7280", "#f3f4f6"),
}


def status_badge(s: str) -> str:
    fg, bg = STATUS_COLORS.get(s, ("#111827", "#f3f4f6"))
    return f"<span style='background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-weight:600;font-size:12px'>{s}</span>"


def render_styled_table(df: pd.DataFrame, status_col: str = "상태"):
    """pandas 버전에 무관하게 표를 렌더."""
    def style_status_color(v):
        fg, bg = STATUS_COLORS.get(v, ("#111827", "#ffffff"))
        return f"background-color:{bg};color:{fg};font-weight:600"
    try:
        styler = df.style
        if hasattr(styler, "map"):
            styled = styler.map(style_status_color, subset=[status_col])
        else:
            styled = styler.applymap(style_status_color, subset=[status_col])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        return
    except Exception:
        pass
    # 폴백: HTML 직접
    html = df.copy()
    html[status_col] = html[status_col].map(status_badge)
    st.write(html.to_html(escape=False, index=False), unsafe_allow_html=True)


# ============ UI ============
st.title("교육과정 편성 자율점검")
st.caption("2022 개정 교육과정 학점 배당표(.xlsx)를 업로드하면 자율점검표 21개 항목을 자동 검토합니다.")

with st.sidebar:
    st.header("사용 안내")
    st.markdown(
        """
        1. **xlsx 파일 업로드**
        2. 자동 파싱 → 21개 점검 항목 확인
        3. 결과를 CSV로 다운로드 가능

        **점검 상태**
        - `PASS` 통과
        - `FAIL` 위반
        - `CHECK` 사용자 확인 필요
        - `MANUAL` 수동 점검 필요
        - `N/A` 해당 없음
        """
    )
    st.divider()
    st.markdown("**지원하는 헤더 형식**")
    st.code("구분 / 교과(군) / 1)과목유형 / 2)과목 /\n기준학점 / 운영학점 / 1~3학년(1·2학기) /\n3)비고 / 이수학점 / 필수이수학점")

uploaded = st.file_uploader("학점 배당표 엑셀 파일 선택", type=["xlsx"])

if uploaded is None:
    st.info("좌측 안내를 참고하여 xlsx 파일을 업로드하세요.")
    st.stop()

# ===== 파싱 =====
try:
    bio = io.BytesIO(uploaded.read())
    parsed = parse_excel(bio)
except Exception as e:
    st.error("엑셀 파싱 중 오류가 발생했습니다.")
    with st.expander("오류 상세"):
        st.code(traceback.format_exc())
    st.stop()

meta = parsed["meta"]
col1, col2, col3, col4 = st.columns(4)
col1.metric("학교", meta.get("school") or "-")
col2.metric("학년도", meta.get("year") or "-")
col3.metric("추출 과목 수", len(parsed["subjects"]))
col4.metric("요약 행 수", len(parsed["summary"]))

# ===== 점검 =====
checker = CurriculumChecker(parsed)
results = checker.run_all()
df_results = pd.DataFrame(results)

# 상태 분포
status_counts = df_results["상태"].value_counts().to_dict()
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("PASS", status_counts.get("PASS", 0))
m2.metric("FAIL", status_counts.get("FAIL", 0))
m3.metric("CHECK", status_counts.get("CHECK", 0))
m4.metric("MANUAL", status_counts.get("MANUAL", 0))
m5.metric("N/A", status_counts.get("N/A", 0))

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["점검 결과", "추출 과목", "요약 행", "유의사항/비고"])

with tab1:
    st.subheader("21개 점검 항목 결과")
    render_styled_table(df_results, status_col="상태")
    csv = df_results.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("결과 CSV 다운로드", csv,
                       file_name=f"점검결과_{meta.get('school') or 'school'}.csv",
                       mime="text/csv")

with tab2:
    st.subheader(f"추출된 과목 ({len(parsed['subjects'])}개)")
    df_sub = pd.DataFrame(parsed["subjects"])
    if not df_sub.empty:
        # 정리된 컬럼 순서
        cols = ["구분", "교과군", "과목유형", "과목명", "기준학점", "운영학점",
                "1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "학기합", "비고"]
        cols = [c for c in cols if c in df_sub.columns]
        st.dataframe(df_sub[cols], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("하단 요약 행")
    if parsed["summary"]:
        df_sum = pd.DataFrame(parsed["summary"])
        # label 컬럼이 있으면 앞으로
        if "label" in df_sum.columns:
            cols = ["label", "운영학점", "이수학점", "필수이수학점"] + [sl for sl in parsed["semester_labels"] if sl in df_sum.columns]
            cols = [c for c in cols if c in df_sum.columns]
            st.dataframe(df_sum[cols], use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_sum, use_container_width=True, hide_index=True)
    else:
        st.info("추출된 요약 행이 없습니다.")

with tab4:
    st.subheader("유의사항 / 비고 (수동 점검 대상)")
    if parsed["notes"]:
        for i, n in enumerate(parsed["notes"], 1):
            st.markdown(f"**{i}.** {n}")
    else:
        st.caption("유의사항 텍스트가 추출되지 않았습니다.")
    st.divider()
    st.markdown("**과목별 비고 추출**")
    subs_with_note = [s for s in parsed["subjects"] if s.get("비고")]
    if subs_with_note:
        df_n = pd.DataFrame([{"과목명": s["과목명"], "비고": s["비고"]} for s in subs_with_note])
        st.dataframe(df_n, use_container_width=True, hide_index=True)
    else:
        st.caption("과목별 비고가 비어있습니다.")
