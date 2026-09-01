# -*- coding: utf-8 -*-
"""
recommender.py — 추천 알고리즘 (이 프로젝트에서 가장 중요한 파일)

추천 점수는 두 가지를 섞어서 만든다.

  1) 콘텐츠 기반 점수 : 내가 좋아하는 테마와 관광지 테마가 얼마나 닮았나
  2) 협업 필터링 점수 : 나와 비슷한 사람들이 그곳에 몇 점을 줬나

  최종 점수 = 0.6 × 콘텐츠 점수 + 0.4 × 협업 점수

넘파이(numpy) 같은 라이브러리를 쓰지 않고 순수 파이썬으로만 만들었다.
계산 과정을 손으로 따라가 볼 수 있어야 하기 때문이다.
"""

import math

# 테마 6개 — 순서가 곧 벡터의 자리번호다. 절대 바꾸면 안 된다.
#   역사=0번, 자연=1번, 체험=2번, 맛집=3번, 사진스팟=4번, 휴식=5번
THEMES = ["역사", "자연", "체험", "맛집", "사진스팟", "휴식"]

# 관광지 사이를 옮겨 다니는 데 걸리는 시간(분)
# 화면에 총 소요시간을 보여줄 때만 쓴다. 시간 예산 계산에는 넣지 않는다.
TRAVEL_MIN = 20

# 여행 시간별로 코스에 담을 관광지 개수
TARGET_COUNT = {3: 3, 6: 4, 9: 5}

MIN_SPOTS = 3          # 최소 3곳은 반드시 채운다
MAX_SAME_THEME = 2     # 같은 테마는 한 코스에 최대 2곳까지


# ═══════════════════════════════════════════════════════════
# 1. 벡터 만들기
# ═══════════════════════════════════════════════════════════

def to_pref_vector(pref_dict):
    """내 선호도를 6칸짜리 숫자 목록으로 바꾼다.

    {'역사':5, '자연':3, '맛집':4, '사진스팟':2}
        → [5, 3, 0, 4, 2, 0]
    적지 않은 테마는 0으로 채운다.
    """
    return [float(pref_dict.get(theme, 0)) for theme in THEMES]


def to_spot_vector(themes_text):
    """관광지 테마를 6칸짜리 0/1 목록으로 바꾼다.

    '역사,사진스팟' → [1, 0, 0, 0, 1, 0]
    있으면 1, 없으면 0.
    """
    owned = [t.strip() for t in themes_text.split(",")]
    return [1.0 if theme in owned else 0.0 for theme in THEMES]


# ═══════════════════════════════════════════════════════════
# 2. 코사인 유사도
# ═══════════════════════════════════════════════════════════

def cosine(a, b, show=False):
    """두 목록이 얼마나 닮았는지 0~1 사이 숫자로 알려준다.

    계산 방법
      ① 내적   : 같은 자리끼리 곱해서 모두 더한다
      ② 크기   : 각 목록의 제곱합에 루트를 씌운다
      ③ 유사도 : 내적 ÷ (크기A × 크기B)
    """
    # ① 내적
    dot = sum(x * y for x, y in zip(a, b))

    # ② 각 목록의 크기(길이)
    size_a = math.sqrt(sum(x * x for x in a))
    size_b = math.sqrt(sum(y * y for y in b))

    # 크기가 0이면 나눌 수 없다 (아무 테마도 안 고른 경우)
    if size_a == 0 or size_b == 0:
        if show:
            print("    크기가 0이라 유사도를 계산할 수 없습니다 → 0을 돌려줍니다")
        return 0.0

    result = dot / (size_a * size_b)

    if show:
        print(f"    내적     = {dot}")
        print(f"    크기A    = √{sum(x * x for x in a):.0f} = {size_a:.4f}")
        print(f"    크기B    = √{sum(y * y for y in b):.0f} = {size_b:.4f}")
        print(f"    유사도   = {dot} ÷ ({size_a:.4f} × {size_b:.4f}) = {result:.4f}")

    return result


