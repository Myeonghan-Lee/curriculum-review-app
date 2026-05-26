"""
교육과정 편성 자율점검표 (21개 항목) 자동 점검 로직
"""
from __future__ import annotations
from collections import defaultdict
from db import (
    SUBJECT_DB, HIERARCHY_PAIRS, BASIC_GROUPS,
    T_COMMON, T_GENERAL, T_CAREER, T_CONVERGENCE, T_SPECIAL,
    G_KOR, G_MAT, G_ENG, G_SOC, G_SCI, G_PE, G_ART, G_TI, G_FL, G_LIB,
)


class CurriculumChecker:
    def __init__(self, parsed: dict):
        self.parsed = parsed
        self.subjects = parsed.get("subjects", [])
        self.summary = parsed.get("summary_rows", [])
        self.notes = parsed.get("notes", [])
        self.semester_labels = parsed.get("semester_labels", [])
        self.meta = parsed.get("메타데이터", {})
        self._results: list[dict] = []

    # ---------- 공통 헬퍼 ----------
    def _total_subject_credits(self) -> float:
        """교과 총 운영학점 (창체 제외)"""
        return sum(s.get("운영학점", 0) for s in self.subjects)

    def _required_credits(self) -> float:
        """필수 이수 학점 합계"""
        return sum(s.get("필수이수학점", 0) for s in self.subjects)

    def _ca_credits(self) -> float:
        """창의적 체험활동 학점"""
        for s in self.summary:
            nm = str(s.get("과목명", ""))
            if "창의적 체험활동" in nm or "창체" in nm:
                return s.get("운영학점", 0) or s.get("학기합계", 0)
        return 0.0

    def _semester_totals(self) -> dict[str, float]:
        """학기별 총 학점"""
        totals = defaultdict(float)
        for s in self.subjects:
            for lbl, v in s.get("학기별학점", {}).items():
                totals[lbl] += v
        return dict(totals)

    def _group_totals(self) -> dict[str, float]:
        """교과군별 운영학점 (DB 기준)"""
        totals = defaultdict(float)
        for s in self.subjects:
            info = SUBJECT_DB.get(s["과목명"])
            if info:
                totals[info[0]] += s.get("운영학점", 0)
            else:
                grp = s.get("교과군") or ""
                if grp:
                    totals[str(grp).strip()] += s.get("운영학점", 0)
        return dict(totals)

    def _add(self, code: str, name: str, status: str, message: str, detail: str = ""):
        self._results.append({
            "코드": code, "점검항목": name, "상태": status,
            "결과": message, "상세": detail,
        })

    # ---------- A. 학점 총량 ----------
    def check_A1(self):
        total = self._total_subject_credits() + self._ca_credits()
        ok = total >= 192
        self._add("A1", "총 이수학점 192 이상",
                  "PASS" if ok else "FAIL",
                  f"총 {total:.0f}학점 (교과 {self._total_subject_credits():.0f} + 창체 {self._ca_credits():.0f})")

    def check_A2(self):
        total = self._total_subject_credits()
        ok = total >= 174
        self._add("A2", "교과 174학점 이상",
                  "PASS" if ok else "FAIL", f"교과 총 {total:.0f}학점")

    def check_A3(self):
        req = self._required_credits()
        ok = req >= 84
        self._add("A3", "필수 이수 84학점 이상",
                  "PASS" if ok else "CHECK", f"필수 합계 {req:.0f}학점")

    def check_A4(self):
        ca = self._ca_credits()
        ok = ca >= 18
        self._add("A4", "창체 18학점 이상",
                  "PASS" if ok else "FAIL", f"창체 {ca:.0f}학점")

    def check_A5(self):
        total = self._total_subject_credits()
        excess = total - 174
        if excess <= 0:
            status, msg = "PASS", "초과 이수 없음"
        elif excess <= 18:
            status, msg = "PASS", f"교과 초과 {excess:.0f}학점 (적정)"
        else:
            status, msg = "CHECK", f"교과 초과 {excess:.0f}학점 (과다 여부 확인 필요)"
        self._add("A5", "초과이수 적정성", status, msg)

    # ---------- B. 학기별 배분 ----------
    def check_B1(self):
        totals = self._semester_totals()
        if not totals:
            self._add("B1", "학기간 균형 (차이 5학점 이내)", "N/A", "학기 데이터 없음")
            return
        mx, mn = max(totals.values()), min(totals.values())
        diff = mx - mn
        ok = diff <= 5
        detail = " / ".join(f"{k}: {v:.0f}" for k, v in sorted(totals.items()))
        self._add("B1", "학기간 균형 (차이 5학점 이내)",
                  "PASS" if ok else "CHECK",
                  f"최대-최소 차이 {diff:.0f}학점", detail)

    def check_B2(self):
        # 한 과목이 여러 학기에 걸쳐 동시 운영되지 않는지 (학기 단위 이수)
        ok_count = 0
        warn = []
        for s in self.subjects:
            sem = {k: v for k, v in s.get("학기별학점", {}).items() if v > 0}
            if len(sem) == 0:
                continue
            ok_count += 1
            # 동일 과목이 3개 이상 학기에 분산되면 경고
            if len(sem) >= 3:
                warn.append(f"{s['과목명']}({','.join(sem.keys())})")
        if not warn:
            self._add("B2", "학기 단위 이수", "PASS", f"{ok_count}개 과목 정상")
        else:
            self._add("B2", "학기 단위 이수", "CHECK",
                      f"{len(warn)}개 과목 다학기 분산", "; ".join(warn[:5]))

    def check_B3(self):
        # 창체 편중 (수동 확인 필요)
        self._add("B3", "창체 학년/학기 편중 여부", "MANUAL",
                  "엑셀 비고/유의사항 및 학사일정 확인 필요")

    # ---------- C. 과목별 학점 ----------
    def check_C1(self):
        violations = []
        for s in self.subjects:
            info = SUBJECT_DB.get(s["과목명"])
            if not info:
                continue
            grp, typ, base, delta = info
            op = s.get("운영학점", 0)
            if op == 0:
                continue
            # 학기당 학점은 학기별 분포로 판단
            sem_vals = [v for v in s.get("학기별학점", {}).values() if v > 0]
            for v in sem_vals:
                lo, hi = base - delta, base + delta
                if typ == T_SPECIAL:
                    lo, hi = 1, base + delta
                if v < lo or v > hi:
                    violations.append(f"{s['과목명']}({v:.0f}학점/학기)")
                    break
        if not violations:
            self._add("C1", "과목별 학점 증감 범위 (±1, 체·예 ±2)", "PASS",
                      f"DB 매칭 {len([1 for s in self.subjects if s['과목명'] in SUBJECT_DB])}개 모두 적정")
        else:
            self._add("C1", "과목별 학점 증감 범위 (±1, 체·예 ±2)", "CHECK",
                      f"{len(violations)}건 범위 초과 가능",
                      "; ".join(violations[:8]))

    def check_C2(self):
        h1 = next((s for s in self.subjects if s["과목명"] == "한국사1"), None)
        h2 = next((s for s in self.subjects if s["과목명"] == "한국사2"), None)
        if not h1 or not h2:
            self._add("C2", "한국사 각 3학점", "N/A", "한국사1/2 없음")
            return
        ok = h1["운영학점"] == 3 and h2["운영학점"] == 3
        self._add("C2", "한국사 각 3학점",
                  "PASS" if ok else "FAIL",
                  f"한국사1={h1['운영학점']:.0f}, 한국사2={h2['운영학점']:.0f}")

    def check_C3(self):
        # 동일 과목명이 서로 다른 학점으로 편성되지 않았는지
        name_credits = defaultdict(set)
        for s in self.subjects:
            name_credits[s["과목명"]].add(s.get("운영학점", 0))
        diff = [(n, sorted(c)) for n, c in name_credits.items() if len(c) > 1]
        if not diff:
            self._add("C3", "동일 과목 동일 학점", "PASS", "중복 학점 편성 없음")
        else:
            self._add("C3", "동일 과목 동일 학점", "FAIL",
                      f"{len(diff)}건 불일치",
                      "; ".join(f"{n}={c}" for n, c in diff[:5]))

    # ---------- D. 교과군별 ----------
    def check_D1(self):
        gt = self._group_totals()
        basic = sum(gt.get(g, 0) for g in BASIC_GROUPS)
        total = self._total_subject_credits()
        ratio = (basic / total * 100) if total else 0
        ok = basic <= 81
        msg = f"국·수·영 {basic:.0f}학점 (교과의 {ratio:.1f}%)"
        self._add("D1", "국·수·영 81학점 이내",
                  "PASS" if ok else "CHECK", msg,
                  f"국어 {gt.get(G_KOR, 0):.0f} / 수학 {gt.get(G_MAT, 0):.0f} / 영어 {gt.get(G_ENG, 0):.0f}")

    def check_D2(self):
        gt = self._group_totals()
        pe = gt.get(G_PE, 0)
        # 매 학기 편성 여부
        pe_sems = defaultdict(float)
        for s in self.subjects:
            info = SUBJECT_DB.get(s["과목명"])
            if not (info and info[0] == G_PE):
                continue
            for lbl, v in s.get("학기별학점", {}).items():
                if v > 0:
                    pe_sems[lbl] += v
        n_sem = len(pe_sems)
        ok = pe >= 10 and n_sem >= len(self.semester_labels)
        msg = f"체육 {pe:.0f}학점 / {n_sem}개 학기 편성"
        self._add("D2", "체육 10학점 이상 + 매 학기 편성",
                  "PASS" if ok else "CHECK", msg)

    # ---------- E. 순서/위계 ----------
    def check_E1(self):
        # 공통 과목이 해당 교과(군)의 선택 과목보다 먼저 편성되었는지
        first_sem = {}  # (과목명) -> 첫 학기 라벨
        for s in self.subjects:
            for lbl, v in s.get("학기별학점", {}).items():
                if v > 0:
                    if s["과목명"] not in first_sem or lbl < first_sem[s["과목명"]]:
                        first_sem[s["과목명"]] = lbl
        violations = []
        for s in self.subjects:
            info = SUBJECT_DB.get(s["과목명"])
            if not info:
                continue
            grp, typ, *_ = info
            if typ != T_COMMON:
                continue
            cm_first = first_sem.get(s["과목명"])
            if not cm_first:
                continue
            # 같은 교과군 선택 과목의 첫 학기
            for s2 in self.subjects:
                info2 = SUBJECT_DB.get(s2["과목명"])
                if not info2 or info2[0] != grp:
                    continue
                if info2[1] == T_COMMON:
                    continue
                sel_first = first_sem.get(s2["과목명"])
                if sel_first and sel_first < cm_first:
                    violations.append(f"{s2['과목명']}({sel_first})<{s['과목명']}({cm_first})")
        if not violations:
            self._add("E1", "공통→선택 순서", "PASS", "모든 공통 과목이 선택 과목보다 먼저 편성")
        else:
            self._add("E1", "공통→선택 순서", "CHECK",
                      f"{len(violations)}건 역순 가능",
                      "; ".join(violations[:5]))

    def check_E2(self):
        first_sem = {}
        for s in self.subjects:
            for lbl, v in sorted(s.get("학기별학점", {}).items()):
                if v > 0:
                    first_sem.setdefault(s["과목명"], lbl)
        violations = []
        for prev, nxt in HIERARCHY_PAIRS:
            p, n = first_sem.get(prev), first_sem.get(nxt)
            if p and n and n < p:
                violations.append(f"{prev}({p}) > {nxt}({n})")
        if not violations:
            self._add("E2", "위계 과목 선후 순서", "PASS",
                      f"{len([1 for p, n in HIERARCHY_PAIRS if first_sem.get(p) and first_sem.get(n)])}쌍 정상")
        else:
            self._add("E2", "위계 과목 선후 순서", "FAIL",
                      f"{len(violations)}쌍 역순", "; ".join(violations[:5]))

    # ---------- F. 과목명/형식 ----------
    def check_F1(self):
        unknown = []
        for s in self.subjects:
            nm = s["과목명"]
            if not nm:
                continue
            if nm not in SUBJECT_DB:
                unknown.append(nm)
        if not unknown:
            self._add("F1", "2022 개정 정식 과목명 사용", "PASS", "전 과목 정식 명칭")
        else:
            self._add("F1", "2022 개정 정식 과목명 사용", "CHECK",
                      f"{len(unknown)}개 과목 DB 미일치 (학교 신설/오타 확인)",
                      "; ".join(unknown[:8]))

    def check_F2(self):
        cm = self.parsed.get("col_map", {})
        if "교과영역" in cm or "교과군" in cm:
            self._add("F2", "학점배당표 기록 형식 (영역·교과군 컬럼)", "PASS",
                      "필수 컬럼 모두 존재")
        else:
            self._add("F2", "학점배당표 기록 형식 (영역·교과군 컬럼)", "FAIL",
                      "교과영역/교과군 컬럼 누락")

    def check_F3(self):
        self._add("F3", "기록 형식 세부 (선택 표기, 학기당 과목수)", "MANUAL",
                  "엑셀 비고/하단 유의사항 수동 확인 필요")

    # ---------- G. 정성/수동 ----------
    def check_G1(self):
        # 학생 선택권: 진로/융합 선택 비율
        gen = car = conv = 0
        for s in self.subjects:
            info = SUBJECT_DB.get(s["과목명"])
            if not info:
                continue
            t = info[1]
            op = s.get("운영학점", 0)
            if t == T_GENERAL: gen += op
            elif t == T_CAREER: car += op
            elif t == T_CONVERGENCE: conv += op
        total_sel = gen + car + conv
        msg = f"일반 {gen:.0f} / 진로 {car:.0f} / 융합 {conv:.0f} (계 {total_sel:.0f})"
        if total_sel >= 80:
            self._add("G1", "학생 선택권 보장", "PASS", msg)
        else:
            self._add("G1", "학생 선택권 보장", "CHECK", msg)

    def check_G2(self):
        # 공통 과목 전원 이수: 공통과목으로 등록된 모든 과목이 운영학점>0
        missing = []
        # DB에서 공통 과목 중 일반고에 일반적인 것들
        common_must = ["공통국어1", "공통국어2", "공통수학1", "공통수학2",
                       "공통영어1", "공통영어2", "통합사회1", "통합사회2",
                       "통합과학1", "통합과학2", "한국사1", "한국사2"]
        names = {s["과목명"] for s in self.subjects if s.get("운영학점", 0) > 0}
        for c in common_must:
            if c not in names:
                missing.append(c)
        if not missing:
            self._add("G2", "공통 과목 전원 이수", "PASS",
                      f"공통 12과목 모두 편성")
        else:
            self._add("G2", "공통 과목 전원 이수", "CHECK",
                      f"{len(missing)}개 누락",
                      "; ".join(missing))

    def check_G3(self):
        rel = [s for s in self.subjects if "종교" in (s["과목명"] or "")]
        if not rel:
            self._add("G3", "종교 과목 복수 편성", "N/A", "종교 과목 미편성")
        else:
            self._add("G3", "종교 과목 복수 편성", "MANUAL",
                      f"종교 관련 {len(rel)}개 편성 - 복수선택 보장 여부 수동 확인")

    # ---------- 실행 ----------
    def run_all(self) -> list[dict]:
        self._results = []
        for m in [self.check_A1, self.check_A2, self.check_A3, self.check_A4, self.check_A5,
                  self.check_B1, self.check_B2, self.check_B3,
                  self.check_C1, self.check_C2, self.check_C3,
                  self.check_D1, self.check_D2,
                  self.check_E1, self.check_E2,
                  self.check_F1, self.check_F2, self.check_F3,
                  self.check_G1, self.check_G2, self.check_G3]:
            try:
                m()
            except Exception as e:
                self._add(m.__name__.replace("check_", ""), m.__name__, "ERROR", f"{type(e).__name__}: {e}")
        return self._results


def run_checks(parsed: dict) -> list[dict]:
    return CurriculumChecker(parsed).run_all()
