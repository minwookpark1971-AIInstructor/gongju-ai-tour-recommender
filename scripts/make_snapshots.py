# -*- coding: utf-8 -*-
"""
make_snapshots.py — 단계별 완성본 폴더 생성기 (교사 전용)

수업 중에 진도가 뒤처진 학생이 복사해서 이어갈 수 있도록
step2_done ~ step7_done 폴더를 만든다.

중요: 이 폴더들을 손으로 만들어 두면 안 된다.
     나중에 recommender.py 를 고치면 6개 폴더가 전부 옛날 코드로 남는다.
     그래서 항상 '완성본에서 잘라내는' 방식으로 자동 생성한다.

실행: python scripts/make_snapshots.py
"""

import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "snapshots")

# recommender.py 를 어디에서 자를지 정한다.
# 완성본은 큰 제목으로 구역이 나뉘어 있어서 그 제목을 기준으로 자르면 된다.
RECOMMENDER_CUT = {
    4: "# 3. 협업 필터링 점수",   # Step4 = 1~2구역 (벡터 + 코사인 + content_score)
    5: "# 5. 코스 만들기",        # Step5 = 1~4구역 (+ collab_score, final_score)
    6: None,                      # Step6 = 전체
}

STEP_TITLE = {
    2: "데이터 정제와 DB 적재까지 끝난 상태",
    3: "데이터 분석 대시보드(/stats)까지 끝난 상태",
    4: "콘텐츠 기반 점수(content_score)까지 끝난 상태",
    5: "협업 필터링과 하이브리드 점수까지 끝난 상태",
    6: "코스 생성(make_course)까지 끝난 상태",
    7: "웹 화면까지 전부 끝난 완성본",
}

NEXT_STEP = {
    2: "Step 3 — /stats 화면으로 데이터 분포를 확인합니다.",
    3: "Step 4 — recommender.py 에 content_score 를 만듭니다.",
    4: "Step 5 — collab_score 와 하이브리드 점수를 만듭니다.",
    5: "Step 6 — make_course 로 코스를 만듭니다.",
    6: "Step 7 — 입력·결과·목록·상세 화면을 만듭니다.",
    7: "Step 8 — 가중치를 바꿔 보고 발표를 준비합니다.",
}


# ── Step2 용 app.py (아직 화면이 없다) ────────────────────────
APP_HELLO = '''# -*- coding: utf-8 -*-
"""app.py — 아직은 글자 하나만 보여주는 서버입니다."""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "AI 관광 추천 서비스"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
'''

# ── Step3~6 용 app.py (/stats 까지만) ────────────────────────
APP_STATS = '''# -*- coding: utf-8 -*-
"""app.py — 데이터 분석 화면(/stats)까지 만든 상태입니다."""

import os
from flask import Flask, render_template

import db

app = Flask(__name__)
app.secret_key = "tour-ai-gongju-2026"


@app.route("/")
def index():
    return render_template("stats.html", **stats_data())


@app.route("/stats")
def stats():
    return render_template("stats.html", **stats_data())


def stats_data():
    """대시보드에 보여줄 숫자들을 모아서 돌려준다."""
    conn = db.get_conn()
    theme_counts = db.stats_theme_counts(conn)
    age_top = db.stats_age_top_themes(conn)
    top_rated = db.stats_top_rated(conn)
    total_spots = conn.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_ratings = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    conn.close()

    max_count = max(theme_counts.values()) if theme_counts else 1
    theme_bars = [(t, c, int(c / max_count * 100)) for t, c in theme_counts.items()]
    return dict(theme_bars=theme_bars, age_top=age_top, top_rated=top_rated,
                total_spots=total_spots, total_users=total_users,
                total_ratings=total_ratings)


if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH):
        print("데이터베이스가 없습니다. 먼저 python scripts/init_db.py 를 실행하세요.")
    else:
        app.run(debug=True, port=5000)
'''

# ── Step3~6 용 base.html ────────────────────────────────────
# 완성본의 base.html 은 '관광지 목록' 링크를 갖고 있는데,
# Step3~6 단계의 app.py 에는 아직 /spots 라우트가 없다.
# 그대로 쓰면 url_for('spots') 에서 오류가 나므로 링크를 뺀 것을 따로 쓴다.
BASE_SIMPLE = '''<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}AI 관광 추천 서비스{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <header>
    <div class="wrap">
      <a class="logo" href="{{ url_for('index') }}">공주 AI 관광 추천</a>
      <nav>
        <a href="{{ url_for('stats') }}">데이터 분석</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    {% block content %}{% endblock %}
  </main>

  <footer>
    <div class="wrap">
      충청남도 공주시 관광지 30곳 · 경영정보 전공 실습 프로젝트
    </div>
  </footer>
</body>
</html>
'''


