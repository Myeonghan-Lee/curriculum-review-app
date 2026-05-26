import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="교육과정 편제표 검토기", layout="wide")
st.title("🏫 교육과정 편제표 자동 검토 시스템")

# --- [새로 추가된 핵심 로직: 유연한 엑셀 읽기 함수] ---
def load_excel_robustly(file):
    import re
    
    # 1. 넉넉하게 맨 위 30줄을 읽어옵니다. (header=None으로 읽어 원본 구조 파악)
    temp_df = pd.read_excel(file, header=None, nrows=30)
    
    header_idx = -1 # 헤더를 찾았는지 확인하기 위한 초기값
    
    for i in range(len(temp_df)):
        # 셀의 결측치(NaN)를 빈 문자열로 바꾸고, 모든 공백(\s)을 완전히 제거하여 텍스트만 추출합니다.
        # 예: "구  분", "구\n분" -> "구분"으로 변환하여 검사
        row_values = [re.sub(r'\s+', '', str(val)) for val in temp_df.iloc[i].fillna('')]
        
        # '구분' 또는 '교과'라는 단어가 하나라도 있으면 해당 행을 헤더로 지정
        if any('구분' in val for val in row_values) or any('교과' in val for val in row_values):
            header_idx = i
            break
            
    # 🚨 헤더를 못 찾은 경우: 파이썬이 읽은 원본 엑셀 화면을 앱에 직접 띄워서 보여줍니다!
    if header_idx == -1:
        import streamlit as st
        st.error("❌ '구분'이나 '교과'라는 글자가 포함된 헤더 행을 상단 30줄에서 찾을 수 없습니다.")
        st.write("🔍 [디버깅] 현재 파이썬이 읽어들인 엑셀 상단 10줄 원본 데이터입니다:")
        st.dataframe(temp_df.head(10).astype(str))
        st.stop() # 여기서 앱 실행을 즉시 중단합니다.
        
    # 2. 찾은 헤더 행을 기준으로 데이터를 다시 제대로 읽습니다.
    df = pd.read_excel(file, header=header_idx)
    
    # 3. 컬럼명 정규화 (띄어쓰기, 줄바꿈, 괄호 등 특수문자 모두 제거)
    df.columns = [re.sub(r'[\s\(\)\n]', '', str(col)) for col in df.columns]
    
    # 4. '과목' 컬럼을 '과목명'으로 통일 (학교마다 다를 수 있으므로)
    if '과목' in df.columns and '과목명' not in df.columns:
        df.rename(columns={'과목': '과목명'}, inplace=True)
        
    return df

# --- [전처리 함수 수정 (정규화된 컬럼명 기준)] ---
def preprocess_curriculum(df):
    # 필수로 있어야 할 컬럼 확인 및 ffill
    core_cols = ['구분', '교과군', '과목유형']
    existing_cols = [col for col in core_cols if col in df.columns]
    
    if existing_cols:
        df[existing_cols] = df[existing_cols].ffill()
    else:
        st.error(f"엑셀 파일에서 기본 열({core_cols})을 찾을 수 없습니다. 현재 인식된 열: {list(df.columns)}")
        st.stop() # 실행 중단
        
    id_vars = ['구분', '교과군', '과목유형', '과목명', '기본학점']
    
    # 비고나 개설유형 열이 정규화된 이름으로 존재하는지 확인 후 추가
    for extra in ['과목개설유형', '비고']:
        if extra in df.columns: 
            id_vars.append(extra)

    # 1학기, 2학기 값 찾기 (1-1, 1-2 또는 1학기, 2학기 등)
    # 여기서는 제출하신 엑셀의 열 이름을 유연하게 잡기 위해 숫자와 '-'가 포함된 열을 찾습니다.
    value_vars = [col for col in df.columns if '-' in str(col) or '학기' in str(col)]
    
    df_melted = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='개설학기',
        value_name='배정학점'
    )
    
    df_cleaned = df_melted.dropna(subset=['배정학점'])
    df_cleaned['배정학점'] = pd.to_numeric(df_cleaned['배정학점'], errors='coerce')
    df_cleaned = df_cleaned[df_cleaned['배정학점'] > 0]
    
    return df_cleaned

# --- [검증 로직 함수 (동일)] ---
def validate_curriculum(df):
    results = []
    
    total_credits = df['배정학점'].sum()
    if total_credits >= 174:
        results.append(("✅ 통과", f"교과 총 이수 학점: {total_credits}학점 (174학점 이상 충족)"))
    else:
        results.append(("❌ 오류", f"교과 총 이수 학점 부족: {total_credits}학점 (174학점 이상 편성 필요)"))

    kme_credits = df[df['교과군'].isin(['국어', '수학', '영어'])]['배정학점'].sum()
    if kme_credits <= 81:
        results.append(("✅ 통과", f"국·수·영 총합: {kme_credits}학점 (81학점 이하 충족)"))
    else:
        results.append(("❌ 오류", f"국·수·영 총합 초과: {kme_credits}학점 (81학점 초과 금지)"))

    pe_data = df[df['교과군'].isin(['체육'])]
    pe_semesters = pe_data['개설학기'].unique()
    if len(pe_semesters) >= 6:
        results.append(("✅ 통과", "체육 교과 매 학기 편성 충족"))
    else:
        results.append(("❌ 오류", f"체육 교과 누락 학기 발생 (현재 {len(pe_semesters)}개 학기 편성)"))
        
    return results

# --- [메인 UI] ---
uploaded_file = st.file_uploader("교육과정 편제표 엑셀 파일을 업로드하세요 (.xlsx)", type=['xlsx', 'xls'])

if uploaded_file is not None:
    # try-except로 감싸서 에러 추적을 쉽게 만듦
    # try:
    raw_df = load_excel_robustly(uploaded_file)
    
    st.subheader("1. 원본 데이터 헤더 인식 결과")
    st.write("인식된 컬럼명:", list(raw_df.columns))
    st.dataframe(raw_df.head(5))
    
    with st.spinner('데이터를 정제하고 검증하는 중입니다...'):
        clean_df = preprocess_curriculum(raw_df)
        
        st.subheader("2. 구조 변환 완료 (Long Form)")
        st.dataframe(clean_df)
        
        validation_results = validate_curriculum(clean_df)
