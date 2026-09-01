# -*- coding: utf-8 -*-
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
