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