# ── 단계별 연습용 실행 파일 ──────────────────────────────────
TRY_STEP4 = '''# -*- coding: utf-8 -*-
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
'''

TRY_STEP5 = '''# -*- coding: utf-8 -*-
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
'''

TRY_STEP6 = '''# -*- coding: utf-8 -*-
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
'''


def cut_recommender(step):
    """완성된 recommender.py 를 해당 단계까지만 잘라서 돌려준다."""
    with open(os.path.join(BASE, "recommender.py"), encoding="utf-8") as f:
        lines = f.readlines()

    heading = RECOMMENDER_CUT[step]
    if heading is None:
        return "".join(lines)

    for i, line in enumerate(lines):
        if line.strip().startswith(heading):
            # 제목 위의 구분선(═)까지 함께 잘라낸다
            end = i
            while end > 0 and lines[end - 1].lstrip().startswith("# ═"):
                end -= 1
            return "".join(lines[:end]).rstrip() + "\n"

    raise ValueError(f"recommender.py 에서 '{heading}' 을 찾지 못했습니다")


def copy(src_rel, dst_dir, dst_rel=None):
    src = os.path.join(BASE, src_rel)
    dst = os.path.join(dst_dir, dst_rel or src_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def write(text, dst_dir, rel):
    dst = os.path.join(dst_dir, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def build_step(step):
    folder = os.path.join(OUT, f"step{step}_done")
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

    # ── 어느 단계든 공통으로 들어가는 것 ──
    copy("requirements.txt", folder)
    for name in ("spots_raw.csv", "users_raw.csv", "ratings_raw.csv"):
        copy(f"data/{name}", folder)
    copy("scripts/preprocess.py", folder)
    copy("scripts/init_db.py", folder)

    # ── 단계별로 달라지는 것 ──
    if step == 2:
        write(APP_HELLO, folder, "app.py")
    else:
        copy("db.py", folder)
        copy("static/style.css", folder)
        copy("templates/stats.html", folder)
        copy("data/tour.db", folder)          # 바로 실행되도록 DB도 넣어 준다

    if step in (3, 4, 5, 6):
        write(APP_STATS, folder, "app.py")
        write(BASE_SIMPLE, folder, "templates/base.html")   # /spots 링크 없는 것
    elif step == 7:
        copy("templates/base.html", folder)

    if step in RECOMMENDER_CUT:
        write(cut_recommender(step), folder, "recommender.py")
        write({4: TRY_STEP4, 5: TRY_STEP5, 6: TRY_STEP6}[step],
              folder, "try_recommend.py")

    if step == 7:
        copy("app.py", folder)
        copy("recommender.py", folder)
        copy("geo.py", folder)                 # 확장과제용 (기본 기능은 안 씀)
        copy("data/spots_geo.csv", folder)
        for name in ("index.html", "result.html", "spots.html",
                     "spot_detail.html", "popular.html"):
            copy(f"templates/{name}", folder)

    # ── 안내문 ──
    실행 = ["pip install flask pandas"]
    if step == 2:
        실행.append("python scripts/init_db.py")
    실행.append("python app.py")
    if step in (4, 5, 6):
        실행.append("python try_recommend.py")

    readme = f"""# step{step}_done — {STEP_TITLE[step]}

수업을 따라오지 못했을 때 **이 폴더를 통째로 복사해서** 이어가면 된다.

## 실행 방법

```
{chr(10).join(실행)}
```

## 다음에 할 일

{NEXT_STEP[step]}

---
이 폴더는 `scripts/make_snapshots.py` 가 완성본에서 자동으로 만들어 낸 것이다.
직접 고치지 말고, 완성본을 고친 뒤 생성기를 다시 돌릴 것.
"""
    write(readme, folder, "README.md")

    n = sum(len(files) for _, _, files in os.walk(folder))
    return folder, n


def main():
    os.makedirs(OUT, exist_ok=True)
    print("단계별 완성본 폴더를 만듭니다...")
    print()
    for step in (2, 3, 4, 5, 6, 7):
        folder, n = build_step(step)
        print(f"  step{step}_done  파일 {n:>2}개  — {STEP_TITLE[step]}")
    print()
    print(f"저장 위치: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
