# -*- coding: utf-8 -*-
"""
db.py — 데이터베이스에 연결하고 자료를 꺼내오는 함수 모음

app.py 가 SQL을 직접 쓰지 않도록, 자주 쓰는 조회를 여기에 모아 두었다.
"""

import os
import sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "tour.db")

THEMES = ["역사", "자연", "체험", "맛집", "사진스팟", "휴식"]


def get_conn():
    """데이터베이스에 연결한다.
    row_factory를 설정하면 결과를 딕셔너리처럼 컬럼 이름으로 쓸 수 있다."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 관광지 ──────────────────────────────────────────────────

def get_all_spots(conn, theme=None):
    """관광지 전체를 가져온다. theme을 주면 그 테마를 가진 곳만 가져온다."""
    if theme:
        rows = conn.execute(
            "SELECT * FROM spots WHERE themes LIKE ? ORDER BY name",
            (f"%{theme}%",)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM spots ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_spot(conn, spot_id):
    row = conn.execute("SELECT * FROM spots WHERE id = ?", (spot_id,)).fetchone()
    return dict(row) if row else None


def get_spot_rating(conn, spot_id):
    """관광지의 평균 평점과 평점 개수를 돌려준다."""
    row = conn.execute(
        "SELECT AVG(score) AS avg, COUNT(*) AS cnt FROM ratings WHERE spot_id = ?",
        (spot_id,)).fetchone()
    return (round(row["avg"], 1) if row["cnt"] else None), row["cnt"]


# ── 이용자 ──────────────────────────────────────────────────

def add_user(conn, nickname, age_group, gender, companion, preferences):
    """새 이용자와 그 사람의 선호 테마를 저장하고 id를 돌려준다."""
    cur = conn.execute(
        "INSERT INTO users (nickname, age_group, gender, companion, created_at)"
        " VALUES (?,?,?,?,?)",
        (nickname, age_group, gender, companion, now()))
    user_id = cur.lastrowid
    for theme in THEMES:
        conn.execute(
            "INSERT INTO preferences (user_id, theme, weight) VALUES (?,?,?)",
            (user_id, theme, int(preferences.get(theme, 0))))
    conn.commit()
    return user_id


def get_user(conn, user_id):
    """이용자 정보와 선호 테마를 함께 가져온다."""
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return None
    user = dict(row)
    prefs = conn.execute(
        "SELECT theme, weight FROM preferences WHERE user_id = ?", (user_id,)).fetchall()
    user["preferences"] = {p["theme"]: p["weight"] for p in prefs}
    return user


# ── 평점 ────────────────────────────────────────────────────

def add_rating(conn, user_id, spot_id, score):
    """같은 사람이 같은 곳에 두 번 평점을 남기면 새 점수로 바꾼다."""
    old = conn.execute(
        "SELECT id FROM ratings WHERE user_id = ? AND spot_id = ?",
        (user_id, spot_id)).fetchone()
    if old:
        conn.execute("UPDATE ratings SET score = ?, created_at = ? WHERE id = ?",
                     (score, now(), old["id"]))
    else:
        conn.execute(
            "INSERT INTO ratings (user_id, spot_id, score, created_at) VALUES (?,?,?,?)",
            (user_id, spot_id, score, now()))
    conn.commit()


# ── 코스 ────────────────────────────────────────────────────

def add_course(conn, user_id, spot_ids, total_score):
    conn.execute(
        "INSERT INTO courses (user_id, spot_ids, total_score, created_at) VALUES (?,?,?,?)",
        (user_id, ",".join(str(i) for i in spot_ids), total_score, now()))
    conn.commit()


# ── 통계 (/stats 화면용) ────────────────────────────────────

def stats_theme_counts(conn):
    """테마별로 관광지가 몇 곳인지 센다.
    themes 컬럼이 '역사,자연' 처럼 붙어 있어서 SQL 한 줄로는 셀 수 없다.
    파이썬으로 하나씩 풀어서 센다."""
    counts = {t: 0 for t in THEMES}
    for row in conn.execute("SELECT themes FROM spots"):
        for t in row["themes"].split(","):
            if t in counts:
                counts[t] += 1
    return counts


def stats_age_top_themes(conn, top_n=3):
    """연령대별로 선호 점수가 높은 테마 TOP3를 뽑는다."""
    rows = conn.execute(
        "SELECT u.age_group, p.theme, AVG(p.weight) AS w"
        " FROM preferences p JOIN users u ON p.user_id = u.id"
        " GROUP BY u.age_group, p.theme").fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["age_group"], []).append((r["theme"], round(r["w"], 2)))
    return {age: sorted(items, key=lambda x: -x[1])[:top_n]
            for age, items in sorted(grouped.items())}


# ── [확장 4] 인기 코스 ──────────────────────────────────────

def popular_spots(conn, days=7, limit=10):
    """최근에 만들어진 코스에 가장 많이 담긴 관광지 순위.

    courses 표에는 spot_ids가 '3,7,12' 처럼 한 칸에 붙어 있어서
    SQL만으로는 세기 어렵다. 파이썬으로 풀어서 센다.
    """
    rows = conn.execute(
        "SELECT spot_ids FROM courses"
        " WHERE created_at >= datetime('now', 'localtime', ?)",
        (f"-{days} days",)).fetchall()

    count = {}
    for r in rows:
        for sid in r["spot_ids"].split(","):
            if sid.strip():
                count[int(sid)] = count.get(int(sid), 0) + 1
    if not count:
        return [], 0

    order = sorted(count.items(), key=lambda x: -x[1])[:limit]
    result = []
    for sid, n in order:
        spot = get_spot(conn, sid)
        if spot:
            spot["pick_count"] = n
            result.append(spot)
    return result, len(rows)


def popular_courses(conn, days=7, limit=5):
    """최근에 가장 많이 만들어진 코스 조합 순위."""
    rows = conn.execute(
        "SELECT spot_ids, COUNT(*) AS cnt, AVG(total_score) AS avg"
        " FROM courses WHERE created_at >= datetime('now', 'localtime', ?)"
        " GROUP BY spot_ids ORDER BY cnt DESC, avg DESC LIMIT ?",
        (f"-{days} days", limit)).fetchall()

    result = []
    for r in rows:
        names = []
        for sid in r["spot_ids"].split(","):
            spot = get_spot(conn, int(sid))
            if spot:
                names.append(spot["name"])
        result.append({"names": names, "cnt": r["cnt"],
                       "avg": round(r["avg"], 3) if r["avg"] else 0})
    return result


def stats_top_rated(conn, limit=10):
    """평균 평점이 높은 관광지 순위."""
    rows = conn.execute(
        "SELECT s.name, s.themes, AVG(r.score) AS avg, COUNT(*) AS cnt"
        " FROM ratings r JOIN spots s ON r.spot_id = s.id"
        " GROUP BY s.id ORDER BY avg DESC, cnt DESC LIMIT ?", (limit,)).fetchall()
    return [{"name": r["name"], "themes": r["themes"],
             "avg": round(r["avg"], 2), "cnt": r["cnt"]} for r in rows]
