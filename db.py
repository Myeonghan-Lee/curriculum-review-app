"""
2022 개정 교육과정 과목 DB
- SUBJECT_DB: 정식 과목명 -> {교과군, 과목유형, 기본학점, 증감폭}
- HIERARCHY_PAIRS: 위계상 (선수, 후수) 쌍 목록
"""

# 과목 유형
T_COMMON      = "공통"
T_GENERAL     = "일반선택"
T_CAREER      = "진로선택"
T_CONVERGENCE = "융합선택"
T_SPECIAL     = "특수목적"   # 체육/예술 등 별도 학점 규정

# 교과군
G_KOR = "국어"
G_MAT = "수학"
G_ENG = "영어"
G_SOC = "사회"   # 한국사 포함
G_SCI = "과학"
G_PE  = "체육"
G_ART = "예술"
G_TI  = "기술가정/정보"
G_FL  = "제2외국어/한문"
G_LIB = "교양"

# 학점 표기 규칙: (기본학점, 허용 증감폭)
SUBJECT_DB = {
    # ===== 국어 =====
    "공통국어1": (G_KOR, T_COMMON, 4, 1),
    "공통국어2": (G_KOR, T_COMMON, 4, 1),
    "화법과 언어": (G_KOR, T_GENERAL, 4, 1),
    "독서와 작문": (G_KOR, T_GENERAL, 4, 1),
    "문학": (G_KOR, T_GENERAL, 4, 1),
    "주제 탐구 독서": (G_KOR, T_CAREER, 4, 1),
    "문학과 영상": (G_KOR, T_CAREER, 4, 1),
    "직무 의사소통": (G_KOR, T_CAREER, 4, 1),
    "독서 토론과 글쓰기": (G_KOR, T_CONVERGENCE, 4, 1),
    "매체 의사소통": (G_KOR, T_CONVERGENCE, 4, 1),
    "언어생활 탐구": (G_KOR, T_CONVERGENCE, 4, 1),
    # ===== 수학 =====
    "공통수학1": (G_MAT, T_COMMON, 4, 1),
    "공통수학2": (G_MAT, T_COMMON, 4, 1),
    "기본수학1": (G_MAT, T_COMMON, 4, 1),
    "기본수학2": (G_MAT, T_COMMON, 4, 1),
    "대수": (G_MAT, T_GENERAL, 4, 1),
    "미적분Ⅰ": (G_MAT, T_GENERAL, 4, 1),
    "확률과 통계": (G_MAT, T_GENERAL, 4, 1),
    "미적분Ⅱ": (G_MAT, T_CAREER, 4, 1),
    "기하": (G_MAT, T_CAREER, 4, 1),
    "경제 수학": (G_MAT, T_CAREER, 4, 1),
    "인공지능 수학": (G_MAT, T_CAREER, 4, 1),
    "직무 수학": (G_MAT, T_CAREER, 4, 1),
    "수학과 문화": (G_MAT, T_CONVERGENCE, 4, 1),
    "실용 통계": (G_MAT, T_CONVERGENCE, 4, 1),
    "수학과제 탐구": (G_MAT, T_CONVERGENCE, 4, 1),
    # ===== 영어 =====
    "공통영어1": (G_ENG, T_COMMON, 4, 1),
    "공통영어2": (G_ENG, T_COMMON, 4, 1),
    "기본영어1": (G_ENG, T_COMMON, 4, 1),
    "기본영어2": (G_ENG, T_COMMON, 4, 1),
    "영어Ⅰ": (G_ENG, T_GENERAL, 4, 1),
    "영어Ⅱ": (G_ENG, T_GENERAL, 4, 1),
    "영어 독해와 작문": (G_ENG, T_GENERAL, 4, 1),
    "영미 문학 읽기": (G_ENG, T_CAREER, 4, 1),
    "영어 발표와 토론": (G_ENG, T_CAREER, 4, 1),
    "심화 영어": (G_ENG, T_CAREER, 4, 1),
    "심화 영어 독해와 작문": (G_ENG, T_CAREER, 4, 1),
    "직무 영어": (G_ENG, T_CAREER, 4, 1),
    "실생활 영어 회화": (G_ENG, T_CONVERGENCE, 4, 1),
    "미디어 영어": (G_ENG, T_CONVERGENCE, 4, 1),
    "세계 문화와 영어": (G_ENG, T_CONVERGENCE, 4, 1),
    # ===== 사회 (한국사 포함) =====
    "한국사1": (G_SOC, T_COMMON, 3, 1),
    "한국사2": (G_SOC, T_COMMON, 3, 1),
    "통합사회1": (G_SOC, T_COMMON, 4, 1),
    "통합사회2": (G_SOC, T_COMMON, 4, 1),
    "세계시민과 지리": (G_SOC, T_GENERAL, 4, 1),
    "세계사": (G_SOC, T_GENERAL, 4, 1),
    "사회와 문화": (G_SOC, T_GENERAL, 4, 1),
    "현대사회와 윤리": (G_SOC, T_GENERAL, 4, 1),
    "한국지리 탐구": (G_SOC, T_CAREER, 4, 1),
    "도시의 미래 탐구": (G_SOC, T_CAREER, 4, 1),
    "동아시아 역사 기행": (G_SOC, T_CAREER, 4, 1),
    "정치": (G_SOC, T_CAREER, 4, 1),
    "법과 사회": (G_SOC, T_CAREER, 4, 1),
    "경제": (G_SOC, T_CAREER, 4, 1),
    "윤리와 사상": (G_SOC, T_CAREER, 4, 1),
    "인문학과 윤리": (G_SOC, T_CAREER, 4, 1),
    "국제 관계의 이해": (G_SOC, T_CAREER, 4, 1),
    "여행지리": (G_SOC, T_CONVERGENCE, 4, 1),
    "역사로 탐구하는 현대 세계": (G_SOC, T_CONVERGENCE, 4, 1),
    "사회문제 탐구": (G_SOC, T_CONVERGENCE, 4, 1),
    "금융과 경제생활": (G_SOC, T_CONVERGENCE, 4, 1),
    "윤리문제 탐구": (G_SOC, T_CONVERGENCE, 4, 1),
    "기후변화와 지속가능한 세계": (G_SOC, T_CONVERGENCE, 4, 1),
    # ===== 과학 =====
    "통합과학1": (G_SCI, T_COMMON, 4, 1),
    "통합과학2": (G_SCI, T_COMMON, 4, 1),
    "과학탐구실험1": (G_SCI, T_COMMON, 1, 0),
    "과학탐구실험2": (G_SCI, T_COMMON, 1, 0),
    "물리학": (G_SCI, T_GENERAL, 4, 1),
    "화학": (G_SCI, T_GENERAL, 4, 1),
    "생명과학": (G_SCI, T_GENERAL, 4, 1),
    "지구과학": (G_SCI, T_GENERAL, 4, 1),
    "역학과 에너지": (G_SCI, T_CAREER, 4, 1),
    "전자기와 양자": (G_SCI, T_CAREER, 4, 1),
    "물질과 에너지": (G_SCI, T_CAREER, 4, 1),
    "화학 반응의 세계": (G_SCI, T_CAREER, 4, 1),
    "세포와 물질대사": (G_SCI, T_CAREER, 4, 1),
    "생물의 유전": (G_SCI, T_CAREER, 4, 1),
    "지구시스템과학": (G_SCI, T_CAREER, 4, 1),
    "행성우주과학": (G_SCI, T_CAREER, 4, 1),
    "과학의 역사와 문화": (G_SCI, T_CONVERGENCE, 4, 1),
    "기후변화와 환경생태": (G_SCI, T_CONVERGENCE, 4, 1),
    "융합과학 탐구": (G_SCI, T_CONVERGENCE, 4, 1),
    # ===== 체육 =====
    "체육1": (G_PE, T_SPECIAL, 2, 1),
    "체육2": (G_PE, T_SPECIAL, 2, 1),
    "운동과 건강": (G_PE, T_SPECIAL, 2, 1),
    "스포츠 문화": (G_PE, T_SPECIAL, 2, 1),
    "스포츠 과학": (G_PE, T_SPECIAL, 2, 1),
    "스포츠 생활1": (G_PE, T_SPECIAL, 2, 1),
    "스포츠 생활2": (G_PE, T_SPECIAL, 2, 1),
    # ===== 예술 =====
    "음악": (G_ART, T_SPECIAL, 3, 1),
    "미술": (G_ART, T_SPECIAL, 3, 1),
    "연극": (G_ART, T_SPECIAL, 3, 1),
    "음악 연주와 창작": (G_ART, T_SPECIAL, 3, 1),
    "음악 감상과 비평": (G_ART, T_SPECIAL, 3, 1),
    "미술 창작": (G_ART, T_SPECIAL, 3, 1),
    "미술 감상과 비평": (G_ART, T_SPECIAL, 3, 1),
    "음악과 미디어": (G_ART, T_SPECIAL, 3, 1),
    "미술과 매체": (G_ART, T_SPECIAL, 3, 1),
    # ===== 기술가정/정보 =====
    "기술·가정": (G_TI, T_GENERAL, 4, 1),
    "정보": (G_TI, T_GENERAL, 4, 1),
    "로봇과 공학세계": (G_TI, T_CAREER, 4, 1),
    "생활과학 탐구": (G_TI, T_CAREER, 4, 1),
    "인공지능 기초": (G_TI, T_CAREER, 4, 1),
    "데이터 과학": (G_TI, T_CAREER, 4, 1),
    "창의 공학 설계": (G_TI, T_CONVERGENCE, 4, 1),
    "지식 재산 일반": (G_TI, T_CONVERGENCE, 4, 1),
    "생애 설계와 자립": (G_TI, T_CONVERGENCE, 4, 1),
    "아동발달과 부모": (G_TI, T_CONVERGENCE, 4, 1),
    "소프트웨어와 생활": (G_TI, T_CONVERGENCE, 4, 1),
    # ===== 제2외국어/한문 =====
    "독일어": (G_FL, T_GENERAL, 4, 1),
    "프랑스어": (G_FL, T_GENERAL, 4, 1),
    "스페인어": (G_FL, T_GENERAL, 4, 1),
    "중국어": (G_FL, T_GENERAL, 4, 1),
    "일본어": (G_FL, T_GENERAL, 4, 1),
    "러시아어": (G_FL, T_GENERAL, 4, 1),
    "아랍어": (G_FL, T_GENERAL, 4, 1),
    "베트남어": (G_FL, T_GENERAL, 4, 1),
    "독일어 회화": (G_FL, T_CAREER, 4, 1),
    "프랑스어 회화": (G_FL, T_CAREER, 4, 1),
    "스페인어 회화": (G_FL, T_CAREER, 4, 1),
    "중국어 회화": (G_FL, T_CAREER, 4, 1),
    "일본어 회화": (G_FL, T_CAREER, 4, 1),
    "러시아어 회화": (G_FL, T_CAREER, 4, 1),
    "아랍어 회화": (G_FL, T_CAREER, 4, 1),
    "베트남어 회화": (G_FL, T_CAREER, 4, 1),
    "심화 독일어": (G_FL, T_CAREER, 4, 1),
    "심화 프랑스어": (G_FL, T_CAREER, 4, 1),
    "심화 스페인어": (G_FL, T_CAREER, 4, 1),
    "심화 중국어": (G_FL, T_CAREER, 4, 1),
    "심화 일본어": (G_FL, T_CAREER, 4, 1),
    "심화 러시아어": (G_FL, T_CAREER, 4, 1),
    "심화 아랍어": (G_FL, T_CAREER, 4, 1),
    "심화 베트남어": (G_FL, T_CAREER, 4, 1),
    "독일어권 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "프랑스어권 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "스페인어권 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "중국 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "일본 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "러시아 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "아랍 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "베트남 문화": (G_FL, T_CONVERGENCE, 4, 1),
    "한문": (G_FL, T_GENERAL, 4, 1),
    "한문 고전 읽기": (G_FL, T_CAREER, 4, 1),
    "언어생활과 한자": (G_FL, T_CONVERGENCE, 4, 1),
    # ===== 교양 =====
    "진로와 직업": (G_LIB, T_GENERAL, 4, 1),
    "생태와 환경": (G_LIB, T_GENERAL, 4, 1),
    "인간과 철학": (G_LIB, T_CAREER, 4, 1),
    "논리와 사고": (G_LIB, T_CAREER, 4, 1),
    "인간과 심리": (G_LIB, T_CAREER, 4, 1),
    "교육의 이해": (G_LIB, T_CAREER, 4, 1),
    "삶과 종교": (G_LIB, T_CAREER, 4, 1),
    "보건": (G_LIB, T_CAREER, 4, 1),
    "인간과 경제활동": (G_LIB, T_CONVERGENCE, 4, 1),
    "논술": (G_LIB, T_CONVERGENCE, 4, 1),
}

# 위계상 (선수 -> 후수)
HIERARCHY_PAIRS = [
    ("공통국어1", "공통국어2"),
    ("공통수학1", "공통수학2"),
    ("공통수학2", "대수"),
    ("공통수학2", "미적분Ⅰ"),
    ("미적분Ⅰ", "미적분Ⅱ"),
    ("공통영어1", "공통영어2"),
    ("공통영어2", "영어Ⅰ"),
    ("영어Ⅰ", "영어Ⅱ"),
    ("통합사회1", "통합사회2"),
    ("통합과학1", "통합과학2"),
    ("한국사1", "한국사2"),
    ("체육1", "체육2"),
]

# 기초 교과(국·수·영)
BASIC_GROUPS = {G_KOR, G_MAT, G_ENG}
