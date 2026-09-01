# -*- coding: utf-8 -*-
"""
app.py — 웹 서버 (프로그램의 시작점)

실행: python app.py
접속: http://127.0.0.1:5000
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session

import db
import geo
import recommender as R

app = Flask(__name__)

# 세션(누가 접속했는지 기억하는 기능)을 쓰려면 비밀 열쇠가 필요하다.
# 수업용이라 코드에 그대로 적었지만,
# 진짜 서비스라면 이 값은 절대 공개하면 안 된다.
app.secret_key = "tour-ai-gongju-2026"

THEMES = R.THEMES
AGE_GROUPS = ["10대", "20대", "30대", "40대이상"]
GENDERS = ["남", "여", "응답안함"]
COMPANIONS = ["혼자", "친구", "가족"]
HOURS = [3, 6, 9]

# ── 확장과제용 선택지 ──────────────────────────────────────
WEATHERS = ["맑음", "비", "더움", "추움"]
BUDGETS = [("제한없음", ""), ("1만원", "10000"), ("2만원", "20000"), ("3만원", "30000")]


@app.route("/")
def index():
    """첫 화면 — 취향을 입력받는다."""
    return render_template("index.html",
                           themes=THEMES, age_groups=AGE_GROUPS,
                           genders=GENDERS, companions=COMPANIONS, hours=HOURS,
                           weathers=WEATHERS, budgets=BUDGETS)


@app.route("/recommend", methods=["POST"])
def recommend():
    """추천 결과 화면.

    처리 순서
      ① 입력값을 받는다
      ② 이용자와 선호 테마를 데이터베이스에 저장한다
      ③ session에 내 번호를 적어 둔다 (나중에 평점을 남길 때 쓴다)
      ④ 코스를 만든다
      ⑤ 만든 코스를 courses 표에 기록한다
    """
    form = request.form

    # ① 입력값 받기
    nickname = form.get("nickname", "").strip() or "익명"
    age_group = form.get("age_group", AGE_GROUPS[0])
    gender = form.get("gender", GENDERS[-1])
    companion = form.get("companion", COMPANIONS[0])
    hours = int(form.get("hours", 3))
    w_content = float(form.get("w_content", 0.6))

    # 테마별 선호 점수 (0~5)
    preferences = {t: int(form.get(f"theme_{t}", 0)) for t in THEMES}

    # ── 확장과제 입력 (안 고르면 전부 꺼진 상태 = 기본 동작) ──
    weather = form.get("weather") or None
    if weather == "맑음":
        weather = None                      # 맑으면 가산점이 없으므로 끈 것과 같다
    raw_budget = form.get("max_cost", "").strip()
    max_cost = int(raw_budget) if raw_budget else None
    real_distance = form.get("real_distance") == "on"

    conn = db.get_conn()

    # ② 이용자 저장 → ③ session에 기록
    user_id = db.add_user(conn, nickname, age_group, gender, companion, preferences)
    session["user_id"] = user_id
    session["nickname"] = nickname

    # ④ 코스 만들기
    user = db.get_user(conn, user_id)
    spots = db.get_all_spots(conn)
    course, summary = R.make_course(user, spots, conn,
                                    hours=hours, w_content=w_content,
                                    weather=weather, max_cost=max_cost,
                                    real_distance=real_distance)

    # [확장 3] 코스를 지도 위에 그리기 위한 좌표를 계산한다
    map_bg, map_route = geo.to_svg_points(spots, [c["spot"] for c in course])

    # ⑤ 만든 코스 기록
    if course:
        db.add_course(conn, user_id,
                      [c["spot"]["id"] for c in course], summary["avg_score"])
    conn.close()

    return render_template("result.html",
                           user=user, course=course, summary=summary,
                           hours=hours, w_content=w_content,
                           themes=THEMES, preferences=preferences,
                           gender=gender,
                           weather=form.get("weather", ""), max_cost=raw_budget,
                           real_distance=real_distance,
                           weathers=WEATHERS, budgets=BUDGETS,
                           map_bg=map_bg, map_route=map_route)


@app.route("/spots")
def spots():
    """관광지 목록 — ?theme=역사 처럼 테마로 걸러 볼 수 있다."""
    theme = request.args.get("theme")
    conn = db.get_conn()
    items = db.get_all_spots(conn, theme=theme)
    # 각 관광지의 평균 평점도 같이 붙인다
    for s in items:
        s["avg"], s["cnt"] = db.get_spot_rating(conn, s["id"])
    conn.close()
    return render_template("spots.html", spots=items, themes=THEMES, current=theme)


@app.route("/spots/<int:spot_id>")
def spot_detail(spot_id):
    """관광지 상세 — 평점을 남길 수 있다."""
    conn = db.get_conn()
    spot = db.get_spot(conn, spot_id)
    if spot is None:
        conn.close()
        return "그런 관광지가 없습니다.", 404
    avg, cnt = db.get_spot_rating(conn, spot_id)

    # 내가 이미 이 곳에 점수를 줬는지 확인한다
    my_score = None
    if session.get("user_id"):
        row = conn.execute(
            "SELECT score FROM ratings WHERE user_id = ? AND spot_id = ?",
            (session["user_id"], spot_id)).fetchone()
        my_score = row["score"] if row else None
    conn.close()

    return render_template("spot_detail.html", spot=spot, avg=avg, cnt=cnt,
                           my_score=my_score,
                           logged_in=bool(session.get("user_id")))


@app.route("/spots/<int:spot_id>/rate", methods=["POST"])
def rate(spot_id):
    """별점 저장. 취향 입력을 안 한 사람은 저장할 수 없다."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("index"))
    score = int(request.form.get("score", 3))
    conn = db.get_conn()
    db.add_rating(conn, user_id, spot_id, score)
    conn.close()
    return redirect(url_for("spot_detail", spot_id=spot_id))


@app.route("/popular")
def popular():
    """[확장 4] 최근에 많이 추천된 관광지와 코스를 보여준다.

    courses 표에 쌓인 기록을 그대로 활용한다.
    학생들이 추천을 받을수록 이 화면이 채워진다.
    """
    days = int(request.args.get("days", 7))
    conn = db.get_conn()
    spots, course_count = db.popular_spots(conn, days=days)
    courses = db.popular_courses(conn, days=days)
    conn.close()
    top = spots[0]["pick_count"] if spots else 1
    ranked = [(s, int(s["pick_count"] / top * 100)) for s in spots]
    return render_template("popular.html", ranked=ranked, courses=courses,
                           course_count=course_count, days=days)


@app.route("/stats")
def stats():
    """데이터 분석 대시보드."""
    conn = db.get_conn()
    theme_counts = db.stats_theme_counts(conn)
    age_top = db.stats_age_top_themes(conn)
    top_rated = db.stats_top_rated(conn)
    total_spots = conn.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_ratings = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    conn.close()

    # 막대그래프의 길이를 퍼센트로 계산해 둔다 (화면에서 div 너비로 쓴다)
    max_count = max(theme_counts.values()) if theme_counts else 1
    theme_bars = [(t, c, int(c / max_count * 100)) for t, c in theme_counts.items()]

    return render_template("stats.html",
                           theme_bars=theme_bars, age_top=age_top,
                           top_rated=top_rated, total_spots=total_spots,
                           total_users=total_users, total_ratings=total_ratings)


if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH):
        print("데이터베이스가 없습니다. 먼저 아래 명령을 실행하세요.")
        print("  python scripts/init_db.py")
    else:
        # 발표 때 옆 조에게 보여주려면 host="0.0.0.0" 으로 바꾼다
        app.run(debug=True, port=5000)
