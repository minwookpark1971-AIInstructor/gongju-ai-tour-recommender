# -*- coding: utf-8 -*-
"""try_recommend.py — 콘텐츠 점수와 협업 점수를 합쳐 본다

실행: python try_recommend.py
"""

import db
import recommender as R

내_선호 = {"역사": 5, "자연": 3, "체험": 0, "맛집": 4, "사진스팟": 2, "휴식": 0}
나 = {"age_group": "40대이상", "companion": "가족"}

conn = db.get_conn()
spots = db.get_all_spots(conn)

print(f"{'관광지':<22} {'취향':>6} {'평점':>6} {'최종':>6}   근거")
print("-" * 90)
결과 = []
for s in spots:
    c = R.content_score(내_선호, s["themes"])
    cf, note = R.collab_score(나, s["id"], conn)
    결과.append((R.final_score(c, cf), s["name"], c, cf, note))

for final, name, c, cf, note in sorted(결과, reverse=True)[:10]:
    print(f"{name:<22} {c:>6.3f} {cf:>6.3f} {final:>6.3f}   {note}")

print()
print("가중치를 바꿔 보세요. final_score(c, cf, w_content=0.9) 처럼요.")
conn.close()
