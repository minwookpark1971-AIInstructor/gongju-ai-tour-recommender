# -*- coding: utf-8 -*-
"""
preprocess.py — 1단계: 관광지 원본 데이터 정제

data/spots_raw.csv 는 일부러 지저분하게 만들어져 있다.
  (1) 같은 관광지가 두 번 들어간 행이 있다
  (2) 소요시간이 비어 있는 행이 있다
  (3) 테마 이름이 제각각이다 ('역사유적', '먹거리', '포토존' ...)

이 파일은 위 3가지를 고쳐서 깨끗한 데이터로 만든다.

실행: python scripts/preprocess.py
"""

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

# 테마 6개 — 이 6개 외의 값은 존재하면 안 된다
THEMES = ["역사", "자연", "체험", "맛집", "사진스팟", "휴식"]

# 표기가 흔들린 테마 이름을 표준 이름으로 바꾸는 표
THEME_ALIAS = {
    "역사유적": "역사",
    "자연경관": "자연",
    "먹거리": "맛집",
    "포토존": "사진스팟",
    "힐링": "휴식",
    "체험학습": "체험",
}

# 소요시간이 비어 있을 때 채워 넣을 기본값(분)
DEFAULT_DURATION = 60


def read_csv(path):
    """CSV를 읽어서 딕셔너리 목록으로 돌려준다.

    pandas가 설치돼 있으면 pandas로, 없으면 파이썬 기본 csv 모듈로 읽는다.
    (학교 컴퓨터에 pandas 설치가 막혀도 수업이 멈추지 않게 하기 위함)

    encoding='utf-8-sig' 가 중요하다.
    엑셀에서 저장한 한글 CSV는 파일 맨 앞에 눈에 보이지 않는 표시가 붙는데,
    'utf-8' 로만 읽으면 첫 번째 컬럼 이름이 깨진다.
    """
    try:
        import pandas as pd
        df = pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)
        return df.to_dict("records")
    except ImportError:
        print("  (pandas가 없어서 기본 csv 모듈로 읽습니다)")
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))


def normalize_themes(text):
    """'역사유적,자연경관' → '역사,자연' 으로 표기를 통일한다."""
    result = []
    for raw in str(text).split(","):
        name = raw.strip()
        if not name:
            continue
        # 별칭표에 있으면 표준 이름으로 바꾸고, 없으면 그대로 둔다
        name = THEME_ALIAS.get(name, name)
        if name not in THEMES:
            raise ValueError(f"알 수 없는 테마입니다: '{name}' — THEME_ALIAS에 추가하세요")
        if name not in result:      # 같은 테마가 두 번 들어가지 않게
            result.append(name)
    return ",".join(result)


def clean_spots(verbose=True):
    """관광지 원본을 정제해서 깨끗한 목록으로 돌려준다."""
    rows = read_csv(os.path.join(DATA, "spots_raw.csv"))
    before = len(rows)

    cleaned = []
    seen_names = set()
    dup_count = 0
    filled_count = 0
    theme_fixed = 0

    for row in rows:
        # (1) 관광지명 앞뒤 공백을 없애고, 이미 나온 이름이면 버린다
        name = str(row["name"]).strip()
        if name in seen_names:
            dup_count += 1
            if verbose:
                print(f"  [중복 제거] {name}")
            continue
        seen_names.add(name)

        # (2) 소요시간이 비어 있으면 기본값으로 채운다
        duration = str(row["duration_min"]).strip()
        if duration == "":
            duration = DEFAULT_DURATION
            filled_count += 1
            if verbose:
                print(f"  [결측 보정] {name} 의 소요시간을 {DEFAULT_DURATION}분으로 채움")
        duration = int(duration)

        # (3) 테마 표기를 통일한다
        original = str(row["themes"]).strip()
        themes = normalize_themes(original)
        if themes != original:
            theme_fixed += 1
            if verbose:
                print(f"  [표기 통일] {name}: '{original}' → '{themes}'")

        cleaned.append({
            "name": name,
            "region": str(row["region"]).strip(),
            "themes": themes,
            "duration_min": duration,
            "cost": int(row["cost"]),
            "indoor": int(row["indoor"]),
            "description": str(row["description"]).strip(),
            "image": str(row["image"]).strip(),
        })

    if verbose:
        print()
        print("─" * 50)
        print(f"정제 전 : {before}행")
        print(f"정제 후 : {len(cleaned)}행")
        print(f"  중복 제거      : {dup_count}건")
        print(f"  소요시간 보정  : {filled_count}건")
        print(f"  테마 표기 통일 : {theme_fixed}건")
        print("─" * 50)

    return cleaned


def main():
    print("관광지 데이터를 정제합니다...")
    print()
    spots = clean_spots()

    # 정제 결과를 파일로도 남겨둔다 (눈으로 확인할 수 있게)
    out = os.path.join(DATA, "spots_clean.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(spots[0].keys()))
        w.writeheader()
        w.writerows(spots)
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
