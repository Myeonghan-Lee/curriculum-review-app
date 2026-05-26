import streamlit as st
import pandas as pd

from engine.excel_parser import load_curriculum_excel
from engine.normalizer import normalize_curriculum
from engine.validator import validate_curriculum
from engine.remark_parser import extract_manual_review

st.set_page_config(
    page_title="고등학교 교육과정 자동 검토",
    layout="wide"
)

st.title("고등학교 교육과정 자동 검토 시스템")

uploaded_file = st.file_uploader(
    "교육과정 엑셀 파일 업로드",
    type=["xlsx"]
)

if uploaded_file:
    st.success("파일 업로드 완료")
    with st.spinner("엑셀 분석 중..."):
        raw_df = load_curriculum_excel(uploaded_file)
        normalized_df = normalize_curriculum(raw_df)
        validation_result = validate_curriculum(normalized_df)
        manual_review = extract_manual_review(normalized_df)
    st.subheader("정규화 데이터")
    st.dataframe(normalized_df)
    st.subheader("자동 검토 결과")

    for item in validation_result:
        if item["status"] == "ERROR":
            st.error(item["message"])

        elif item["status"] == "WARNING":
            st.warning(item["message"])

        else:
            st.info(item["message"])

    st.subheader("수동 검토 필요 항목")

    if manual_review:
        st.dataframe(pd.DataFrame(manual_review))
    else:
        st.success("수동 검토 항목 없음")
