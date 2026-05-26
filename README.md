# 교육과정 편성 자율점검 (Streamlit)

2022 개정 교육과정 학점 배당표(.xlsx)를 업로드하면 **자율점검표 21개 항목**을 자동 검토합니다.

## 주요 기능
- 병합셀 자동 해제 및 3행 헤더 자동 인식
- 과목명/유형/학점 추출 + 학기별 배당 학점 자동 계산
- 2022 개정 145개 과목 DB 기반 위계·학점·표기 검증
- 비고 및 하단 유의사항 자동 추출 (수동 점검 지원)

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포
1. 이 폴더를 GitHub 저장소(Public)에 push
2. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 연동
3. **New app** → 저장소 선택 → `app.py` 지정 → Deploy
4. push 시 자동 재배포

## 파일 구성
| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit UI |
| `parser.py` | 엑셀 파싱 (병합셀 해제·동적 헤더 탐지) |
| `checker.py` | 21개 점검 로직 |
| `db.py` | 2022 개정 과목 DB |

## 지원하는 헤더 형식
- 표준 키워드: `구분`, `교과(군)`, `과목유형`, `과목명/과목`, `기준학점`, `운영학점`, `1~3학년(1·2학기)`, `비고`, `이수학점`, `필수이수학점`
- 키워드에 `1)`, `2)` 같은 번호 접두사 또는 `\n` 줄바꿈이 있어도 정규화 후 매칭

## 트러블슈팅
| 증상 | 원인 / 해결 |
|------|-------------|
| `AttributeError: 'Styler' object has no attribute 'applymap'` | pandas 2.1+에서 `applymap` → `map`. requirements.txt의 pandas 버전 확인 |
| `ValueError: 헤더 행을 찾지 못했습니다` | 엑셀 상단 20행 내 헤더 키워드가 5개 미만. 시트 구조/병합 상태를 확인 |
| 과목명이 `공통`, `일반`으로 잘못 추출됨 | `과목유형` 컬럼과 매칭 충돌. parser.py 최신 버전(우선순위 매칭)으로 교체 |

## 라이선스
MIT
