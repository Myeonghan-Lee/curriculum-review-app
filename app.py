# app.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="고교학점제 배당표 자동 검토기", layout="wide")

st.title("📊 2022 개정 교육과정 학점 배당표 자동 검토 시스템")
st.markdown("여러 학교의 엑셀 배당표를 업로드하면 국가 교육과정 지침에 맞춰 자동으로 검증합니다.")

# 다중 파일 업로드 컴포넌트
uploaded_files = st.file_uploader("검토할 엑셀 파일(.xlsx)들을 모두 올려주세요.", type=['xlsx'], accept_multiple_files=True)

if uploaded_files:
    for file in uploaded_files:
        st.subheader(f"🏫 {file.name} 검토 결과")
        
        # 1. 원시 데이터(Raw Layer) 로드
        # header 파라미터는 실제 엑셀 표의 시작 행에 맞춰 조정 필요
        raw_df = pd.read_excel(file, engine='openpyxl')
        
        # 병합 셀 처리를 위한 Forward Fill 적용
        raw_df[['구분', '교과(군)', '과목 유형']] = raw_df[['구분', '교과(군)', '과목 유형']].ffill()
        
        # 데이터 처리 및 검토 함수 호출 (아래 3단계 참조)
        # computed_df = process_computed_layer(raw_df)
        # results = run_rule_engine(computed_df)
        
        # UI에 결과 출력
        st.write("✅ 검토 완료 (샘플 UI)")
        st.dataframe(raw_df.head(5)) # 임시로 상위 5개 행만 출력

import re

def parse_selection_credits(credit_str):
    """
    '12 (택4)' 형태의 문자열을 파싱하여 (총학점, 선택과목수, 개별학점)을 반환합니다.
    """
    if pd.isna(credit_str) or not isinstance(credit_str, str):
        return None, None, None
    
    match = re.search(r'(\d+)\s*\(택(\d+)\)', credit_str)
    if match:
        total_credits = int(match.group(1))
        select_count = int(match.group(2))
        single_credit = total_credits / select_count
        return total_credits, select_count, single_credit
    return None, None, None

def process_computed_layer(raw_df):
    """
    병합된 선택 과목 셀을 해체하고, 시뮬레이션용 플랫 데이터를 생성합니다.
    (실제 구현 시에는 엑셀의 구조에 맞게 컬럼명을 매핑하는 세밀한 작업이 필요합니다.)
    """
    computed_df = raw_df.copy()
    # TODO: 학기별 열을 순회하며 parse_selection_credits 적용 및 숫자 데이터로 변환
    return computed_df

def run_rule_engine(computed_df):
    report = []
    
    # 룰 1: 국영수 81학점 초과 금지 검토 (공통과목 + 최대 선택 가능 학점 시뮬레이션)
    kme_credits = calculate_max_kme_credits(computed_df) # 별도 구현 필요
    if kme_credits > 81:
        report.append(f"❌ 국영수 교과 이수 학점 총합 초과: {kme_credits}학점 (기준 81학점)")
    else:
        report.append(f"✅ 국영수 이수 학점 적합 ({kme_credits}학점)")

    # 룰 2: 체육 교과 매 학기 편성 검토
    pe_status = check_pe_every_semester(computed_df) # 별도 구현 필요
    if not pe_status:
         report.append("❌ 체육 교과가 미편성된 학기가 존재합니다. (매 학기 편성 필수)")
    else:
         report.append("✅ 체육 교과 매 학기 편성 충족")
         
    return report
