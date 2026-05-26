"""
checker.py - 교육과정 편성 자율점검표 21개 항목 점검
"""
from typing import Dict, List, Any, Optional
from db import SUBJECT_DB, HIERARCHY_PAIRS, lookup, normalize_name


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_CHECK = "CHECK"
STATUS_MANUAL = "MANUAL"
STATUS_NA = "N/A"


class CurriculumChecker:
    def __init__(self, parsed: Dict[str, Any]):
        self.parsed = parsed
        self.subjects = parsed.get("subjects", [])
        self.summary = parsed.get("summary", [])
        self.notes = parsed.get("notes", [])
        self.meta = parsed.get("meta", {})
        self.sem_labels = parsed.get("semester_labels", ["1-1","1-2","2-1","2-2","3-1","3-2"])
        self.results: List[Dict[str, Any]] = []

    # ---------- helpers ----------
    def _add(self, code, name, status, detail):
        self.results.append({
            "코드": code, "점검항목": name, "상태": status, "상세": detail
        })

    def _subjects_credit(self) -> float:
        return sum((s.get("운영학점") or 0) for s in self.subjects)

    def _ca_credit(self) -> Optional[float]:
        # summary에서 '창의적 체험활동' 찾기
        for s in self.summary:
            lbl = (s.get("label") or "")
            if "창의" in lbl or "창체" in lbl:
                return s.get("이수학점") or s.get("운영학점")
        return None

    def _sem_total(self) -> Dict[str, float]:
        totals = {sl: 0.0 for sl in self.sem_labels}
        for s in self.subjects:
            for sl in self.sem_labels:
                totals[sl] += (s.get(sl) or 0)
        return totals

    # ---------- A. 학점 총량 ----------
    def check_A1_total(self):
        subj = self._subjects_credit()
        ca = self._ca_credit() or 0
        total = subj + ca
        st = STATUS_PASS if total >= 192 else STATUS_FAIL
        self._add("A1", "총 이수학점 192학점 이상",
                  st, f"교과 {subj:.0f} + 창체 {ca:.0f} = {total:.0f}학점")

    def check_A2_subject_total(self):
        subj = self._subjects_credit()
        st = STATUS_PASS if subj >= 174 else STATUS_CHECK
        self._add("A2", "교과 174학점 이상", st, f"교과 합계 {subj:.0f}학점")

    def check_A3_required(self):
        req = sum((s.get("필수이수학점") or 0) for s in self.summary)
        if req == 0:
            # 학교지정 합산으로 추정
            req = sum((s.get("운영학점") or 0) for s in self.subjects
                      if (s.get("구분") or "").strip() == "학교지정")
        st = STATUS_PASS if req >= 84 else STATUS_CHECK
        self._add("A3", "필수 이수학점 84학점 이상",
                  st, f"필수/학교지정 합계 약 {req:.0f}학점")

    def check_A4_ca(self):
        ca = self._ca_credit()
        if ca is None:
            self._add("A4", "창의적 체험활동 18학점", STATUS_NA, "창체 행을 찾지 못함")
            return
        st = STATUS_PASS if ca >= 18 else STATUS_FAIL
        self._add("A4", "창의적 체험활동 18학점", st, f"창체 {ca:.0f}학점")

    def check_A5_excess(self):
        subj = self._subjects_credit()
        excess = subj - 174
        st = STATUS_PASS if excess <= 18 else STATUS_CHECK
        self._add("A5", "초과 이수학점 적정",
                  st, f"교과 초과 {excess:+.0f}학점 (174 기준)")

    # ---------- B. 학기별 배분 ----------
    def check_B1_semester_balance(self):
        tot = self._sem_total()
        vals = list(tot.values())
        diff = max(vals) - min(vals) if vals else 0
        st = STATUS_PASS if diff <= 5 else STATUS_CHECK
        detail = " / ".join(f"{k}:{v:.0f}" for k, v in tot.items())
        self._add("B1", "학기간 학점 차이 5학점 이내",
                  st, f"차이 {diff:.0f}학점 ({detail})")

    def check_B2_semester_unit(self):
        # 한 과목이 여러 학기에 분산되지 않는지 (단순 체크)
        multi = []
        for s in self.subjects:
            count = sum(1 for sl in self.sem_labels if (s.get(sl) or 0) > 0)
            if count > 1:
                multi.append(s["과목명"])
        st = STATUS_PASS if not multi else STATUS_CHECK
        self._add("B2", "학기 단위 과목 이수",
                  st, f"복수학기 편성 과목 {len(multi)}개" + (f": {', '.join(multi[:3])}..." if multi else ""))

    def check_B3_ca_balance(self):
        self._add("B3", "창체 편중 없음", STATUS_MANUAL,
                  "창체 학년별 분배는 학교 자체 확인 필요")

    # ---------- C. 과목별 학점 ----------
    def check_C1_credit_range(self):
        violations = []
        for s in self.subjects:
            name = normalize_name(s["과목명"])
            db = lookup(name)
            op = s.get("운영학점")
            if db is None or op is None:
                continue
            _, _, mn, mx, _ = db
            if op < mn or op > mx:
                violations.append(f"{name}({op:.0f}, 허용 {mn}-{mx})")
        st = STATUS_PASS if not violations else STATUS_CHECK
        detail = f"위반 {len(violations)}건" + (f": {'; '.join(violations[:5])}" if violations else "")
        self._add("C1", "과목별 학점 증감 범위 (±1/체예교 ±2)", st, detail)

    def check_C2_korean_history(self):
        targets = {"한국사1": None, "한국사2": None}
        for s in self.subjects:
            n = normalize_name(s["과목명"])
            if n in targets:
                targets[n] = s.get("운영학점")
        ok = all(v == 3 for v in targets.values())
        st = STATUS_PASS if ok else STATUS_FAIL
        self._add("C2", "한국사1·2 각 3학점",
                  st, f"한국사1={targets['한국사1']}, 한국사2={targets['한국사2']}")

    def check_C3_same_subject(self):
        # 같은 과목명이 서로 다른 학점으로 편성된 경우
        from collections import defaultdict
        m = defaultdict(set)
        for s in self.subjects:
            n = normalize_name(s["과목명"])
            if s.get("운영학점"):
                m[n].add(s["운영학점"])
        dups = {k: v for k, v in m.items() if len(v) > 1}
        st = STATUS_PASS if not dups else STATUS_FAIL
        self._add("C3", "동일 과목 동일 학점",
                  st, f"불일치 {len(dups)}건" + (f": {dups}" if dups else ""))

    # ---------- D. 교과군별 ----------
    def check_D1_basic_subjects(self):
        # 국·수·영 합계
        basic = ["국어", "수학", "영어"]
        total = 0
        for s in self.subjects:
            db = lookup(s["과목명"])
            tg = db[0] if db else (s.get("교과군") or "")
            tg_norm = str(tg).replace(" ", "")
            if tg_norm in [b.replace(" ", "") for b in basic]:
                total += (s.get("운영학점") or 0)
        st = STATUS_CHECK if total > 81 else STATUS_PASS
        self._add("D1", "기초교과(국·수·영) 81학점 이하",
                  st, f"국·수·영 합계 {total:.0f}학점 (선택풀 포함; 학생당 실 이수는 별도 확인)")

    def check_D2_physical(self):
        pe_total = 0
        pe_sems = set()
        for s in self.subjects:
            db = lookup(s["과목명"])
            tg = db[0] if db else (s.get("교과군") or "")
            if "체육" in str(tg):
                pe_total += (s.get("운영학점") or 0)
                for sl in self.sem_labels:
                    if (s.get(sl) or 0) > 0:
                        pe_sems.add(sl)
        cond1 = pe_total >= 10
        cond2 = len(pe_sems) >= 6
        st = STATUS_PASS if cond1 and cond2 else STATUS_CHECK
        self._add("D2", "체육 10학점 이상 + 매 학기 편성",
                  st, f"체육 {pe_total:.0f}학점, {len(pe_sems)}개 학기 편성")

    # ---------- E. 순서/위계 ----------
    def check_E1_common_first(self):
        violations = []
        for s in self.subjects:
            n = normalize_name(s["과목명"])
            db = lookup(n)
            if not db:
                continue
            stype = db[1]
            if stype != "공통":
                continue
            # 1학년 1학기/2학기에 편성되어야 정상
            first_sem = None
            for sl in self.sem_labels:
                if (s.get(sl) or 0) > 0:
                    first_sem = sl
                    break
            if first_sem and not first_sem.startswith("1"):
                violations.append(f"{n}({first_sem})")
        st = STATUS_PASS if not violations else STATUS_CHECK
        self._add("E1", "공통과목 → 선택과목 순서",
                  st, f"위반 {len(violations)}건" + (f": {', '.join(violations[:5])}" if violations else ""))

    def check_E2_hierarchy(self):
        # 위계쌍에서 후속이 선수보다 먼저 편성되었는지
        sem_order = {sl: i for i, sl in enumerate(self.sem_labels)}
        smap = {}
        for s in self.subjects:
            n = normalize_name(s["과목명"])
            for sl in self.sem_labels:
                if (s.get(sl) or 0) > 0:
                    smap.setdefault(n, []).append(sl)
        violations = []
        for pre, post in HIERARCHY_PAIRS:
            if pre in smap and post in smap:
                pre_min = min(sem_order[sl] for sl in smap[pre])
                post_min = min(sem_order[sl] for sl in smap[post])
                if post_min < pre_min:
                    violations.append(f"{pre}→{post}")
        st = STATUS_PASS if not violations else STATUS_FAIL
        self._add("E2", "위계 과목 선후 순서",
                  st, f"위반 {len(violations)}건" + (f": {', '.join(violations)}" if violations else ""))

    # ---------- F. 과목명/형식 ----------
    def check_F1_subject_names(self):
        unknown = []
        for s in self.subjects:
            n = normalize_name(s["과목명"])
            if not n:
                continue
            if lookup(n) is None:
                unknown.append(n)
        st = STATUS_PASS if not unknown else STATUS_CHECK
        sample = ", ".join(unknown[:6])
        self._add("F1", "2022 개정 정식 과목명 사용",
                  st, f"DB 미일치 {len(unknown)}건" + (f": {sample}" if unknown else ""))

    def check_F2_version(self):
        title = (self.meta.get("title") or "") + " ".join(self.meta.get("raw_header", []))
        st = STATUS_PASS if "2022" in title else STATUS_CHECK
        self._add("F2", "2022 개정 교육과정 명시", st, f"제목: {self.meta.get('title') or '-'}")

    def check_F3_format(self):
        self._add("F3", "학점 배당표 기록 형식 준수", STATUS_MANUAL,
                  "선택 과목 표기/학기당 과목 수 표기는 셀 서식 확인 필요")

    # ---------- G. 정성적 ----------
    def check_G1_choice(self):
        elective_credits = sum((s.get("운영학점") or 0) for s in self.subjects
                               if (s.get("구분") or "").strip() not in ["학교지정", ""])
        st = STATUS_CHECK
        self._add("G1", "학생 과목 선택권 보장", st,
                  f"선택과목 운영학점 합계 약 {elective_credits:.0f}학점")

    def check_G2_common_all(self):
        # 공통과목 운영학점 합산
        common_total = sum((s.get("운영학점") or 0) for s in self.subjects
                          if (lookup(s["과목명"]) or (None, None,))[1] == "공통")
        self._add("G2", "공통과목 전원 이수",
                  STATUS_PASS if common_total > 0 else STATUS_CHECK,
                  f"공통과목 합계 {common_total:.0f}학점")

    def check_G3_religion(self):
        religion = [s for s in self.subjects if "종교" in str(s.get("과목명") or "")]
        if not religion:
            self._add("G3", "종교 과목 복수 편성", STATUS_NA, "종교 과목 미편성")
            return
        self._add("G3", "종교 과목 복수 편성", STATUS_MANUAL,
                  f"종교 과목 {len(religion)}개 편성, 복수 선택 가능 여부 확인")

    # ---------- 실행 ----------
    def run_all(self) -> List[Dict[str, Any]]:
        self.results = []
        for m in [
            self.check_A1_total, self.check_A2_subject_total, self.check_A3_required,
            self.check_A4_ca, self.check_A5_excess,
            self.check_B1_semester_balance, self.check_B2_semester_unit, self.check_B3_ca_balance,
            self.check_C1_credit_range, self.check_C2_korean_history, self.check_C3_same_subject,
            self.check_D1_basic_subjects, self.check_D2_physical,
            self.check_E1_common_first, self.check_E2_hierarchy,
            self.check_F1_subject_names, self.check_F2_version, self.check_F3_format,
            self.check_G1_choice, self.check_G2_common_all, self.check_G3_religion,
        ]:
            try:
                m()
            except Exception as e:
                self._add("ERR", m.__name__, STATUS_NA, f"점검 실패: {e}")
        return self.results
