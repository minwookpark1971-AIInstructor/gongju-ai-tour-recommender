# -*- coding: utf-8 -*-
"""try_recommend.py — content_score 가 잘 동작하는지 직접 확인해 보는 파일

실행: python try_recommend.py
"""

import recommender as R

# 손으로 계산해 볼 예제
# 내 선호  : 역사5, 자연3, 체험0, 맛집4, 사진스팟2, 휴식0
# 관광지   : 공산성 (역사, 사진스팟)
내_선호 = {"역사": 5, "자연": 3, "체험": 0, "맛집": 4, "사진스팟": 2, "휴식": 0}

print("=" * 55)
print("공산성 (테마: 역사,사진스팟) 과 내 취향은 얼마나 닮았을까?")
print("=" * 55)
점수 = R.content_score(내_선호, "역사,사진스팟", show=True)
print()
print(f"결과: {점수:.4f}")
print()
print("공책에 직접 계산해서 위 숫자와 같은지 확인해 보세요.")
print("  내적 ÷ (크기A × 크기B)")
