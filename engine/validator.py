import pandas as pd

TOTAL_REQUIRED_CREDIT = 192
SUBJECT_REQUIRED_CREDIT = 174
CREATIVE_REQUIRED_CREDIT = 18

SUBJECT_GROUP_RULES = {
    "국어": 8,
    "수학": 8,
    "영어": 8,
    "사회": 6,
    "과학": 10,
    "체육": 10,
    "예술": 10
}

SEMESTERS = [
    "g1_s1",
    "g1_s2",
    "g2_s1",
    "g2_s2",
    "g3_s1",
    "g3_s2"
]

def validate_total_credit(df):

    total_credit = pd.to_numeric(
        df["operation_credit"],
        errors="coerce"
    ).fillna(0).sum()

    if total_credit < SUBJECT_REQUIRED_CREDIT:
        return {
            "status": "ERROR",
            "message": f"교과 학점 부족: {total_credit}"
        }

    return {
        "status": "PASS",
        "message": f"교과 학점 충족: {total_credit}"
    }



def validate_subject_groups(df):

    results = []

    for group_name, required_credit in SUBJECT_GROUP_RULES.items():

        group_df = df[
            df["subject_group"].astype(str).str.contains(group_name)
        ]

        credit_sum = pd.to_numeric(
            group_df["operation_credit"],
            errors="coerce"
        ).fillna(0).sum()

        if credit_sum < required_credit:
            results.append({
                "status": "ERROR",
                "message": f"{group_name} 교과군 학점 부족 ({credit_sum}/{required_credit})"
            })
        else:
            results.append({
                "status": "PASS",
                "message": f"{group_name} 교과군 충족 ({credit_sum}/{required_credit})"
            })

    return results

def validate_pe_semester(df):

    pe_df = df[
        df["subject_group"].astype(str).str.contains("체육")
    ]

    results = []

    for semester in SEMESTERS:

        semester_credit = pe_df[semester].replace("", 0)

        semester_credit = pd.to_numeric(
            semester_credit,
            errors="coerce"
        ).fillna(0).sum()

        if semester_credit <= 0:
            results.append({
                "status": "ERROR",
                "message": f"체육 미편성 학기: {semester}"
            })

    return results



def validate_curriculum(df):

    results = []

    results.append(validate_total_credit(df))

    results.extend(validate_subject_groups(df))

    results.extend(validate_pe_semester(df))

    return results