def content_score(user_pref, spot_themes, show=False):
    """콘텐츠 기반 점수 (0~1).
    내 선호 테마와 관광지 테마가 닮을수록 1에 가깝다."""
    a = to_pref_vector(user_pref)
    b = to_spot_vector(spot_themes)
    if show:
        print(f"    내 선호   = {a}")
        print(f"    관광지    = {b}   ({spot_themes})")
    return cosine(a, b, show=show)


# ═══════════════════════════════════════════════════════════
# 3. 협업 필터링 점수
# ═══════════════════════════════════════════════════════════

def collab_score(user, spot_id, conn):
    """'나와 비슷한 사람들'이 그 관광지에 준 평균 평점 (0~1).

    비슷한 사람을 찾는 순서 — 앞에서 못 찾으면 다음으로 넘어간다.
      1순위: 같은 연령대 + 같은 동행유형
      2순위: 같은 연령대
      3순위: 전체 이용자
      4순위: 아무도 평점을 안 남겼다 → 0.5 (중립)

    이렇게 단계를 두는 이유:
      새로 생긴 관광지는 평점이 거의 없다. 1순위만 고집하면
      대부분의 관광지가 0.5로 깔려서 추천이 밋밋해진다.

    돌려주는 값: (점수, 설명문구) 두 개
    """
    age = user["age_group"]
    comp = user["companion"]

    # 1순위 — 같은 연령대 + 같은 동행유형
    row = conn.execute(
        "SELECT AVG(r.score), COUNT(*) FROM ratings r JOIN users u ON r.user_id = u.id"
        " WHERE r.spot_id = ? AND u.age_group = ? AND u.companion = ?",
        (spot_id, age, comp)).fetchone()
    if row[1] > 0:
        return row[0] / 5, f"{age}·{comp} 이용자 {row[1]}명 평점 {row[0]:.1f}점"

    # 2순위 — 같은 연령대
    row = conn.execute(
        "SELECT AVG(r.score), COUNT(*) FROM ratings r JOIN users u ON r.user_id = u.id"
        " WHERE r.spot_id = ? AND u.age_group = ?",
        (spot_id, age)).fetchone()
    if row[1] > 0:
        return row[0] / 5, f"{comp} 이용자 평점은 없어 {age} 전체 {row[1]}명 평점 {row[0]:.1f}점"

    # 3순위 — 전체 이용자
    row = conn.execute(
        "SELECT AVG(score), COUNT(*) FROM ratings WHERE spot_id = ?",
        (spot_id,)).fetchone()
    if row[1] > 0:
        return row[0] / 5, f"또래 평점이 없어 전체 {row[1]}명 평균 {row[0]:.1f}점 사용"

    # 4순위 — 평점이 하나도 없다
    return 0.5, "아직 평점이 없는 곳이라 중간값(0.5) 적용"


# ═══════════════════════════════════════════════════════════
# 4. 최종 점수
# ═══════════════════════════════════════════════════════════

def final_score(content, collab, w_content=0.6):
    """두 점수를 정해진 비율로 섞는다.
    w_content를 키우면 '내 취향'을, 줄이면 '남들 평점'을 더 믿는다."""
    return w_content * content + (1 - w_content) * collab


def build_reason(spot, user_pref, c_score, cf_note):
    """왜 이 관광지를 추천했는지 한 문장으로 만든다.

    주의: 관광지의 '첫 번째' 테마를 쓰면 안 된다.
      예) 베이커리밤마을의 테마는 '맛집,사진스팟' 이다.
          맛집에 2점, 사진스팟에 5점을 준 사람에게
          "선호하신 '맛집' 테마" 라고 하면 완전히 틀린 설명이 된다.
      그 관광지가 가진 테마들 중에서 '내가 가장 높은 점수를 준 테마'를 골라야
      진짜 추천 이유가 된다.
    """
    owned = [t.strip() for t in spot["themes"].split(",")]
    best = max(owned, key=lambda t: user_pref.get(t, 0))

    # 내가 그 테마에 0점을 줬다면 취향이 아니라 평점 때문에 추천된 것이다
    if user_pref.get(best, 0) == 0:
        return f"취향과는 다르지만 {cf_note}"

    return (f"선호하신 '{best}' 테마({user_pref[best]}점)와 "
            f"{int(c_score * 100)}% 일치, {cf_note}")
