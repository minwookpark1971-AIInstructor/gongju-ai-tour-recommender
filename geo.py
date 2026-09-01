# -*- coding: utf-8 -*-
"""
geo.py — 확장과제용: 관광지 좌표로 거리와 지도를 다룬다

기본 과제에서는 쓰지 않는다. 심화 과제 두 가지에 쓰인다.
  · 확장 5) 이동시간을 20분 고정이 아니라 실제 거리로 계산
  · 확장 3) 추천 코스를 지도 위에 순번으로 표시

좌표는 네이버 지역검색 결과의 값을 그대로 옮긴 것이다 (data/spots_geo.csv).
"""

import math

# 시내 이동 평균 속도 (km/h). 공주 시내와 외곽을 섞어 잡은 값.
AVG_SPEED_KMH = 40

# 아무리 가까워도 주차하고 걸어 들어가는 시간이 필요하다
MIN_TRAVEL_MIN = 10


def haversine_km(lat1, lon1, lat2, lon2):
    """지구가 둥근 것을 감안해 두 지점 사이 직선거리를 km로 구한다.

    (하버사인 공식. 고등학교 수준을 넘으므로 '이런 공식이 있다' 정도로 넘어가고,
     결과가 상식에 맞는지만 확인하면 된다.)
    """
    R = 6371.0                      # 지구 반지름 km
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def travel_minutes(a, b):
    """관광지 a에서 b까지 걸리는 시간(분).

    좌표가 없으면 None을 돌려준다 → 부르는 쪽에서 기본값(20분)을 쓰면 된다.
    실제 도로는 직선이 아니므로 직선거리에 1.3배를 곱한다.
    """
    if not all([a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")]):
        return None
    km = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) * 1.3
    minutes = km / AVG_SPEED_KMH * 60
    # 5분 단위로 반올림하면 읽기 편하다
    return max(MIN_TRAVEL_MIN, int(round(minutes / 5) * 5))


def course_travel_minutes(course_spots, default=20):
    """코스를 순서대로 돌 때 필요한 총 이동시간(분)."""
    total = 0
    for a, b in zip(course_spots, course_spots[1:]):
        m = travel_minutes(a, b)
        total += default if m is None else m
    return total


# ═══════════════════════════════════════════════════════════
# 지도 그리기 — 지도 API 없이 SVG 점으로 표시한다
# ═══════════════════════════════════════════════════════════

def to_svg_points(all_spots, course_spots, width=480, height=420, pad=34):
    """좌표를 그림 위의 위치(x, y)로 바꾼다.

    지도 서비스를 쓰지 않고, 관광지들의 경도·위도 범위를 그림 크기에 맞춰
    늘리거나 줄여서 점을 찍는다. 진짜 지도는 아니지만
    '어디가 서로 가까운지'는 그대로 보인다.
    """
    pts = [s for s in all_spots if s.get("lat") and s.get("lon")]
    course = [s for s in course_spots if s.get("lat") and s.get("lon")]
    if len(pts) < 2 or not course:
        return [], []

    # 그림의 범위는 '코스에 담긴 곳'을 기준으로 잡는다.
    #
    # 관광지 30곳 전체(약 30km)에 맞춰 축척을 잡으면,
    # 코스가 전부 원도심(반경 1.5km)일 때 점 네 개가 한 덩어리로 뭉쳐
    # 무엇이 무엇인지 알아볼 수 없게 된다. 그래서 코스에 맞춰 확대한다.
    lat_mid = sum(s["lat"] for s in course) / len(course)
    lon_scale = math.cos(math.radians(lat_mid))    # 경도 1도는 위도 1도보다 짧다

    lons = [s["lon"] for s in course]
    lats = [s["lat"] for s in course]
    cx = (min(lons) + max(lons)) / 2
    cy = (min(lats) + max(lats)) / 2

    # 코스가 화면에 꽉 차지 않도록 범위를 넉넉히 넓힌다
    span_x = (max(lons) - min(lons)) * lon_scale * 1.6
    span_y = (max(lats) - min(lats)) * 1.6

    # 너무 좁게 확대하면 이름표가 화면 밖으로 나가므로 최소 범위를 둔다
    # (위도 0.02도 ≈ 2.2km)
    MIN_SPAN = 0.02
    span_x = max(span_x, MIN_SPAN * lon_scale)
    span_y = max(span_y, MIN_SPAN)

    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)

    def place(s):
        x = width / 2 + (s["lon"] - cx) * lon_scale * scale
        # 위도는 위로 갈수록 커지는데 화면은 아래로 갈수록 커지므로 뒤집는다
        y = height / 2 - (s["lat"] - cy) * scale
        return round(x, 1), round(y, 1)

    course_names = {s["name"] for s in course}
    background = []
    for s in pts:
        if s["name"] in course_names:
            continue
        x, y = place(s)
        # 확대한 범위 밖으로 벗어난 관광지는 그리지 않는다
        if 0 <= x <= width and 0 <= y <= height:
            background.append(dict(name=s["name"], x=x, y=y))

    route = []
    for order, s in enumerate(course, start=1):
        x, y = place(s)
        route.append(dict(order=order, name=s["name"], x=x, y=y))

    separate(route, min_dist=34, width=width, height=height, pad=pad)
    return background, route


def separate(points, min_dist, width, height, pad, rounds=60):
    """너무 가까이 붙은 번호 동그라미를 조금씩 밀어서 떨어뜨린다.

    원도심 관광지들은 서로 1km 안쪽이라 그대로 그리면 동그라미가 겹쳐
    몇 번인지 읽을 수 없다. 위치를 살짝 옮기더라도 번호가 보이는 편이 낫다.
    (그래서 이 그림은 '정확한 지도'가 아니라 '위치 관계 그림'이다)
    """
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(points):
            for b in points[i + 1:]:
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                dist = math.hypot(dx, dy)
                if dist >= min_dist:
                    continue
                if dist < 1e-6:              # 완전히 같은 자리면 옆으로 뗀다
                    dx, dy, dist = 1.0, 0.0, 1.0
                push = (min_dist - dist) / 2
                ux, uy = dx / dist, dy / dist
                a["x"] -= ux * push
                a["y"] -= uy * push
                b["x"] += ux * push
                b["y"] += uy * push
                moved = True
        # 그림 밖으로 밀려나지 않게 가둔다
        for p in points:
            p["x"] = min(max(p["x"], pad), width - pad)
            p["y"] = min(max(p["y"], pad), height - pad)
        if not moved:
            break

    for p in points:
        p["x"] = round(p["x"], 1)
        p["y"] = round(p["y"], 1)
