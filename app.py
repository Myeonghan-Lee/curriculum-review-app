"""
app.py
2022 개정 고등학교 교육과정 편성 자율점검 Streamlit 앱
"""
import streamlit as st
import pandas as pd
import io
from parser import parse_excel
from checker import CurriculumChecker

st.set_page_config(
    page_title="고교 교육과정 자율점검",
    page_icon="📋",
    layout="wide",
)

# ───── 스타일 ─────
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stMetric { background: #f8fafc; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; }
    .badge-pass { background:#dcfce7; color:#166534; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-fail { background:#fee2e2; color:#991b1b; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-check{ background:#fef3c7; color:#92400e; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-manual{background:#dbeafe; color:#1e40af; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    .badge-na   {background:#f1f5f9; color:#475569; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:600; }
    table { font-size: 14px; }
    th { background: #f8fafc !important; text-align: left !important; }
</style>
""", unsafe_allow_html=True)

st.title("고교 교육과정 편성 자율점검 도구")
st.caption("2022 개정 교육과정 기준 · 21개 점검항목 자동 분석")

# ───── 사이드바 ─────
with st.sidebar:
    st.header("파일 업로드")
    uploaded = st.file_uploader(
        "학점 배당표 엑셀(.xlsx)을 업로드하세요",
        type=["xlsx"],
        help="2022 개정 교육과정 학점 배당표 형식 지원",
    )
    st.divider()
    st.markdown("### 점검 기준")
    st.markdown(
        "- 총 이수학점 ≥ 192\n"
        "- 필수 이수학점 ≥ 84\n"
        "- 창의적 체험활동 ≥ 18\n"
        "- 과목별 학점 증감범위 준수\n"
        "- 한국사 3+3=6학점\n"
        "- 체육 매학기 + 10학점 이상\n"
        "- 공통→선택 위계 준수"
    )
    st.divider()
    st.caption("Made with Streamlit")


def badge_html(status: str) -> str:
    """상태값을 HTML 배지로 변환"""
    s = str(status).strip().upper()
    cls = {
        "PASS": "badge-pass",
        "FAIL": "badge-fail",
        "CHECK": "badge-check",
        "MANUAL": "badge-manual",
        "N/A": "badge-na",
    }.get(s, "badge-check")
    return f'<span class="{cls}">{s}</span>'


def style_status_color(val):
    """Styler용 셀 배경색 함수 (Styler.map 호환)"""
    s = str(val).strip().upper()
    color_map = {
        "PASS":   "background-color: #dcfce7; color: #166534; font-weight: 600;",
        "FAIL":   "background-color: #fee2e2; color: #991b1b; font-weight: 600;",
        "CHECK":  "background-color: #fef3c7; color: #92400e; font-weight: 600;",
        "MANUAL": "background-color: #dbeafe; color: #1e40af; font-weight: 600;",
        "N/A":    "background-color: #f1f5f9; color: #475569; font-weight: 600;",
    }
    return color_map.get(s, "")


def render_styled_table(df: pd.DataFrame, status_col: str = "상태"):
    """
    pandas 버전에 따라 Styler.map (>=2.1) 또는 applymap (<2.1) 안전 사용.
    실패 시 HTML 폴백.
    """
    try:
        styler = df.style
        if hasattr(styler, "map"):
            # pandas 2.1+
            styled = styler.map(style_status_color, subset=[status_col])
        else:
            # pandas <2.1
            styled = styler.applymap(style_status_color, subset=[status_col])
        return styled
    except Exception:
        return None


if uploaded is None:
    st.info("좌측 사이드바에서 엑셀 파일을 업로드하면 자동 분석이 시작됩니다.")
    st.markdown("### 사용 방법")
    st.markdown(
        "1. 사이드바에서 2022 개정 교육과정 학점 배당표 엑셀을 업로드합니다.\n"
        "2. 자동 파싱 후 21개 점검항목 결과가 표시됩니다.\n"
        "3. **상세결과 / 과목목록 / 유의사항 / 원본데이터** 탭에서 결과를 확인하세요.\n"
        "4. 결과는 CSV/Excel로 다운로드 가능합니다."
    )
    st.stop()


# ───── 분석 실행 ─────
with st.spinner("엑셀 파싱 및 점검 중..."):
    try:
        bio = io.BytesIO(uploaded.getvalue())
        parsed = parse_excel(bio)
    except Exception as e:
        st.error(f"엑셀 파싱 실패: {e}")
        st.exception(e)
        st.stop()

    try:
        checker = CurriculumChecker(parsed)
        results_df = checker.run_all()
        notes = checker.check_notes()
    except Exception as e:
        st.error(f"점검 로직 실행 실패: {e}")
        st.exception(e)
        st.stop()


# ───── 헤더 메트릭 ─────
meta = parsed.get("metadata", {})
col1, col2, col3, col4 = st.columns(4)
col1.metric("학교", meta.get("학교명") or "-")
col2.metric("입학년도", meta.get("입학년도") or "-")
subjects_df = parsed.get("subjects", pd.DataFrame())
col3.metric("과목 수", len(subjects_df))
total = 0
if "운영학점_계산" in subjects_df.columns:
    try:
        total = pd.to_numeric(subjects_df["운영학점_계산"], errors="coerce").fillna(0).sum()
    except Exception:
        total = 0
col4.metric("교과 합계", f"{total:.0f}학점")

# ───── 점검 결과 요약 ─────
st.subheader("점검 결과 요약")
if "상태" in results_df.columns:
    status_count = results_df["상태"].astype(str).str.upper().value_counts().to_dict()
else:
    status_count = {}
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("PASS", status_count.get("PASS", 0))
c2.metric("FAIL", status_count.get("FAIL", 0))
c3.metric("CHECK", status_count.get("CHECK", 0))
c4.metric("MANUAL", status_count.get("MANUAL", 0))
c5.metric("N/A", status_count.get("N/A", 0))

# ───── 탭 ─────
tab1, tab2, tab3, tab4 = st.tabs(["상세 결과", "과목 목록", "유의사항", "원본 데이터"])

with tab1:
    st.markdown("### 21개 점검항목 결과")

    # 1차 시도: Styler 기반 (pandas 버전 자동 분기)
    styled = render_styled_table(results_df, status_col="상태") if "상태" in results_df.columns else None

    if styled is not None:
        try:
            st.dataframe(styled, use_container_width=True, height=600)
        except Exception:
            # 2차 폴백: HTML 변환
            disp = results_df.copy()
            if "상태" in disp.columns:
                disp["상태"] = disp["상태"].apply(badge_html)
            st.markdown(disp.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        # Styler 사용 불가 시 HTML 배지로 직접 렌더링
        disp = results_df.copy()
        if "상태" in disp.columns:
            disp["상태"] = disp["상태"].apply(badge_html)
        st.markdown(disp.to_html(escape=False, index=False), unsafe_allow_html=True)

    st.download_button(
        label="점검결과 CSV 다운로드",
        data=results_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"점검결과_{meta.get('학교명') or '학교'}.csv",
        mime="text/csv",
    )

with tab2:
    st.markdown("### 과목별 학점 배당")
    show_cols = [c for c in subjects_df.columns if "_num" not in str(c)]
    st.dataframe(subjects_df[show_cols], use_container_width=True, height=500)

    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        results_df.to_excel(writer, sheet_name="점검결과", index=False)
        subjects_df[show_cols].to_excel(writer, sheet_name="과목목록", index=False)
    st.download_button(
        label="분석결과 Excel 다운로드",
        data=out.getvalue(),
        file_name=f"분석결과_{meta.get('학교명') or '학교'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with tab3:
    st.markdown("### 비고 및 유의사항 (수동 점검)")
    if notes:
        for i, n in enumerate(notes, 1):
            st.markdown(f"**{i}.** {n}")
    else:
        st.info("추출된 유의사항이 없습니다.")

with tab4:
    st.markdown("### 원본 데이터 (병합셀 해제 후)")
    raw = parsed.get("raw")
    if raw is not None:
        st.dataframe(raw, use_container_width=True, height=500)
    else:
        st.info("원본 데이터가 없습니다.")

st.divider()
st.caption("본 도구는 자동 점검 보조 도구이며, 최종 확정은 학교 교육과정위원회의 검토가 필요합니다.")
