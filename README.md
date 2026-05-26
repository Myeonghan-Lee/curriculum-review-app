# 교육과정 편성 자율점검 도구

2022 개정 교육과정 기준으로 단위학교의 학점 배당표를 자동 점검하는 Streamlit 웹 애플리케이션입니다.

## 주요 기능

- **엑셀 자동 파싱**: 병합셀 해제, 헤더 동적 탐지, 데이터/요약 영역 분리
- **21개 점검 항목 자동 검증**:
  - A. 학점 총량 (5개)
  - B. 학기별 배분 (3개)
  - C. 과목별 학점 (3개)
  - D. 교과군별 (2개)
  - E. 순서/위계 (2개)
  - F. 과목명/형식 (3개)
  - G. 정성적 점검 (3개)
- **국가 교육과정 DB 내장**: 2022 개정 공식 과목명 150여개, 위계 관계, 학점 범위
- **비고/유의사항 자동 추출**: 수동 점검을 위한 텍스트 분리
- **CSV 결과 다운로드**: 점검 결과를 표 형태로 내보내기

## 로컬 실행

```bash
# 1. 저장소 클론
git clone https://github.com/<your-username>/curriculum-checker.git
cd curriculum-checker

# 2. 가상환경 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

## Streamlit Cloud 배포

1. 이 저장소를 본인의 GitHub 계정으로 **Public** 저장소로 push
2. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 로그인
3. **New app** → 저장소/브랜치/`app.py` 선택 → **Deploy**
4. 약 1~2분 후 `https://<your-app>.streamlit.app` URL 발급

## 파일 구조

```
curriculum-checker/
├── app.py              # Streamlit UI 진입점
├── checker.py          # 21개 점검 로직
├── parser.py           # 엑셀 파싱 모듈
├── db.py               # 국가 교육과정 DB
├── requirements.txt    # 의존성
├── README.md           # 본 문서
├── .gitignore          # Git 제외 목록
└── .streamlit/
    └── config.toml     # Streamlit 테마 설정
```

## 사용 방법

1. 웹 앱에 접속
2. **학점 배당표 엑셀 파일(.xlsx)** 업로드
3. 자동 점검 결과 확인:
   - **PASS**: 자동 검증 통과
   - **FAIL**: 기준 미달 (수정 필요)
   - **CHECK**: 수동 확인 필요
   - **INFO / N/A**: 참고 / 해당 없음
4. **비고/유의사항** 탭에서 수동 점검 항목 검토
5. CSV로 결과 다운로드

## 입력 파일 형식

- **확장자**: `.xlsx` (Excel 2007 이상)
- **구조**: 단위학교 교육과정 학점 배당표 (서울특별시교육청 표준 양식 호환)
- **필수 컬럼**: 교과(군), 과목명, 1학년 1~2학기, 2학년 1~2학기, 3학년 1~2학기
- **권장**: 비고 컬럼 포함

## 기준 문서

- **교육과정 편성 자율점검표** (단위학교 점검용)
- **2022 개정 국가 교육과정** (교육부 고시)

## 라이선스

본 도구는 교육 목적으로 자유롭게 사용·배포할 수 있습니다.

## 문의

이슈는 GitHub Issues에 등록해주세요.
