import streamlit as st
import pandas as pd

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="교육과정 배당표 자동 검토", layout="wide")

# --- 1. 사이드바: 학교별 자체 제약 조건 설정 ---
with st.sidebar:
    st.header("⚙️ 학교별 자체 제약 조건 설정")
    st.markdown("표 하단의 '유의사항'에 해당하는 예외 규칙을 설정하세요.")
    
    # 예시 1: 대일고 유의사항 반영
    max_choice_2nd = st.number_input(
        "2학년 국/수/영 학기당 최대 선택 과목 수", 
        min_value=1, max_value=5, value=1
    )
    
    # 예시 2: 3학년 선택 과목 제약
    max_choice_3rd = st.number_input(
        "3학년 융합/진로/전문 학기당 최대 선택 과목 수", 
        min_value=1, max_value=5, value=1
    )
    
    st.divider()
    st.markdown("※ 이 설정값은 업로드된 모든 엑셀 파일의 시뮬레이션 계산(계산 레이어)에 반영됩니다.")

# --- 2. 메인 화면: 파일 업로드 ---
st.title("📊 고교학점제 교육과정 배당표 자동 검토 시스템")
st.write("여러 학교의 엑셀 파일(.xlsx)을 한 번에 업로드하여 국가 교육과정 지침 및 자체 제약 조건을 검토합니다.")

# accept_multiple_files=True 로 설정하여 다중 업로드 지원
uploaded_files = st.file_uploader(
    "학점 배당표 엑셀 파일 업로드", 
    type=['xlsx'], 
    accept_multiple_files=True
)

# --- 3. 데이터 처리 및 검토 로직 ---
if uploaded_files:
    st.success(f"총 {len(uploaded_files)}개의 파일이 업로드되었습니다. 검토를 시작합니다.")
    
    for file in uploaded_files:
        # 각 파일별로 Expander(토글)를 생성하여 결과 분리
        with st.expander(f"🏫 {file.name} 검토 결과", expanded=True):
            try:
                # 엑셀 파일 읽기 (메모리 상에서만 처리되므로 개인정보/보안에 안전)
                # 앞서 논의한 대로 Header 위치나 병합 셀 처리(ffill)가 중요합니다.
                df_raw = pd.read_excel(file, header=None) 
                
                # ---------------------------------------------------------
                # [TODO] 이곳에 데이터 클렌징 및 2-Layer 분리 로직이 들어갑니다.
                # 1. df_raw 텍스트 기반 오탈자 검사 (원시 레이어)
                # 2. 병합 셀 해체 및 학점 숫자로 변환 -> df_computed 생성 (계산 레이어)
                # ---------------------------------------------------------
                
                # --- 임시 결과 UI (검토 로직 완성 시 대체) ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("1차 관문: 총 이수 학점 검증")
                    # 하단 집계표 검증 결과 출력 예시
                    st.info("✅ 총 이수 학점 192학점 충족")
                    st.info("✅ 교과(군) 필수 이수 84학점 충족")
                    
                with col2:
                    st.subheader("2차 관문: 세부 지침 및 제약 검증")
                    # 사이드바 변수를 활용한 국영수 81학점 초과 검사 등
                    st.warning("⚠️ 국·수·영 81학점 초과 여부: 시뮬레이션 결과 82학점 도출 가능성 있음 (확인 필요)")
                    st.success(f"✅ 2학년 최대 선택 과목 수({max_choice_2nd}과목) 제한 충족")
                
                st.write("미리보기 (원시 데이터의 일부):")
                st.dataframe(df_raw.head())
                
            except Exception as e:
                st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
