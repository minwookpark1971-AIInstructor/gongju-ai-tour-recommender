# -*- coding: utf-8 -*-
"""try_recommend.py — 코스를 실제로 만들어 본다

실행: python try_recommend.py
"""

import db
import recommender as R

나 = {
    "age_group": "10대",
    "companion": "혼자",
    "preferences": {"역사": 1, "자연": 2, "체험": 5, "맛집": 3, "사진스팟": 5, "휴식": 2},
}

conn = db.get_conn()
spots = db.get_all_spots(conn)

for 시간 in (3, 6, 9):
    print("=" * 60)
    print(f"{시간}시간 코스")
    print("=" * 60)
    course, summary = R.make_course(나, spots, conn, hours=시간, show=True)
    for c in course:
        s = c["spot"]
        print(f"  {c['order']}. {s['name']} ({s['duration_min']}분) "
              f"점수 {c['score']:.3f}")
        print(f"     {c['reason']}")
    print(f"  → 관광 {summary['visit_minutes']}분 + 이동 {summary['travel_minutes']}분 "
          f"= 총 {summary['total_minutes']}분")
    print()

conn.close()
