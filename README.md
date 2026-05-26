# 고교 교육과정 편성 자율점검 도구

2022 개정 교육과정 기준 고등학교 학점 배당표(.xlsx)를 자동 분석하여 **21개 점검항목**에 대해 PASS/FAIL/CHECK 결과를 제공하는 Streamlit 웹앱입니다.

## 주요 기능

- 엑셀 학점 배당표 자동 파싱 (병합셀 해제 + 동적 헤더/경계 탐지)
- 21개 점검항목 자동 검증
  - **A. 학점 총량**: 총 192학점, 필수 84학점, 창체 18학점
  - **B. 학기별 배분**: 학기간 균형
  - **C. 과목별 학점**: 증감범위, 한국사 6학점, 동일과목 동일학점
  - **D. 교과군별**: 국·수·영 ≤ 50%, 체육 매학기·10학점 이상
  - **E. 순서/위계**: 공통→선택, 위계 과목 선후행
  - **F. 과목명/형식**: 2022 개정 공식 명칭 일치
  - **G. 정성/수동**: 선택권, 종교 복수편성
- 비고/유의사항 자동 추출 (수동 점검 지원)
- 결과 CSV/Excel 다운로드

## 빠른 시작 (로컬)

```bash
git clone https://github.com/YOUR_ID/curriculum-checker.git
cd curriculum-checker
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## Streamlit Cloud 배포

1. 이 저장소를 GitHub Public 저장소로 push
2. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 연동
3. 저장소 선택 → `app.py` 지정 → Deploy
4. 발급된 `https://[your-app].streamlit.app` URL 공유

## 프로젝트 구조

```
curriculum-checker/
├── app.py              # Streamlit UI
├── parser.py           # 엑셀 파싱
├── checker.py          # 21개 점검 로직
├── db.py               # 국가 교육과정 DB (151+ 과목)
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── config.toml     # 테마 설정
```

## 점검 기준 출처

- **2022 개정 교육과정 총론** (교육부 고시)
- **고등학교 교육과정 편성·운영 기준**
- **교육과정 편성 자율점검표** (시도교육청)

## 라이선스

MIT License

## 면책 조항

본 도구는 자동 점검 보조 도구이며, 최종 교육과정 확정은 학교 교육과정위원회의 검토가 필요합니다.


## 트러블슈팅

### `AttributeError: 'Styler' object has no attribute 'applymap'`
pandas 2.1+ 버전에서 `Styler.applymap`이 `Styler.map`으로 변경되었습니다.
본 패키지의 `app.py`는 두 API를 모두 지원하도록 자동 분기 처리되어 있습니다.
구버전 코드를 사용 중이라면 다음과 같이 변경하세요:

```python
# 변경 전 (deprecated)
df.style.applymap(func, subset=["상태"])

# 변경 후
df.style.map(func, subset=["상태"])
```

### Streamlit Cloud 재배포가 적용되지 않을 때
`Manage app` → `Reboot app` 클릭 또는 `requirements.txt`에 빈 줄을 추가 후 push하면 강제 재빌드됩니다.
