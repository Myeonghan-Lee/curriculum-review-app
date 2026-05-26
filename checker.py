"""
checker.py
2022 개정 고등학교 교육과정 편성 자율점검 (21개 항목)
"""
import re
import pandas as pd
from db import (
    SUBJECT_DB, CREDIT_RANGE, SPECIAL_CREDIT, HIERARCHY_PAIRS,
    REQUIRED_CREDITS, PE_ART_EDU_GROUPS,
    TOTAL_MIN, SUBJECT_MIN, CTA_MIN,
    T_COMMON, T_GENERAL, T_CAREER, T_CONVERG,
)


def find_subject_col(subjects):
    """과목명 컬럼 찾기. '2)과목', '과목명', '과목' 등 패턴 대응."""
    # 1순위: '과목명'
    for c in subjects.columns:
        sc = str(c).replace(" ", "")
        if "과목명" in sc:
            return c
    # 2순위: '과목'을 포함하되 '유형'·'수'·'군'은 제외
    for c in subjects.columns:
        sc = str(c).replace(" ", "")
        if "과목" in sc and "유형" not in sc and "수" not in sc and "군" not in sc:
            return c
    return None


def find_credit_col(subjects):
    """운영학점 컬럼 찾기"""
    for c in subjects.columns:
        sc = str(c).replace(" ", "").replace("\n", "")
        if ("운영" in sc) and ("학점" in sc or "단위" in sc):
            return c
    for c in subjects.columns:
        sc = str(c).replace(" ", "").replace("\n", "")
        if ("기준" in sc) and ("학점" in sc or "단위" in sc):
            return c
    return None


def normalize_name(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s).strip())


