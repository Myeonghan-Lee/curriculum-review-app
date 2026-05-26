"""
교육과정 편성 자율점검표 21개 항목 자동 점검 모듈
"""
import re
from collections import defaultdict

from db import (
    SUBJECT_DB, SUBJECT_TO_GROUP, CREDIT_RANGE, HIERARCHY_PAIRS,
    REQUIRED_CREDITS, TOTAL_CREDIT, REQUIRED_TOTAL, CHANGE_CREDIT,
)


def _flatten_all_subjects():
    all_subjects = set()
    for group, types in SUBJECT_DB.items():
        for subjects in types.values():
            for s in subjects:
                all_subjects.add(s)
    return all_subjects


ALL_OFFICIAL_SUBJECTS = _flatten_all_subjects()


def _normalize(name):
    """과목명 정규화 (공백 제거, 특수문자 통일)"""
    s = re.sub(r"\s+", "", name)
    s = s.replace("·", "·").replace("ㆍ", "·")
    return s


NORMALIZED_SUBJECTS = {_normalize(s): s for s in ALL_OFFICIAL_SUBJECTS}


def get_group(subject_name):
    """과목명으로부터 교과군 추론"""
    if subject_name in SUBJECT_TO_GROUP:
        return SUBJECT_TO_GROUP[subject_name][0]
    norm = _normalize(subject_name)
    if norm in NORMALIZED_SUBJECTS:
        official = NORMALIZED_SUBJECTS[norm]
        return SUBJECT_TO_GROUP[official][0]
    return None


def get_subject_type(subject_name):
    """과목 유형 추론 (공통/일반선택/진로선택/융합선택)"""
    if subject_name in SUBJECT_TO_GROUP:
        return SUBJECT_TO_GROUP[subject_name][1]
    norm = _normalize(subject_name)
    if norm in NORMALIZED_SUBJECTS:
        official = NORMALIZED_SUBJECTS[norm]
        return SUBJECT_TO_GROUP[official][1]
    return None


