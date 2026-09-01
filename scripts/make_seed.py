# -*- coding: utf-8 -*-
"""
make_seed.py — 시드 데이터 생성기 (교사 전용)

가상 이용자 50명과 평점 300건을 만들어 CSV로 저장한다.
학생은 이 파일을 실행할 일이 없다. 이미 만들어진 CSV를 받아서 쓴다.

핵심: 평점을 무작위로 만들면 안 된다.
     연령대·동행유형에 따라 좋아하는 테마가 다르도록 '편향'을 심어야
     추천 결과가 사람마다 달라지는 것이 눈에 보인다.

실행: python scripts/make_seed.py
"""

import csv
import os
import random

# 결과가 매번 같도록 씨앗값을 고정한다 (재현 가능한 데이터)
random.seed(42)

# 테마 6개 — 이 순서는 프로젝트 전체에서 절대 바뀌면 안 된다
THEMES = ["역사", "자연", "체험", "맛집", "사진스팟", "휴식"]

AGE_GROUPS = ["10대", "20대", "30대", "40대이상"]
COMPANIONS = ["혼자", "친구", "가족"]
GENDERS = ["남", "여", "응답안함"]

# 프로젝트 최상위 폴더 경로 (scripts 폴더의 부모)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

# ── 편향 설계 ────────────────────────────────────────────────
# 모든 사람의 기본 선호도는 2점에서 출발한다.
# 여기에 연령대·동행유형에 따라 점수를 더하거나 뺀다.
BASE_WEIGHT = 2

AGE_BIAS = {
    "10대":     {"체험": +2, "사진스팟": +2, "역사": -1},
    "20대":     {"맛집": +2, "사진스팟": +2, "휴식": -1},
    "30대":     {"맛집": +1, "자연": +1, "체험": +1},
    "40대이상": {"역사": +2, "휴식": +2, "사진스팟": -1},
}

COMPANION_BIAS = {
    "혼자": {"휴식": +1, "사진스팟": +1},
    "친구": {"맛집": +1, "사진스팟": +1},
    "가족": {"체험": +1, "자연": +1},
}

# 평점을 하나도 받지 못할 관광지 (신규 등록 관광지를 가정)
# → collab_score의 4순위(평점 0건 → 0.5) 폴백이 실제로 발동하는지 보기 위함
NO_RATING_SPOTS = ["대통길작은미술관", "자연미술관Ko"]


def build_weights(age_group, companion):
    """한 사람의 테마별 선호 점수(0~5)를 만든다."""
    w = {t: BASE_WEIGHT for t in THEMES}
    for theme, delta in AGE_BIAS[age_group].items():
        w[theme] += delta
    for theme, delta in COMPANION_BIAS[companion].items():
        w[theme] += delta
    # 0~5 범위를 벗어나지 않게 자른다
    return {t: max(0, min(5, v)) for t, v in w.items()}


def affinity(weights, spot_themes):
    """이 사람이 그 관광지를 얼마나 좋아할지 0~1로 계산한다.
    관광지가 가진 테마들의 선호 점수 평균을 5로 나눈 값."""
    scores = [weights[t] for t in spot_themes]
    return (sum(scores) / len(scores)) / 5


