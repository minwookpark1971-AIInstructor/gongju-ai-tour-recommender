# -*- coding: utf-8 -*-
"""
check_prompts.py — 프롬프트 대본 정합성 검사 (교사 전용)

프롬프트_대본.md 는 학생이 그대로 따라 하는 문서다.
여기에 적힌 파일 이름·함수 이름·규칙·숫자가 실제 완성본과 어긋나면
학생은 대본대로 했는데 선생님 화면과 다른 결과를 보게 된다.

이 스크립트는 대본이 주장하는 내용이 실제 코드와 맞는지 확인한다.

한계: Claude Code가 그 프롬프트로 '어떤 코드를 만들어 낼지'는 검사할 수 없다.
     검사하는 것은 '대본과 완성본이 서로 모순되지 않는가' 뿐이다.
     실제 완주 확인은 사람이 한 번 직접 해 봐야 한다.

실행: python scripts/check_prompts.py
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import recommender as R      # noqa: E402

SCRIPT = os.path.join(BASE, "프롬프트_대본.md")

results = []


def check(title, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {title}")
    if detail:
        print(f"        {detail}")


def read(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8") as f:
        return f.read()


def main():
    doc = read("프롬프트_대본.md")

    # 1. 대본이 언급한 파일이 실제로 완성본에 있는가
    mentioned = set(re.findall(r"(?:scripts/)?[a-z_]+\.(?:py|csv|css)", doc))
    mentioned = {m for m in mentioned if not m.startswith("_")}
    missing = []
    for name in sorted(mentioned):
        cands = [name, f"scripts/{os.path.basename(name)}",
                 f"data/{os.path.basename(name)}", f"static/{os.path.basename(name)}"]
        if not any(os.path.exists(os.path.join(BASE, c)) for c in cands):
            missing.append(name)
    check("대본이 언급한 파일이 모두 완성본에 존재",
          not missing,
          f"검사 {len(mentioned)}개" + (f" / 없는 파일 {missing}" if missing else " / 전부 존재"))

    # 2. 함수 시그니처가 대본과 일치하는가
    src = read("recommender.py")
    sig_ok = {
        "content_score(user_pref, spot_themes": "def content_score(user_pref, spot_themes" in src,
        "collab_score(user, spot_id, conn)": "def collab_score(user, spot_id, conn)" in src,
        "make_course": "def make_course(" in src,
        "final_score(content, collab, w_content=0.6)":
            "def final_score(content, collab, w_content=0.6)" in src,
    }
    for name in sig_ok:
        if name in doc or name.split("(")[0] in doc:
            pass
    check("대본에 적힌 함수 시그니처가 완성본과 일치",
          all(sig_ok.values()),
          ", ".join(f"{k.split('(')[0]}={'OK' if v else 'X'}" for k, v in sig_ok.items()))

    # 3. 대본의 숫자가 실제 동작과 일치하는가
    check("3/6/9시간 → 3/4/5곳 (대본 Step6)",
          R.TARGET_COUNT == {3: 3, 6: 4, 9: 5},
          f"완성본 TARGET_COUNT = {R.TARGET_COUNT}")

    check("이동시간 20분 (대본 Step6 7번 항목)",
          R.TRAVEL_MIN == 20 and "20분 × (곳수-1)" in doc,
          f"완성본 TRAVEL_MIN = {R.TRAVEL_MIN}분")

    check("같은 테마 최대 2곳 (대본 Step6 5번 항목)",
          R.MAX_SAME_THEME == 2 and "최대 2곳" in doc,
          f"완성본 MAX_SAME_THEME = {R.MAX_SAME_THEME}")

    check("테마 6개와 순서가 대본과 일치",
          R.THEMES == ["역사", "자연", "체험", "맛집", "사진스팟", "휴식"]
          and "역사/자연/체험/맛집/사진스팟/휴식" in doc,
          " · ".join(R.THEMES))

    # 4. 손계산 예제 0.6736 이 실제 계산과 일치
    pref = {"역사": 5, "자연": 3, "체험": 0, "맛집": 4, "사진스팟": 2, "휴식": 0}
    got = R.content_score(pref, "역사,사진스팟")
    check("대본 Step4 손계산 예제 0.6736 이 실제 계산과 일치",
          "0.6736" in doc and abs(got - 0.6736) < 1e-4,
          f"실제 계산 {got:.4f}")

    # 5. 정제 결과 32 → 30 이 대본과 일치
    sys.path.insert(0, os.path.join(BASE, "scripts"))
    from preprocess import clean_spots, read_csv     # noqa: E402
    raw = read_csv(os.path.join(BASE, "data", "spots_raw.csv"))
    clean = clean_spots(verbose=False)
    check("대본 Step2 '32행 → 30행' 이 실제와 일치",
          "**32행**" in doc and "**30행**" in doc
          and len(raw) == 32 and len(clean) == 30,
          f"실제 {len(raw)}행 → {len(clean)}행")

    # 6. 대본이 강조한 안전장치가 실제로 구현돼 있는가
    init_src = read("scripts/init_db.py")
    check("대본 Step2 '--reset 없이는 DB를 안 건드림' 이 실제로 구현됨",
          "--reset" in doc and "os.path.exists(DB_PATH) and not reset" in init_src)

    check("대본 Step1 utf-8-sig 안내가 실제 코드와 일치",
          "utf-8-sig" in doc and "utf-8-sig" in read("scripts/preprocess.py"))

    check("대본 Step7 'JavaScript 쓰지 마' 가 실제로 지켜짐",
          not any("<script" in read(f"templates/{t}")
                  for t in os.listdir(os.path.join(BASE, "templates"))),
          "templates 안에 <script> 태그 0개")

    # 7. 대본이 경고한 build_reason 함정이 실제로 처리돼 있는가
    check("대본 Step7 '첫 번째 테마를 쓰면 안 된다' 경고가 실제 구현과 일치",
          "첫 번째 테마를 쓰면 안 돼" in doc
          and "max(owned, key=lambda t: user_pref.get(t, 0))" in src)

    print()
    print("─" * 56)
    passed = sum(results)
    print(f"결과: {passed} / {len(results)} 통과")
    if passed != len(results):
        print("대본과 완성본이 어긋납니다. 둘 중 하나를 고치세요.")
        return 1
    print("대본과 완성본이 일치합니다.")
    print()
    print("※ 남은 확인은 사람이 해야 합니다 —")
    print("  빈 폴더에서 대본을 순서대로 실제로 넣어 완주해 볼 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
