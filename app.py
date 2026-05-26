"""
교육과정 편성 자율점검 Streamlit 앱 (v5)
- 다중 파일 업로드
- 통합 점검 결과 표시
- 엑셀(.xlsx) 다운로드 (요약 + 학교별 시트)
"""
from __future__ import annotations
import io
import traceback
from collections import Counter
import pandas as pd
import streamlit as st

from parser import parse_excel
from checker import run_checks


# ====================== 페이지 설정 ======================
st.set_page_config(
    page_title="교육과정 편성 자율점검",
    page_icon="📘",
    layout="wide",
)

st.title("📘 교육과정 편성 자율점검")
st.caption("2022 개정 교육과정 기준 · 21개 점검 항목 자동 분석")


# ====================== 헬퍼 ======================
STATUS_COLOR = {
    "PASS":   "#16a34a",
    "FAIL":   "#dc2626",
    "CHECK":  "#d97706",
    "MANUAL": "#2563eb",
    "N/A":    "#6b7280",
    "ERROR":  "#7c3aed",
}


def status_badge_html(s: str) -> str:
    color = STATUS_COLOR.get(s, "#6b7280")
    return (
        f'<span style="display:inline-block;padding:2px 8px;'
        f'border-radius:4px;background:{color};color:#fff;'
        f'font-size:12px;font-weight:600;">{s}</span>'
    )


def render_results_table(df: pd.DataFrame, status_col: str = "상태"):
    """pandas 버전 호환 + HTML 폴백"""
    def color_status(v):
        return f"color: {STATUS_COLOR.get(v, '#111')}; font-weight: 600;"

    try:
        styler = df.style
        if hasattr(styler, "map"):
            styled = styler.map(color_status, subset=[status_col])
        else:
            styled = styler.applymap(color_status, subset=[status_col])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    except Exception:
        # 폴백: HTML 배지로 렌더
        df2 = df.copy()
        df2[status_col] = df2[status_col].map(status_badge_html)
        st.write(df2.to_html(escape=False, index=False), unsafe_allow_html=True)