class CurriculumChecker:
    def __init__(self, parsed, records):
        self.parsed = parsed
        self.records = records
        self.results = []

    def run_all(self):
        """21개 점검 항목 일괄 실행"""
        self.results = []
        self.check_A1_total_credit()
        self.check_A2_required_credit()
        self.check_A3_creative_activity()
        self.check_A4_group_required()
        self.check_A5_elective_total()
        self.check_B1_semester_balance()
        self.check_B2_semester_unit()
        self.check_B3_creative_balance()
        self.check_C1_credit_range()
        self.check_C2_korean_history()
        self.check_C3_same_subject_credit()
        self.check_D1_basic_subjects()
        self.check_D2_pe_credit()
        self.check_E1_common_before_elective()
        self.check_E2_hierarchy_order()
        self.check_F1_subject_names()
        self.check_F2_curriculum_version()
        self.check_F3_recording_format()
        self.check_G1_student_choice()
        self.check_G2_common_all_students()
        self.check_G3_religion_plural()
        return self.results

    def _add(self, code, name, status, detail, manual=False):
        self.results.append({
            "코드": code,
            "점검항목": name,
            "상태": status,
            "세부내용": detail,
            "수동확인필요": manual,
        })

    # ============================================================
    # A. 학점 총량
    # ============================================================
    def check_A1_total_credit(self):
        total = sum(r["총학점"] for r in self.records)
        creative = self._get_creative_credit()
        grand_total = total + creative
        if grand_total >= TOTAL_CREDIT:
            self._add("A1", "총 이수학점 192학점 이상",
                     "PASS", f"교과 {total:.0f} + 창체 {creative:.0f} = {grand_total:.0f}학점")
        else:
            self._add("A1", "총 이수학점 192학점 이상",
                     "FAIL", f"교과 {total:.0f} + 창체 {creative:.0f} = {grand_total:.0f}학점 (부족)")

    def check_A2_required_credit(self):
        total = sum(r["총학점"] for r in self.records)
        if total >= REQUIRED_TOTAL:
            self._add("A2", "필수 이수학점 84학점 이상",
                     "PASS", f"교과 총 {total:.0f}학점 (필수 + 자율)")
        else:
            self._add("A2", "필수 이수학점 84학점 이상",
                     "FAIL", f"교과 총 {total:.0f}학점")

    def check_A3_creative_activity(self):
        creative = self._get_creative_credit()
        if creative >= CHANGE_CREDIT:
            self._add("A3", "창의적 체험활동 18학점 이상",
                     "PASS", f"창체 {creative:.0f}학점")
        else:
            self._add("A3", "창의적 체험활동 18학점 이상",
                     "CHECK", f"창체 {creative:.0f}학점 (요약영역에서 미감지 시 확인)")

    def check_A4_group_required(self):
        group_total = defaultdict(float)
        for r in self.records:
            g = get_group(r["과목명"]) or r["교과군"]
            if g:
                group_total[g] += r["총학점"]

        details = []
        all_pass = True
        for group, required in REQUIRED_CREDITS.items():
            if required == 0:
                continue
            actual = group_total.get(group, 0)
            # 유사 명칭 매칭
            for k in group_total:
                if group in k or k in group:
                    actual = max(actual, group_total[k])
            status_mark = "OK" if actual >= required else "부족"
            if actual < required:
                all_pass = False
            details.append(f"{group}: {actual:.0f}/{required} ({status_mark})")

        self._add("A4", "교과(군)별 필수 이수학점 충족",
                 "PASS" if all_pass else "CHECK",
                 " | ".join(details), manual=not all_pass)

    def check_A5_elective_total(self):
        total = sum(r["총학점"] for r in self.records)
        elective = total - REQUIRED_TOTAL
        self._add("A5", "자율 이수학점 (선택과목) 적정성",
                 "INFO", f"교과 총 {total:.0f}학점, 필수 84 기준 선택 {elective:.0f}학점 추정")

    # ============================================================
    # B. 학기별 배분
    # ============================================================
    def check_B1_semester_balance(self):
        sem_total = defaultdict(float)
        for r in self.records:
            for sc, v in r["학기별"].items():
                sem_total[sc] += v
        if not sem_total:
            self._add("B1", "학기별 이수학점 균형",
                     "CHECK", "학기 컬럼 미감지", manual=True)
            return
        values = list(sem_total.values())
        diff = max(values) - min(values)
        details = ", ".join(f"{k}={v:.0f}" for k, v in sorted(sem_total.items()))
        if diff <= 4:
            self._add("B1", "학기별 이수학점 균형 (차이 4학점 이내)",
                     "PASS", f"{details} (차이 {diff:.0f})")
        else:
            self._add("B1", "학기별 이수학점 균형 (차이 4학점 이내)",
                     "CHECK", f"{details} (차이 {diff:.0f})", manual=True)

    def check_B2_semester_unit(self):
        non_integer = []
        for r in self.records:
            for sc, v in r["학기별"].items():
                if v > 0 and v != int(v):
                    non_integer.append(f"{r['과목명']}({sc}={v})")
        if not non_integer:
            self._add("B2", "학기 단위 이수 (정수 학점)",
                     "PASS", "모든 학점이 정수")
        else:
            self._add("B2", "학기 단위 이수 (정수 학점)",
                     "CHECK", f"비정수: {', '.join(non_integer[:5])}", manual=True)

    def check_B3_creative_balance(self):
        self._add("B3", "창의적 체험활동 학기별 균형",
                 "INFO", "요약영역 창체 행을 수동 확인하세요", manual=True)

    # ============================================================
    # C. 과목별 학점
    # ============================================================
    def check_C1_credit_range(self):
        violations = []
        for r in self.records:
            name = r["과목명"]
            credit = r["총학점"]
            stype = get_subject_type(name)
            group = get_group(name)
            if stype is None or credit == 0:
                continue
            # 한국사
            if "한국사" in name:
                lo, hi = CREDIT_RANGE["한국사"]
            elif "과학탐구실험" in name:
                lo, hi = CREDIT_RANGE["과탐실험"]
            elif stype == "공통":
                lo, hi = CREDIT_RANGE["공통_기본"]
            elif group in ("체육", "예술", "교양"):
                lo, hi = CREDIT_RANGE["체예교"]
            elif name in ("스포츠 문화", "스포츠 과학", "생애 설계와 자립"):
                lo, hi = CREDIT_RANGE["스포츠특수"]
            else:
                lo, hi = CREDIT_RANGE["선택_기본"]
            if not (lo <= credit <= hi):
                violations.append(f"{name}={credit:.0f}(허용 {lo}~{hi})")
        if not violations:
            self._add("C1", "과목별 학점 범위 준수",
                     "PASS", "모든 과목 허용 범위 내")
        else:
            self._add("C1", "과목별 학점 범위 준수",
                     "FAIL", " | ".join(violations[:5]))

    def check_C2_korean_history(self):
        kh_credits = [r["총학점"] for r in self.records if "한국사" in r["과목명"]]
        kh_total = sum(kh_credits)
        if kh_total == 6 and all(c == 3 for c in kh_credits):
            self._add("C2", "한국사 1, 2 각 3학점",
                     "PASS", f"한국사 총 {kh_total:.0f}학점")
        else:
            self._add("C2", "한국사 1, 2 각 3학점",
                     "CHECK", f"한국사 과목: {kh_credits}", manual=True)

    def check_C3_same_subject_credit(self):
        by_name = defaultdict(list)
        for r in self.records:
            if r["총학점"] > 0:
                by_name[r["과목명"]].append(r["총학점"])
        inconsistent = [n for n, vs in by_name.items() if len(set(vs)) > 1]
        if not inconsistent:
            self._add("C3", "동일 과목 동일 학점",
                     "PASS", "동일 과목명은 모두 동일 학점")
        else:
            self._add("C3", "동일 과목 동일 학점",
                     "FAIL", f"불일치: {inconsistent}")

    # ============================================================
    # D. 교과군별
    # ============================================================
    def check_D1_basic_subjects(self):
        basic_total = 0
        for r in self.records:
            g = get_group(r["과목명"])
            if g in ("국어", "수학", "영어"):
                basic_total += r["총학점"]
        if basic_total <= 81:
            self._add("D1", "기초교과(국·수·영) 81학점 이하",
                     "PASS", f"국·수·영 총 {basic_total:.0f}학점")
        else:
            self._add("D1", "기초교과(국·수·영) 81학점 이하",
                     "CHECK",
                     f"학교지정 기준 {basic_total:.0f}학점 (선택풀 운영 시 비고 확인)",
                     manual=True)

    def check_D2_pe_credit(self):
        pe_total = 0
        pe_sems = set()
        for r in self.records:
            g = get_group(r["과목명"])
            if g == "체육":
                pe_total += r["총학점"]
                for sc, v in r["학기별"].items():
                    if v > 0:
                        pe_sems.add(sc)
        if pe_total >= 10 and len(pe_sems) >= 6:
            self._add("D2", "체육 10학점 이상 + 매 학기 편성",
                     "PASS", f"체육 {pe_total:.0f}학점, 편성 학기 {len(pe_sems)}/6")
        elif pe_total >= 10:
            self._add("D2", "체육 10학점 이상 + 매 학기 편성",
                     "CHECK", f"체육 {pe_total:.0f}학점, 편성 학기 {len(pe_sems)}/6", manual=True)
        else:
            self._add("D2", "체육 10학점 이상 + 매 학기 편성",
                     "FAIL", f"체육 {pe_total:.0f}학점")

    # ============================================================
    # E. 순서/위계
    # ============================================================
    def check_E1_common_before_elective(self):
        common_by_group = defaultdict(list)
        elective_by_group = defaultdict(list)
        for r in self.records:
            stype = get_subject_type(r["과목명"])
            group = get_group(r["과목명"])
            if not stype or not group:
                continue
            first_sem = None
            for sc, v in sorted(r["학기별"].items()):
                if v > 0:
                    first_sem = sc
                    break
            if not first_sem:
                continue
            if stype == "공통":
                common_by_group[group].append((r["과목명"], first_sem))
            else:
                elective_by_group[group].append((r["과목명"], first_sem))

        violations = []
        for group in common_by_group:
            if group not in elective_by_group:
                continue
            common_latest = max(sem for _, sem in common_by_group[group])
            elective_earliest = min(sem for _, sem in elective_by_group[group])
            if elective_earliest < common_latest:
                violations.append(f"{group}(공통 최종 {common_latest}, 선택 시작 {elective_earliest})")
        if not violations:
            self._add("E1", "공통과목 → 선택과목 순서",
                     "PASS", "모든 교과군에서 공통이 선택보다 앞 또는 동시")
        else:
            self._add("E1", "공통과목 → 선택과목 순서",
                     "CHECK", " | ".join(violations), manual=True)

    def check_E2_hierarchy_order(self):
        violations = []
        for pre, post in HIERARCHY_PAIRS:
            pre_sem = None
            post_sem = None
            for r in self.records:
                first = None
                for sc, v in sorted(r["학기별"].items()):
                    if v > 0:
                        first = sc
                        break
                if r["과목명"] == pre and first:
                    pre_sem = first
                if r["과목명"] == post and first:
                    post_sem = first
            if pre_sem and post_sem and post_sem < pre_sem:
                violations.append(f"{pre}({pre_sem}) → {post}({post_sem})")
        if not violations:
            self._add("E2", "위계 과목 선후 순서",
                     "PASS", "모든 위계쌍 정상")
        else:
            self._add("E2", "위계 과목 선후 순서",
                     "FAIL", " | ".join(violations))

    # ============================================================
    # F. 과목명/형식
    # ============================================================
    def check_F1_subject_names(self):
        unknown = []
        for r in self.records:
            name = r["과목명"]
            if not name:
                continue
            if name in ALL_OFFICIAL_SUBJECTS:
                continue
            norm = _normalize(name)
            if norm in NORMALIZED_SUBJECTS:
                official = NORMALIZED_SUBJECTS[norm]
                if name != official:
                    unknown.append(f"{name} → {official} (띄어쓰기)")
            else:
                unknown.append(name)
        if not unknown:
            self._add("F1", "2022 개정 공식 과목명 사용",
                     "PASS", "모든 과목명 일치")
        else:
            self._add("F1", "2022 개정 공식 과목명 사용",
                     "CHECK", " | ".join(unknown[:8]), manual=True)

    def check_F2_curriculum_version(self):
        year = self.parsed["metadata"].get("year", "")
        if year and int(year) >= 2025:
            self._add("F2", "2022 개정 교육과정 적용",
                     "PASS", f"{year}학년도 입학생")
        else:
            self._add("F2", "2022 개정 교육과정 적용",
                     "INFO", f"입학년도: {year}", manual=True)

    def check_F3_recording_format(self):
        self._add("F3", "학점 기록 형식 (셀 서식)",
                 "INFO", "엑셀 셀 서식은 별도 수동 점검", manual=True)

    # ============================================================
    # G. 정성적 항목
    # ============================================================
    def check_G1_student_choice(self):
        elective_count = 0
        for r in self.records:
            stype = get_subject_type(r["과목명"])
            if stype and stype != "공통":
                elective_count += 1
        self._add("G1", "학생 과목 선택권 보장",
                 "INFO", f"선택과목 {elective_count}개 편성", manual=True)

    def check_G2_common_all_students(self):
        common_subjects = []
        for r in self.records:
            if get_subject_type(r["과목명"]) == "공통":
                common_subjects.append(r["과목명"])
        self._add("G2", "공통과목 전원 이수",
                 "INFO", f"공통과목 {len(common_subjects)}개: {', '.join(common_subjects[:5])}", manual=True)

    def check_G3_religion_plural(self):
        has_religion = any("종교" in r["과목명"] for r in self.records)
        if has_religion:
            self._add("G3", "종교 과목 복수 편성",
                     "CHECK", "종교 과목 편성 → 종교 외 과목과 복수 편성 여부 확인", manual=True)
        else:
            self._add("G3", "종교 과목 복수 편성",
                     "N/A", "종교 과목 미편성")

    # ============================================================
    # 헬퍼
    # ============================================================
    def _get_creative_credit(self):
        """요약영역에서 창의적 체험활동 학점 탐지"""
        df_sum = self.parsed["summary"]
        for _, row in df_sum.iterrows():
            row_str = " ".join(str(v) for v in row.values if v is not None)
            if "창의적" in row_str or "창체" in row_str:
                for v in row.values:
                    if v is None:
                        continue
                    try:
                        num = float(str(v).strip())
                        if 10 <= num <= 30:
                            return num
                    except (ValueError, TypeError):
                        continue
        return 18  # 기본값