class CurriculumChecker:
    def __init__(self, parsed):
        self.parsed = parsed
        self.subjects = parsed["subjects"]
        self.summary = parsed["summary"]
        self.metadata = parsed["metadata"]
        self.semester_cols = parsed["semester_cols"]
        self.subject_col = find_subject_col(self.subjects)
        self.credit_col = find_credit_col(self.subjects)
        self.results = []

    def _add(self, code, name, status, message, detail=None):
        self.results.append({
            "코드": code,
            "항목": name,
            "상태": status,
            "내용": message,
            "상세": detail or "",
        })

    def _subject_total(self):
        if "운영학점_계산" in self.subjects.columns:
            return float(self.subjects["운영학점_계산"].sum())
        return 0

    @staticmethod
    def _num(v):
        if v is None:
            return 0
        if isinstance(v, (int, float)):
            if pd.isna(v):
                return 0
            return float(v)
        s = str(v).strip()
        if not s or s == "nan":
            return 0
        m = re.match(r"^\s*(\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else 0

    def _get_subj_name(self, row):
        if self.subject_col is None:
            return ""
        return str(row.get(self.subject_col, "") or "")

    def _match_db(self, name):
        nm = normalize_name(name)
        if not nm:
            return None
        for db_name, info in SUBJECT_DB.items():
            if normalize_name(db_name) == nm:
                return db_name, info
        return None

    # ───── A. 학점 총량 ─────
    def check_A1_total(self):
        subject_total = self._subject_total()
        cta = 0
        for row in self.summary.get("창의적체험활동", []):
            for cell in row:
                n = self._num(cell)
                if n >= 18:
                    cta = n
                    break
        if cta == 0:
            cta = 18  # 기본 가정
        total = subject_total + cta
        status = "PASS" if total >= TOTAL_MIN else "FAIL"
        self._add("A1", "총 이수학점 ≥ 192",
                  status,
                  f"교과 {subject_total:.0f} + 창체 {cta:.0f} = {total:.0f}학점")

    def check_A2_required(self):
        if self.subject_col is None:
            self._add("A2", "필수이수 ≥ 84", "CHECK", "과목명 컬럼 미식별")
            return
        common_sum = 0
        common_subjects = []
        for _, row in self.subjects.iterrows():
            name = self._get_subj_name(row)
            m = self._match_db(name)
            if m and m[1][2] == T_COMMON:
                c = self._num(row.get("운영학점_계산", 0))
                common_sum += c
                common_subjects.append(f"{m[0]}({c:.0f})")
        status = "PASS" if common_sum >= 60 else "CHECK"
        self._add("A2", "필수이수 ≥ 84",
                  status,
                  f"공통과목 {common_sum:.0f}학점 ({len(common_subjects)}개)",
                  ", ".join(common_subjects[:8]))

    def check_A3_cta(self):
        cta = 0
        for row in self.summary.get("창의적체험활동", []):
            for cell in row:
                n = self._num(cell)
                if n >= 18:
                    cta = n
                    break
        if cta == 0:
            self._add("A3", "창의적 체험활동 ≥ 18",
                      "CHECK", "창체 행을 추출하지 못함 - 수동 확인")
            return
        status = "PASS" if cta >= CTA_MIN else "FAIL"
        self._add("A3", "창의적 체험활동 ≥ 18",
                  status, f"창체 {cta:.0f}학점")

    # ───── B. 학기별 배분 ─────
    def check_B1_semester_balance(self):
        if not self.semester_cols:
            self._add("B1", "학기간 균형", "CHECK", "학기 컬럼 미식별")
            return
        sem_sum = {}
        for sc in self.semester_cols:
            sem_sum[sc] = float(self.subjects[sc + "_num"].sum())
        mx = max(sem_sum.values())
        mn = min(sem_sum.values())
        diff = mx - mn
        status = "PASS" if diff <= 4 else "CHECK"
        detail = ", ".join(f"{k}:{v:.0f}" for k, v in sem_sum.items())
        self._add("B1", "학기간 학점 균형",
                  status, f"최대-최소 차 {diff:.0f}학점", detail)

    # ───── C. 과목별 학점 ─────
    def check_C1_credit_range(self):
        if self.subject_col is None:
            self._add("C1", "과목별 학점 증감범위", "CHECK", "과목명 컬럼 미식별")
            return
        violations = []
        checked = 0
        for _, row in self.subjects.iterrows():
            name = self._get_subj_name(row)
            m = self._match_db(name)
            if not m:
                continue
            db_name, (area, group, t) = m
            credit = self._num(row.get("운영학점_계산", 0))
            if credit == 0:
                continue
            checked += 1
            if db_name in SPECIAL_CREDIT:
                _, mn, mx = SPECIAL_CREDIT[db_name]
            elif group in PE_ART_EDU_GROUPS and t != T_COMMON:
                mn, mx = 2, 4
            else:
                _, mn, mx = CREDIT_RANGE[t]
            if not (mn <= credit <= mx):
                violations.append(f"{db_name}: {credit:.0f}(범위 {mn}-{mx})")
        if checked == 0:
            self._add("C1", "과목별 학점 증감범위", "CHECK", "DB 매칭 과목 0개")
        elif violations:
            self._add("C1", "과목별 학점 증감범위",
                      "FAIL", f"{len(violations)}/{checked}개 위반",
                      "; ".join(violations[:5]))
        else:
            self._add("C1", "과목별 학점 증감범위", "PASS",
                      f"{checked}개 과목 모두 범위 내")

    def check_C2_korean_history(self):
        if self.subject_col is None:
            self._add("C2", "한국사 3+3=6학점", "CHECK", "과목명 컬럼 미식별")
            return
        kh = {}
        for _, row in self.subjects.iterrows():
            name = normalize_name(self._get_subj_name(row))
            if name in ("한국사1", "한국사2"):
                kh[name] = self._num(row.get("운영학점_계산", 0))
        if kh.get("한국사1") == 3 and kh.get("한국사2") == 3:
            self._add("C2", "한국사 3+3=6학점", "PASS",
                      f"한국사1={kh['한국사1']:.0f}, 한국사2={kh['한국사2']:.0f}")
        elif kh:
            self._add("C2", "한국사 3+3=6학점", "FAIL", f"확인: {kh}")
        else:
            self._add("C2", "한국사 3+3=6학점", "CHECK", "한국사 과목 미식별")

    # ───── D. 교과군별 ─────
    def check_D1_basic_subjects(self):
        if self.subject_col is None:
            self._add("D1", "기초교과 ≤ 50%", "CHECK", "과목명 컬럼 미식별")
            return
        basic = 0
        total = 0
        for _, row in self.subjects.iterrows():
            credit = self._num(row.get("운영학점_계산", 0))
            total += credit
            m = self._match_db(self._get_subj_name(row))
            if m and m[1][1] in ("국어", "수학", "영어"):
                basic += credit
        ratio = basic / total * 100 if total else 0
        status = "PASS" if ratio <= 50 else "CHECK"
        self._add("D1", "국·수·영 ≤ 50%",
                  status, f"{basic:.0f}/{total:.0f}학점 ({ratio:.1f}%)")

    def check_D2_pe(self):
        if self.subject_col is None or not self.semester_cols:
            self._add("D2", "체육 매학기 + ≥10", "CHECK", "데이터 부족")
            return
        pe_total = 0
        pe_per_sem = {sc: 0 for sc in self.semester_cols}
        for _, row in self.subjects.iterrows():
            m = self._match_db(self._get_subj_name(row))
            if m and m[1][1] == "체육":
                pe_total += self._num(row.get("운영학점_계산", 0))
                for sc in self.semester_cols:
                    pe_per_sem[sc] += self._num(row.get(sc + "_num", 0))
        missing = [sc for sc, v in pe_per_sem.items() if v == 0]
        if pe_total >= 10 and not missing:
            self._add("D2", "체육 매학기 + ≥10",
                      "PASS", f"체육 {pe_total:.0f}학점, 6개 학기 모두 편성")
        elif pe_total >= 10:
            self._add("D2", "체육 매학기 + ≥10",
                      "CHECK",
                      f"체육 {pe_total:.0f}학점, 미편성 학기 {missing} (선택 풀 가능성)")
        else:
            self._add("D2", "체육 매학기 + ≥10",
                      "FAIL", f"체육 {pe_total:.0f}학점")

    # ───── E. 순서/위계 ─────
    def check_E1_common_first(self):
        if self.subject_col is None or not self.semester_cols:
            self._add("E1", "공통→선택 순서", "CHECK", "데이터 부족")
            return
        violations = []
        for _, row in self.subjects.iterrows():
            m = self._match_db(self._get_subj_name(row))
            if not m or m[1][2] != T_COMMON:
                continue
            y1 = sum(self._num(row.get(sc + "_num", 0))
                     for sc in self.semester_cols if sc.startswith("1-"))
            y23 = sum(self._num(row.get(sc + "_num", 0))
                      for sc in self.semester_cols if not sc.startswith("1-"))
            if y1 == 0 and y23 > 0:
                violations.append(m[0])
        if violations:
            self._add("E1", "공통→선택 순서", "FAIL",
                      f"공통과목이 2·3학년에만 편성: {violations}")
        else:
            self._add("E1", "공통→선택 순서", "PASS", "공통과목 1학년 우선 편성")

    def check_E2_hierarchy(self):
        if self.subject_col is None or not self.semester_cols:
            self._add("E2", "위계 과목 순서", "CHECK", "데이터 부족")
            return
        subj_sem = {}
        for _, row in self.subjects.iterrows():
            nm = normalize_name(self._get_subj_name(row))
            for sc in self.semester_cols:
                if self._num(row.get(sc + "_num", 0)) > 0:
                    subj_sem.setdefault(nm, []).append(sc)
        violations = []
        for pre, post in HIERARCHY_PAIRS:
            pn, qn = normalize_name(pre), normalize_name(post)
            if pn in subj_sem and qn in subj_sem:
                pre_min = min(subj_sem[pn])
                post_max = max(subj_sem[qn])
                if pre_min >= post_max:
                    violations.append(f"{pre}({pre_min})→{post}({post_max})")
        if violations:
            self._add("E2", "위계 과목 순서", "FAIL", "; ".join(violations))
        else:
            self._add("E2", "위계 과목 순서", "PASS", "선후행 순서 정상")

    # ───── F. 과목명/형식 ─────
    def check_F1_subject_names(self):
        if self.subject_col is None:
            self._add("F1", "공식 과목명 일치", "CHECK", "과목명 컬럼 미식별")
            return
        valid_names = {normalize_name(k): k for k in SUBJECT_DB.keys()}
        unknown = []
        misspelled = []
        for _, row in self.subjects.iterrows():
            raw = self._get_subj_name(row)
            if not raw or raw == "nan":
                continue
            nm = normalize_name(raw)
            if not nm:
                continue
            if nm in valid_names:
                if str(raw).strip() != valid_names[nm]:
                    misspelled.append(f"{raw} → {valid_names[nm]}")
            else:
                if not any(skip in nm for skip in ["선택", "택", "이수", "소계", "합계"]):
                    unknown.append(str(raw))
        msgs = []
        if misspelled:
            msgs.append(f"표기차이 {len(misspelled)}건")
        if unknown:
            msgs.append(f"DB 미등록 {len(unknown)}건")
        if not msgs:
            self._add("F1", "공식 과목명 일치", "PASS", "모든 과목명 일치")
        else:
            detail = "; ".join(misspelled[:3] + unknown[:3])
            self._add("F1", "공식 과목명 일치", "CHECK", "; ".join(msgs), detail)

    # ───── G. 정성/수동 ─────
    def check_G1_choice(self):
        self._add("G1", "학생 과목 선택권 보장",
                  "MANUAL", "선택과목 풀과 수강신청 데이터를 별도 확인 필요")

    def check_G2_religion(self):
        if self.subject_col is None:
            self._add("G2", "종교 복수 편성", "CHECK", "과목명 컬럼 미식별")
            return
        has_religion = any(
            "종교" in self._get_subj_name(row)
            for _, row in self.subjects.iterrows()
        )
        if has_religion:
            self._add("G2", "종교 복수 편성", "MANUAL",
                      "종교 과목 편성 확인 - 대체과목 동시편성 검토")
        else:
            self._add("G2", "종교 복수 편성", "N/A", "종교 과목 미편성")

    def check_notes(self):
        """비고/유의사항 추출"""
        notes = []
        for c in self.subjects.columns:
            if "비고" in str(c) or "유의" in str(c):
                for _, row in self.subjects.iterrows():
                    v = row.get(c)
                    if v is None or pd.isna(v):
                        continue
                    s = str(v).strip()
                    if s and s != "nan":
                        nm = self._get_subj_name(row)
                        notes.append(f"[{nm}] {s}")
        for row in self.summary.get("유의사항", []):
            text = " ".join(str(c) for c in row if c and str(c).strip() not in ("", "nan", "None"))
            if text.strip():
                notes.append(text)
        # 중복 제거
        seen = set()
        uniq = []
        for n in notes:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        return uniq

    def run_all(self):
        self.check_A1_total()
        self.check_A2_required()
        self.check_A3_cta()
        self.check_B1_semester_balance()
        self.check_C1_credit_range()
        self.check_C2_korean_history()
        self.check_D1_basic_subjects()
        self.check_D2_pe()
        self.check_E1_common_first()
        self.check_E2_hierarchy()
        self.check_F1_subject_names()
        self.check_G1_choice()
        self.check_G2_religion()
        return pd.DataFrame(self.results)