def build_excel_bytes(per_file_results: list[dict]) -> bytes:
    """
    여러 학교 점검 결과를 1개의 .xlsx로 패키징
    - '요약' 시트: 학교별 PASS/FAIL/CHECK 카운트
    - '전체결과' 시트: 모든 결과 통합
    - 학교별 시트: 개별 점검 결과
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1) 요약
        summary_rows = []
        for item in per_file_results:
            name = item["file"]
            meta = item.get("meta", {})
            if item.get("error"):
                summary_rows.append({
                    "파일명": name,
                    "학교명": "",
                    "입학년도": "",
                    "오류": item["error"][:200],
                })
                continue
            counts = Counter(r["상태"] for r in item["results"])
            summary_rows.append({
                "파일명": name,
                "학교명": meta.get("학교명", ""),
                "입학년도": meta.get("입학년도", ""),
                "교과총학점": item.get("교과총학점", ""),
                "창체학점": item.get("창체학점", ""),
                "총학점": item.get("총학점", ""),
                "PASS": counts.get("PASS", 0),
                "FAIL": counts.get("FAIL", 0),
                "CHECK": counts.get("CHECK", 0),
                "MANUAL": counts.get("MANUAL", 0),
                "N/A": counts.get("N/A", 0),
                "ERROR": counts.get("ERROR", 0),
            })
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name="요약", index=False)

        # 2) 전체 결과 통합
        all_rows = []
        for item in per_file_results:
            if item.get("error"):
                continue
            for r in item["results"]:
                all_rows.append({
                    "파일명": item["file"],
                    "학교명": item.get("meta", {}).get("학교명", ""),
                    **r,
                })
        if all_rows:
            pd.DataFrame(all_rows).to_excel(writer, sheet_name="전체결과", index=False)

        # 3) 학교별 시트
        used_names = set()
        for item in per_file_results:
            if item.get("error"):
                continue
            base = item.get("meta", {}).get("학교명") or item["file"]
            base = str(base)[:25].replace("/", "_").replace("\\", "_").replace("?", "")
            for ch in ["*", "[", "]", ":"]:
                base = base.replace(ch, "")
            # 시트명 중복 방지
            name = base
            i = 2
            while name in used_names or name in {"요약", "전체결과"}:
                name = f"{base[:23]}_{i}"
                i += 1
            used_names.add(name)
            pd.DataFrame(item["results"]).to_excel(writer, sheet_name=name, index=False)

            # 비고/유의사항 보조 시트
            notes = item.get("notes", [])
            if notes:
                note_sheet = f"{name[:23]}_비고"
                pd.DataFrame({"내용": notes}).to_excel(writer, sheet_name=note_sheet, index=False)

    output.seek(0)
    return output.getvalue()


def process_one(filename: str, file_bytes: bytes) -> dict:
    """파일 1개 파싱 + 점검 실행"""
    try:
        bio = io.BytesIO(file_bytes)
        parsed = parse_excel(bio)
        results = run_checks(parsed)

        # 메트릭용 보조 데이터
        subj_total = sum(s.get("운영학점", 0) for s in parsed["subjects"])
        ca = 0.0
        for s in parsed.get("summary_rows", []):
            nm = str(s.get("과목명", ""))
            if "창의적 체험활동" in nm or "창체" in nm:
                ca = s.get("운영학점", 0) or s.get("학기합계", 0)
                break

        return {
            "file": filename,
            "meta": parsed.get("메타데이터", {}),
            "parsed": parsed,
            "results": results,
            "notes": parsed.get("notes", []),
            "subjects": parsed.get("subjects", []),
            "교과총학점": round(subj_total, 1),
            "창체학점": round(ca, 1),
            "총학점": round(subj_total + ca, 1),
            "error": None,
        }
    except Exception as e:
        return {
            "file": filename,
            "meta": {},
            "results": [],
            "notes": [],
            "subjects": [],
            "error": f"{type(e).__name__}: {e}",
            "trace": traceback.format_exc(),
        }


# ====================== 사이드바 ======================
with st.sidebar:
    st.header("사용 안내")
    st.markdown(
        "- 학교별 학점 배당표 엑셀(.xlsx)을 **여러 개** 업로드할 수 있습니다.\n"
        "- 21개 점검 항목이 각 파일별로 자동 실행됩니다.\n"
        "- 결과는 **엑셀 파일**로 다운로드 가능합니다.\n\n"
        "**상태 라벨**\n"
        "- PASS: 자동 점검 통과\n"
        "- FAIL: 명백한 미준수\n"
        "- CHECK: 추가 확인 필요\n"
        "- MANUAL: 수동 점검 항목\n"
        "- N/A: 해당 없음"
    )


# ====================== 메인 ======================
uploaded_files = st.file_uploader(
    "학점 배당표 엑셀 파일을 업로드하세요 (다중 선택 가능)",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("좌측 또는 위 영역에서 엑셀 파일을 업로드해 주세요.")
    st.stop()

# 모든 파일 처리
st.write(f"### 📂 업로드된 파일: {len(uploaded_files)}개")
per_file_results = []
progress = st.progress(0.0, text="파싱 시작…")
for i, uf in enumerate(uploaded_files, 1):
    progress.progress(i / len(uploaded_files), text=f"({i}/{len(uploaded_files)}) {uf.name} 처리 중…")
    per_file_results.append(process_one(uf.name, uf.getvalue()))
progress.empty()

# ====================== 통합 요약 ======================
st.subheader("📊 통합 요약")
sum_rows = []
for item in per_file_results:
    if item.get("error"):
        sum_rows.append({
            "파일명": item["file"], "학교명": "", "총학점": "",
            "PASS": "", "FAIL": "", "CHECK": "", "MANUAL": "", "N/A": "",
            "오류": item["error"][:80],
        })
        continue
    cnt = Counter(r["상태"] for r in item["results"])
    sum_rows.append({
        "파일명": item["file"],
        "학교명": item["meta"].get("학교명", ""),
        "총학점": item["총학점"],
        "PASS": cnt.get("PASS", 0),
        "FAIL": cnt.get("FAIL", 0),
        "CHECK": cnt.get("CHECK", 0),
        "MANUAL": cnt.get("MANUAL", 0),
        "N/A": cnt.get("N/A", 0),
        "오류": "",
    })
df_sum = pd.DataFrame(sum_rows)
st.dataframe(df_sum, use_container_width=True, hide_index=True)

# 전체 합산 메트릭
ok_files = [x for x in per_file_results if not x.get("error")]
err_files = [x for x in per_file_results if x.get("error")]
c1, c2, c3, c4 = st.columns(4)
c1.metric("처리 성공", f"{len(ok_files)}건")
c2.metric("처리 실패", f"{len(err_files)}건")
total_fail = sum(Counter(r["상태"] for r in x["results"]).get("FAIL", 0) for x in ok_files)
total_check = sum(Counter(r["상태"] for r in x["results"]).get("CHECK", 0) for x in ok_files)
c3.metric("총 FAIL 건수", total_fail)
c4.metric("총 CHECK 건수", total_check)

# ====================== 엑셀 다운로드 버튼 ======================
st.markdown("---")
xlsx_bytes = build_excel_bytes(per_file_results)
st.download_button(
    label="📥 점검 결과 엑셀 다운로드",
    data=xlsx_bytes,
    file_name="교육과정_점검결과.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    use_container_width=True,
)

# ====================== 파일별 상세 ======================
st.markdown("---")
st.subheader("📑 파일별 상세 결과")

tab_labels = []
for x in per_file_results:
    label = x["meta"].get("학교명") or x["file"]
    if x.get("error"):
        label = "⚠ " + label
    tab_labels.append(label[:30])

tabs = st.tabs(tab_labels)
for tab, item in zip(tabs, per_file_results):
    with tab:
        st.markdown(f"**파일명:** `{item['file']}`")
        if item.get("error"):
            st.error(f"파싱/점검 중 오류 발생: {item['error']}")
            with st.expander("오류 상세 보기"):
                st.code(item.get("trace", ""))
            continue

        meta = item["meta"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("학교명", meta.get("학교명", "—"))
        m2.metric("입학년도", meta.get("입학년도", "—"))
        m3.metric("교과 총학점", f"{item['교과총학점']:.0f}")
        m4.metric("창체 학점", f"{item['창체학점']:.0f}")

        # 점검 결과
        df_res = pd.DataFrame(item["results"])
        render_results_table(df_res)

        # 비고/유의사항
        if item["notes"]:
            with st.expander(f"비고/유의사항 ({len(item['notes'])}건)"):
                for n in item["notes"]:
                    st.markdown(f"- {n}")

        # 과목 미리보기
        with st.expander(f"추출 과목 미리보기 ({len(item['subjects'])}개)"):
            if item["subjects"]:
                df_subj = pd.DataFrame(item["subjects"])
                cols = [c for c in ["교과영역", "교과군", "과목유형", "과목명",
                                     "기준학점", "운영학점", "필수이수학점", "비고"]
                         if c in df_subj.columns]
                st.dataframe(df_subj[cols], use_container_width=True, hide_index=True)
