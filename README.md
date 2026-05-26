# 교육과정 편성 자율점검 (Streamlit)

2022 개정 교육과정 학점 배당표(.xlsx)를 업로드하면 자율점검표 21개 항목을 자동으로 검토합니다.

## 빠른 시작 (로컬)

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 자동 열림.

## Streamlit Cloud 배포

1. 이 폴더 전체를 GitHub **Public** 저장소에 push
2. https://share.streamlit.io 접속 → New app
3. Repository, Branch=`main`, Main file=`app.py` 입력 → Deploy
4. 약 1~2분 후 `https://<app>.streamlit.app` URL 발급

## 파일 구성

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit UI (업로드/탭/CSV 다운로드) |
| `parser.py` | 엑셀 파싱 (다중시트 자동선택, 병합셀 해제, 동적 헤더탐지) |
| `checker.py` | 21개 점검 로직 |
| `db.py` | 2022 개정 과목 DB + 위계쌍 |
| `requirements.txt` | 의존성 |
| `.streamlit/config.toml` | 테마/업로드 한계 |

## 지원하는 엑셀 형식

다음 헤더 키워드 중 3개 이상 인식됩니다 (번호접두사·줄바꿈·괄호 자동 처리):
- `구분`, `교과(군)`, `과목유형`, `과목명`(또는 `과목`)
- `기준학점`, `운영학점`(또는 `이수단위`, `단위`)
- `1~3학년 / 1~2학기`
- `비고`, `이수학점`, `필수이수학점`

여러 시트가 있는 워크북은 헤더 점수가 가장 높은 시트가 **자동 선택**됩니다.

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|-----------|
| `헤더 행을 찾지 못했습니다` | 시트 상단 30행 안에 헤더 키워드 3개 이상 있어야 함. 오류 메시지에 시트별 진단 점수 표시됨 |
| `Styler.applymap AttributeError` | 본 패키지는 pandas 2.1+의 `Styler.map`을 사용하며, 구버전에는 자동 폴백 처리됨 |
| Streamlit Cloud 재배포 안됨 | share.streamlit.io → 앱 → ⋮ → Reboot app |

## 점검 항목 (21개)

A. 학점 총량 / B. 학기별 배분 / C. 과목별 학점 / D. 교과군별 / E. 위계 / F. 과목명·형식 / G. 정성요건

상태 코드: `PASS` 통과, `FAIL` 위반, `CHECK` 사용자 확인, `MANUAL` 수동 점검, `N/A` 해당 없음.