def main():
    # ── 1) 관광지 목록 읽기 (정제 정답 파일 사용) ──────────────
    spots_path = os.path.join(DATA, "_expected_spots.csv")
    with open(spots_path, encoding="utf-8-sig") as f:
        spots = list(csv.DictReader(f))
    print(f"관광지 {len(spots)}곳을 읽었습니다.")

    ratable = [s for s in spots if s["name"] not in NO_RATING_SPOTS]
    print(f"이 중 {len(NO_RATING_SPOTS)}곳은 평점을 만들지 않습니다 "
          f"(신규 관광지 상황을 만들기 위해): {', '.join(NO_RATING_SPOTS)}")

    # ── 2) 이용자 50명 만들기 ────────────────────────────────
    # 연령대 4개 × 동행 3개 = 12조합이 모두 최소 1명씩 나오도록
    # 조합을 순서대로 돌려가며 배정한다.
    combos = [(a, c) for a in AGE_GROUPS for c in COMPANIONS]
    users = []
    for i in range(50):
        age, comp = combos[i % len(combos)]
        users.append({
            "nickname": f"이용자{i + 1:02d}",
            "age_group": age,
            "gender": random.choice(GENDERS),
            "companion": comp,
            "weights": build_weights(age, comp),
        })
    print(f"이용자 {len(users)}명을 만들었습니다. (12개 조합 모두 포함)")

    # ── 3) 이용자 CSV 저장 (선호 테마 점수 포함) ──────────────
    users_path = os.path.join(DATA, "users_raw.csv")
    with open(users_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nickname", "age_group", "gender", "companion"] + THEMES)
        for u in users:
            w.writerow([u["nickname"], u["age_group"], u["gender"], u["companion"]]
                       + [u["weights"][t] for t in THEMES])
    print(f"저장: {users_path}")

    # ── 4) 평점 300건 만들기 ─────────────────────────────────
    # 한 사람당 6곳에 평점을 남긴다. (50명 × 6 = 300건)
    # 4곳은 '좋아할 만한 곳'에서, 2곳은 아무 곳에서나 고른다.
    #   → 좋아하는 곳만 고르면 데이터가 한쪽으로 쏠려서
    #     평점이 하나도 없는 관광지가 너무 많아진다.
    rows = []
    for u in users:
        affs = [(s, affinity(u["weights"], s["themes"].split(","))) for s in ratable]

        # 선호도를 가중치로 삼아 4곳을 뽑는다 (같은 곳이 중복되지 않게)
        picked = []
        pool = affs[:]
        for _ in range(4):
            total = sum(a for _, a in pool)
            r = random.uniform(0, total)
            acc = 0
            for idx, (s, a) in enumerate(pool):
                acc += a
                if acc >= r:
                    picked.append(s)
                    pool.pop(idx)
                    break

        # 나머지 2곳은 무작위로
        rest = [s for s, _ in pool]
        picked += random.sample(rest, 2)

        for s in picked:
            a = affinity(u["weights"], s["themes"].split(","))
            # 선호도 0~1을 평점 1~5로 바꾸고, 사람마다 다른 취향을 흉내내기 위해
            # -1 ~ +1 사이의 흔들림을 준다
            score = round(1 + 4 * a) + random.choice([-1, 0, 0, 0, 1])
            score = max(1, min(5, score))
            rows.append([u["nickname"], s["name"], score])

    ratings_path = os.path.join(DATA, "ratings_raw.csv")
    with open(ratings_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nickname", "spot_name", "score"])
        w.writerows(rows)
    print(f"평점 {len(rows)}건을 만들었습니다.")
    print(f"저장: {ratings_path}")

    # ── 5) 만든 결과가 의도대로인지 확인 ──────────────────────
    rated_names = {r[1] for r in rows}
    print()
    print("[확인] 평점이 하나도 없는 관광지:",
          ", ".join(sorted({s["name"] for s in spots} - rated_names)))
    # 테마별 '합계'로 보면 안 된다.
    # 역사 태그를 가진 관광지가 11곳, 맛집은 6곳이라 합계는 태그 개수에 끌려간다.
    # 편향이 제대로 심겼는지는 반드시 '평균 평점'으로 확인해야 한다.
    age_of = {u["nickname"]: u["age_group"] for u in users}
    themes_of = {s["name"]: s["themes"].split(",") for s in spots}
    for age in AGE_GROUPS:
        acc = {t: [] for t in THEMES}
        for nick, name, sc in rows:
            if age_of[nick] != age:
                continue
            for t in themes_of[name]:
                acc[t].append(sc)
        avg = {t: sum(v) / len(v) for t, v in acc.items() if v}
        best = sorted(avg.items(), key=lambda x: -x[1])[:3]
        print(f"[확인] {age:>6s} 평균 평점이 높은 테마 TOP3:",
              ", ".join(f"{t} {v:.2f}점" for t, v in best))


if __name__ == "__main__":
    main()
