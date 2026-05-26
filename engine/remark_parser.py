KEYWORDS = [
    "공동교육과정",
    "온라인",
    "학교연합",
    "순차개설",
    "미개설 가능",
    "공유캠퍼스"
]



def extract_manual_review(df):

    results = []

    for _, row in df.iterrows():

        remark = str(row.get("remark", ""))

        if remark.strip() == "":
            continue

        found_keywords = []

        for keyword in KEYWORDS:

            if keyword in remark:
                found_keywords.append(keyword)

        if found_keywords:

            results.append({
                "course_name": row.get("course_name"),
                "remark": remark,
                "keywords": ", ".join(found_keywords)
            })

    return results
