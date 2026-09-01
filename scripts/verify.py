# -*- coding: utf-8 -*-
"""
verify.py — 검증 스크립트 (교사 전용)

수업 전날 이 파일 하나만 돌려서 전부 통과하면 준비가 끝난 것이다.
하나라도 실패하면 그 항목을 고치고 다시 돌린다.

실행: python scripts/verify.py
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

import db                       # noqa: E402
import recommender as R         # noqa: E402
from preprocess import read_csv, clean_spots   # noqa: E402

DATA = os.path.join(BASE, "data")

results = []


def check(no, title, ok, detail=""):
    results.append(ok)
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {no:>2}. {title}")
    if detail:
        print(f"        {detail}")


def main():
    conn = db.get_conn()
    spots = db.get_all_spots(conn)

    # 0. 원본 32행 → 정제 30행
    raw = read_csv(os.path.join(DATA, "spots_raw.csv"))
    clean = clean_spots(verbose=False)
    check(0, "spots_raw.csv 32행 → 정제 후 30행",
          len(raw) == 32 and len(clean) == 30,
          f"원본 {len(raw)}행 → 정제 {len(clean)}행")

    # 1. 테마가 표준 6개 안에만 존재
    bad = {t for s in spots for t in s["themes"].split(",") if t not in R.THEMES}
    check(1, "모든 테마가 표준 6개 안에만 존재",
          len(spots) == 30 and not bad,
          f"관광지 {len(spots)}곳" + (f" / 잘못된 테마 {bad}" if bad else " / 잘못된 테마 없음"))

    # 2. 소요시간 값과 평균
    durations = [s["duration_min"] for s in spots]
    allowed = {30, 45, 60, 90, 120}
    avg = sum(durations) / len(durations)
    check(2, "소요시간이 {30,45,60,90,120} 안에 있고 평균 60.0분",
          set(durations) <= allowed and abs(avg - 60.0) < 0.05,
          f"평균 {avg:.1f}분")

    # 3. 관광지명 중복 없음
    names = [s["name"].strip() for s in spots]
    check(3, "관광지명 중복 0건",
          len(names) == len(set(names)),
          f"고유 이름 {len(set(names))}개")

    # 4. 시드 이용자 50명 + 12조합 모두 존재
    #    '정확히 50명'으로 검사하면 안 된다.
    #    학생이 앱을 한 번이라도 쓰면 users에 행이 늘어나서 검증이 깨진다.
    #    검사해야 할 것은 '시드 데이터가 그대로 있는가'이지 '총 인원'이 아니다.
    seed = conn.execute(
        "SELECT age_group, companion FROM users WHERE nickname LIKE '이용자%'").fetchall()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    combos = {(u["age_group"], u["companion"]) for u in seed}
    check(4, "시드 이용자 50명 유지, 연령×동행 12조합 모두 1명 이상",
          len(seed) == 50 and len(combos) == 12,
          f"시드 {len(seed)}명 / {len(combos)}조합"
          f" (실습으로 추가된 이용자 {total_users - len(seed)}명은 정상)")

    # 5. 평점 300건 이상, 점수 1~5
    scores = [r["score"] for r in conn.execute("SELECT score FROM ratings")]
    check(5, "평점 300건 이상, 점수가 모두 1~5",
          len(scores) >= 300 and all(1 <= s <= 5 for s in scores),
          f"{len(scores)}건 (시드 300건 + 실습 {len(scores) - 300}건)"
          f" / 최소 {min(scores)} 최대 {max(scores)}")

    # 6. 손계산 예제와 일치
    pref = {"역사": 5, "자연": 3, "체험": 0, "맛집": 4, "사진스팟": 2, "휴식": 0}
    got = R.content_score(pref, "역사,사진스팟")
    check(6, "content_score가 손계산 0.6736과 소수점 4자리까지 일치",
          abs(got - 0.6736) < 1e-4,
          f"계산 결과 {got:.4f}")

    # 7. 협업 필터링 폴백 4단계가 모두 발동
    fired = set()
    for age in ["10대", "20대", "30대", "40대이상"]:
        for comp in ["혼자", "친구", "가족"]:
            u = {"age_group": age, "companion": comp}
            for s in spots:
                _, note = R.collab_score(u, s["id"], conn)
                if "평점이 없는 곳" in note:
                    fired.add(4)
                elif "전체" in note and "또래" in note:
                    fired.add(3)
                elif "전체" in note:
                    fired.add(2)
                else:
                    fired.add(1)
    check(7, "협업 필터링 폴백 1·2·3·4순위가 각각 최소 1회 발동",
          fired == {1, 2, 3, 4},
          f"발동한 단계: {sorted(fired)}")

    # 8. 여행시간별 개수
    u = {"age_group": "20대", "companion": "친구",
         "preferences": {"역사": 3, "자연": 3, "체험": 3, "맛집": 3, "사진스팟": 3, "휴식": 3}}
    counts = {}
    for h in (3, 6, 9):
        course, _ = R.make_course(u, spots, conn, hours=h)
        counts[h] = len(course)
    check(8, "3/6/9시간 요청 시 각각 3/4/5곳 반환",
          counts == {3: 3, 6: 4, 9: 5},
          f"{counts}")

    # 9. 한 코스에 같은 테마 3곳 이상 없음
    worst = 0
    for h in (3, 6, 9):
        for age in ["10대", "40대이상"]:
            uu = {"age_group": age, "companion": "혼자", "preferences": u["preferences"]}
            course, _ = R.make_course(uu, spots, conn, hours=h)
            cnt = {}
            for c in course:
                for t in c["spot"]["themes"].split(","):
                    cnt[t] = cnt.get(t, 0) + 1
            worst = max(worst, max(cnt.values()) if cnt else 0)
    check(9, "한 코스에 동일 테마가 3곳 이상 들어가지 않음",
          worst <= R.MAX_SAME_THEME,
          f"한 코스 내 같은 테마 최대 {worst}곳")

    # 10. 서로 다른 이용자의 코스가 실제로 달라지는가 (데모 성패)
    teen = {"age_group": "10대", "companion": "혼자",
            "preferences": {"역사": 1, "자연": 2, "체험": 5, "맛집": 3, "사진스팟": 5, "휴식": 2}}
    senior = {"age_group": "40대이상", "companion": "가족",
              "preferences": {"역사": 5, "자연": 4, "체험": 2, "맛집": 3, "사진스팟": 1, "휴식": 5}}
    c1, _ = R.make_course(teen, spots, conn, hours=6)
    c2, _ = R.make_course(senior, spots, conn, hours=6)
    n1 = [c["spot"]["name"] for c in c1]
    n2 = [c["spot"]["name"] for c in c2]
    diff = len(set(n1) ^ set(n2)) // 2
    check(10, "10대·혼자 vs 40대이상·가족 코스가 최소 2곳 이상 다름",
          diff >= 2,
          f"서로 다른 곳 {diff}곳\n         10대·혼자   : {', '.join(n1)}"
          f"\n         40대이상·가족: {', '.join(n2)}")

    # 11. 가중치를 바꾸면 코스가 달라지는가
    a, _ = R.make_course(teen, spots, conn, hours=6, w_content=0.9)
    b, _ = R.make_course(teen, spots, conn, hours=6, w_content=0.1)
    na = [c["spot"]["name"] for c in a]
    nb = [c["spot"]["name"] for c in b]
    check(11, "가중치 0.9 vs 0.1일 때 코스가 달라짐",
          na != nb,
          f"취향90%: {', '.join(na)}\n         평점90%: {', '.join(nb)}")

    # 12. init_db.py 재실행 시 평점 보존
    #     (직접 실행하지 않고, 안전장치 코드가 들어 있는지 확인)
    src = open(os.path.join(BASE, "scripts", "init_db.py"), encoding="utf-8").read()
    check(12, "init_db.py가 --reset 없이는 기존 DB를 건드리지 않음",
          "--reset" in src and "os.path.exists(DB_PATH) and not reset" in src,
          "재실행 안전장치 코드 확인됨")

    conn.close()

    print()
    print("─" * 56)
    passed = sum(results)
    print(f"결과: {passed} / {len(results)} 통과")
    if passed == len(results):
        print("모든 항목을 통과했습니다. 수업 준비 완료.")
    else:
        print("실패한 항목을 고치고 다시 실행하세요.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
