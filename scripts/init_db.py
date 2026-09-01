# -*- coding: utf-8 -*-
"""
init_db.py — 2단계: 정제한 데이터를 SQLite 데이터베이스에 넣는다

실행:
    python scripts/init_db.py           # DB가 없을 때만 새로 만든다 (안전)
    python scripts/init_db.py --reset   # 기존 DB를 지우고 처음부터 다시 만든다

주의: --reset 을 쓰면 수업 중에 남긴 평점이 전부 사라진다.
      그래서 아무 옵션 없이 실행하면 아무것도 건드리지 않도록 만들었다.
"""

import csv
import os
import sqlite3
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
DB_PATH = os.path.join(DATA, "tour.db")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import clean_spots, THEMES   # noqa: E402

# 테이블 5개를 만드는 SQL
SCHEMA = """
CREATE TABLE spots (
  id           INTEGER PRIMARY KEY,
  name         TEXT    NOT NULL,
  region       TEXT    NOT NULL,
  themes       TEXT    NOT NULL,
  duration_min INTEGER NOT NULL,
  cost         INTEGER NOT NULL,
  indoor       INTEGER NOT NULL,
  description  TEXT,
  image        TEXT,
  lat          REAL,          -- 확장과제용 위도 (없어도 기본 기능은 동작)
  lon          REAL           -- 확장과제용 경도
);

CREATE TABLE users (
  id         INTEGER PRIMARY KEY,
  nickname   TEXT,
  age_group  TEXT,
  gender     TEXT,
  companion  TEXT,
  created_at TEXT
);

CREATE TABLE preferences (
  id      INTEGER PRIMARY KEY,
  user_id INTEGER,
  theme   TEXT,
  weight  INTEGER
);

CREATE TABLE ratings (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER,
  spot_id    INTEGER,
  score      INTEGER,
  created_at TEXT
);

CREATE TABLE courses (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER,
  spot_ids    TEXT,
  total_score REAL,
  created_at  TEXT
);
"""


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build(conn):
    """빈 데이터베이스에 표를 만들고 데이터를 넣는다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.executescript(SCHEMA)
    print("표 5개를 만들었습니다: spots, users, preferences, ratings, courses")

    # ── 관광지 넣기 ──────────────────────────────────────────
    spots = clean_spots(verbose=False)
    for s in spots:
        conn.execute(
            "INSERT INTO spots (name, region, themes, duration_min, cost, indoor, description, image)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (s["name"], s["region"], s["themes"], s["duration_min"],
             s["cost"], s["indoor"], s["description"], s["image"]))
    print(f"관광지 {len(spots)}곳을 넣었습니다.")

    # 확장과제용 좌표 — 파일이 있을 때만 넣는다.
    # 기본 과제에서는 이 값을 쓰지 않으므로 없어도 아무 문제 없다.
    geo_path = os.path.join(DATA, "spots_geo.csv")
    if os.path.exists(geo_path):
        n = 0
        for g in read_csv(geo_path):
            cur = conn.execute("UPDATE spots SET lat = ?, lon = ? WHERE name = ?",
                               (float(g["lat"]), float(g["lon"]), g["name"]))
            n += cur.rowcount
        print(f"확장과제용 좌표 {n}곳을 넣었습니다.")

    # 관광지 이름으로 id를 찾을 수 있게 표를 만들어 둔다
    spot_id = {name: sid for sid, name in conn.execute("SELECT id, name FROM spots")}

    # ── 이용자와 선호 테마 넣기 ──────────────────────────────
    users = read_csv(os.path.join(DATA, "users_raw.csv"))
    user_id = {}
    for u in users:
        cur = conn.execute(
            "INSERT INTO users (nickname, age_group, gender, companion, created_at)"
            " VALUES (?,?,?,?,?)",
            (u["nickname"], u["age_group"], u["gender"], u["companion"], now))
        user_id[u["nickname"]] = cur.lastrowid
        for theme in THEMES:
            conn.execute(
                "INSERT INTO preferences (user_id, theme, weight) VALUES (?,?,?)",
                (cur.lastrowid, theme, int(u[theme])))
    print(f"이용자 {len(users)}명과 선호 테마 {len(users) * len(THEMES)}건을 넣었습니다.")

    # ── 평점 넣기 ────────────────────────────────────────────
    ratings = read_csv(os.path.join(DATA, "ratings_raw.csv"))
    for r in ratings:
        conn.execute(
            "INSERT INTO ratings (user_id, spot_id, score, created_at) VALUES (?,?,?,?)",
            (user_id[r["nickname"]], spot_id[r["spot_name"]], int(r["score"]), now))
    print(f"평점 {len(ratings)}건을 넣었습니다.")

    conn.commit()


def main():
    reset = "--reset" in sys.argv

    if os.path.exists(DB_PATH) and not reset:
        # 이미 DB가 있으면 손대지 않는다.
        # 여기서 덮어쓰면 수업 중에 학생들이 남긴 평점이 전부 날아간다.
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        conn.close()
        print(f"이미 데이터베이스가 있습니다: {DB_PATH}")
        print(f"현재 평점 {n}건이 저장돼 있어서 아무것도 바꾸지 않았습니다.")
        print()
        print("처음부터 다시 만들고 싶다면 아래 명령을 쓰세요.")
        print("  python scripts/init_db.py --reset")
        print("  (주의: 지금까지 남긴 평점이 모두 사라집니다)")
        return

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("기존 데이터베이스를 지웠습니다.")

    conn = sqlite3.connect(DB_PATH)
    build(conn)
    conn.close()
    print()
    print(f"완료: {DB_PATH}")
    print("이제 python app.py 로 서버를 켜세요.")


if __name__ == "__main__":
    main()
