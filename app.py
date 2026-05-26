import streamlit as st
import pandas as pd

# --- [1] 페이지 설정 ---
st.set_page_config(page_title="교육과정 편제표 검토기", layout="wide")
st.title("🏫 교육과정 편제표 자동 검토 시스템")
st.markdown("학교에서 제출한 편제표 엑셀 파일을 업로드하면, 국가 교육과정 지침에 따른 위반 사항을 자동으로 검출합니다.")

# --- [2] 데이터 전처리 함수 ---
def preprocess_curriculum(df):
    # 1. 병합된 셀(결측치) 앞의 값으로 채우기
    df[['구분', '교과군', '과목유형']] = df[['구분', '교과군', '과목유형']].ffill()
    
    # 2. 롱 폼(Long form)으로 변환 (Melt)
    # 실제 엑셀 파일의 열 이름에 맞게 수정이 필요할 수 있습니다.
    id_vars = ['구분', '교과군', '과목유형', '과목명', '기본학점']
    # 엑셀에 비고나 개설유형이 있다면 id_vars에 추가합니다.
    if '비고' in df.columns: id_vars.append('비고')
    if '과목 개설 유형' in df.columns: id_vars.append('과목 개설 유형')

    value_vars = ['1-1', '1-2', '2-1', '2-2', '3-1', '3-2']
    
    # 존재하는 학기 열만 value_vars로 사용
    value_vars = [col for col in value_vars if col in df.columns]

    df_melted = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='개설학기',
        value_name='배정학점'
    )
    
    # 3. 배정학점이 없는(결측치이거나 0인) 행 제거 (수강하지 않는 학기)
    df_cleaned = df_melted.dropna(subset=['배정학점'])
    # 학점이 숫자인 경우 0 이상만 남기기
    df_cleaned['배정학점'] = pd.to_numeric(df_cleaned['배정학점'], errors='coerce')
    df_cleaned = df_cleaned[df_cleaned['배정학점'] > 0]
    
    return df_cleaned

# --- [3] 검증 로직 함수 ---
def validate_curriculum(df):
    results = []
    
    # 1. 총 이수 학점 검증 (교과 174학점 이상)
    total_credits = df['배정학점'].sum()
    if total_credits >= 174:
        results.append(("✅ 통과", f"교과 총 이수 학점: {total_credits}학점 (174학점 이상 충족)"))
    else:
        results.append(("❌ 오류", f"교과 총 이수 학점 부족: {total_credits}학점 (174학점 이상 편성 필요)"))

    # 2. 국·수·영 이수 학점 총합 검증 (81학점 초과 금지)
    kme_credits = df[df['교과군'].isin(['국어', '수학', '영어'])]['배정학점'].sum()
    if kme_credits <= 81:
        results.append(("✅ 통과", f"국·수·영 총합: {kme_credits}학점 (81학점 이하 충족)"))
    else:
        results.append(("❌ 오류", f"국·수·영 총합 초과: {kme_credits}학점 (81학점 초과 금지)"))

    # 3. 체육 교과 연속성 검증 (매 학기 편성)
    pe_data = df[df['교과군'] == '체육']
    pe_semesters = pe_data['개설학기'].unique()
    if len(pe_semesters) == 6:
        results.append(("✅ 통과", "체육 교과 매 학기(6개 학기) 편성 충족"))
    else:
        missing = set(['1-1', '1-2', '2-1', '2-2', '3-1', '3-2']) - set(pe_semesters)
        results.append(("❌ 오류", f"체육 교과 누락 학기 발생: {', '.join(missing)}"))
        
    return results

# --- [4] 메인 UI 구성 ---
uploaded_file = st.file_uploader("교육과정 편제표 엑셀 파일을 업로드하세요 (.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    try:
        # 데이터 읽기 (header 위치는 엑셀 양식에 따라 조정 필요)
        raw_df = pd.read_excel(uploaded_file, header=0)
        
        st.subheader("원본 데이터 미리보기")
        st.dataframe(raw_df.head(3))
        
        with st.spinner('데이터를 정제하고 검증하는 중입니다...'):
            # 전처리
            clean_df = preprocess_curriculum(raw_df)
            
            st.subheader("구조 변환 완료 (Long Form)")
            st.dataframe(clean_df)
            
            # 검증 수행
            validation_results = validate_curriculum(clean_df)
            
            st.subheader("📊 교육과정 점검 결과")
            for status, message in validation_results:
                if status == "✅ 통과":
                    st.success(f"{status} | {message}")
                else:
                    st.error(f"{status} | {message}")
                    
    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다. 양식을 확인해주세요.\n(에러 내용: {e})")
