import pandas as pd


TARGET_COLUMNS = {
    "구분": "section",
    "교과(군)": "subject_group",
    "과목 유형": "subject_type",
    "과목": "course_name",
    "기본 학점": "base_credit",
    "운영 학점": "operation_credit",
    "비고": "remark"
}


SEMESTER_COLUMNS = {
    "1학년 1학기": "g1_s1",
    "1학년 2학기": "g1_s2",
    "2학년 1학기": "g2_s1",
    "2학년 2학기": "g2_s2",
    "3학년 1학기": "g3_s1",
    "3학년 2학기": "g3_s2"
}



def normalize_curriculum(df):

    df = df.fillna("")

    header_row = None

    for idx, row in df.iterrows():

        row_values = [str(v) for v in row.values]

        if "교과(군)" in row_values:
            header_row = idx
            break

    if header_row is None:
        raise Exception("헤더 행을 찾을 수 없습니다")

    df.columns = df.iloc[header_row]

    df = df[header_row + 1:]

    normalized_rows = []

    for _, row in df.iterrows():

        course_name = str(row.get("과목", "")).strip()

        if course_name == "":
            continue

        item = {
            "section": row.get("구분", ""),
            "subject_group": row.get("교과(군)", ""),
            "subject_type": row.get("과목 유형", ""),
            "course_name": course_name,
            "base_credit": row.get("기본 학점", 0),
            "operation_credit": row.get("운영 학점", 0),
            "g1_s1": row.get("1학년 1학기", ""),
            "g1_s2": row.get("1학년 2학기", ""),
            "g2_s1": row.get("2학년 1학기", ""),
            "g2_s2": row.get("2학년 2학기", ""),
            "g3_s1": row.get("3학년 1학기", ""),
            "g3_s2": row.get("3학년 2학기", ""),
            "remark": row.get("비고", "")
        }

        normalized_rows.append(item)

    result_df = pd.DataFrame(normalized_rows)

    return result_df
