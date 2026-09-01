# -*- coding: utf-8 -*-
"""
make_offline_kit.py — 오프라인 설치 키트 생성기 (교사 전용)

학교망에서 pip 설치가 막히는 경우를 대비해,
미리 받아 둔 whl 파일을 USB로 나눠 주기 위한 폴더를 만든다.

기본은 Flask만 받는다 (약 0.6MB).
  이 프로젝트는 pandas를 CSV 읽기에만 쓰는데, preprocess.py가
  pandas가 없으면 파이썬 기본 csv 모듈로 넘어가도록 만들어져 있다.
  pandas를 넣으면 numpy까지 딸려 와서 23MB가 된다. USB 배포에 부담이다.

pandas까지 넣고 싶으면:
    python scripts/make_offline_kit.py --with-pandas

실행: python scripts/make_offline_kit.py
"""

import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(BASE, "dist", "offline_kit")
WHEELS = os.path.join(KIT, "wheels")

INSTALL_BAT = """@echo off
chcp 65001 > nul
echo ============================================
echo  AI 관광 추천 서비스 - 오프라인 설치
echo ============================================
echo.
python -m pip install --no-index --find-links=wheels flask
if errorlevel 1 goto fail
echo.
echo 설치가 끝났습니다.
echo 이제 프로젝트 폴더에서 아래 두 줄을 실행하세요.
echo.
echo   python scripts/init_db.py
echo   python app.py
echo.
pause
exit /b 0

:fail
echo.
echo 설치에 실패했습니다. 선생님께 알려 주세요.
pause
exit /b 1
"""

README = """# 오프라인 설치 키트

학교 컴퓨터에서 `pip install` 이 막혀 있을 때 쓴다.
인터넷 연결 없이 설치할 수 있다.

## 설치 방법 (윈도우)

1. 이 폴더를 USB에서 바탕화면으로 복사한다
2. `install.bat` 을 더블클릭한다

## 직접 명령으로 설치하려면

```
python -m pip install --no-index --find-links=wheels flask
```

## pandas 는 왜 없나요?

이 프로젝트는 pandas를 CSV 읽기에만 쓴다.
`scripts/preprocess.py` 는 pandas가 없으면 파이썬에 기본으로 들어 있는
`csv` 모듈로 자동으로 넘어가도록 만들어져 있다.

pandas를 넣으면 numpy까지 함께 받아야 해서 용량이 23MB로 늘어난다.
수업에 꼭 필요한 것은 아니므로 기본 키트에서는 뺐다.

pandas가 필요하면 선생님이 아래 명령으로 키트를 다시 만들면 된다.

```
python scripts/make_offline_kit.py --with-pandas
```
"""


def folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


def main():
    with_pandas = "--with-pandas" in sys.argv
    packages = ["flask"] + (["pandas"] if with_pandas else [])

    if os.path.exists(KIT):
        shutil.rmtree(KIT)
    os.makedirs(WHEELS)

    print(f"내려받을 패키지: {', '.join(packages)}")
    print("(인터넷 연결이 필요합니다)")
    print()

    result = subprocess.run(
        [sys.executable, "-m", "pip", "download", *packages, "-d", WHEELS],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print("내려받기에 실패했습니다.")
        print(result.stderr.strip()[-500:])
        return 1

    with open(os.path.join(KIT, "install.bat"), "w", encoding="utf-8") as f:
        f.write(INSTALL_BAT)
    with open(os.path.join(KIT, "README.md"), "w", encoding="utf-8") as f:
        f.write(README)

    files = sorted(os.listdir(WHEELS))
    print(f"whl 파일 {len(files)}개")
    for name in files:
        size = os.path.getsize(os.path.join(WHEELS, name)) / 1024
        print(f"  {size:>8.0f} KB  {name}")
    print()
    print(f"키트 전체 크기: {folder_size(KIT) / 1024 / 1024:.2f} MB")
    print(f"저장 위치: {KIT}")
    if not with_pandas:
        print()
        print("pandas 없이 만들었습니다. 프로젝트는 pandas 없이도 전부 동작합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
