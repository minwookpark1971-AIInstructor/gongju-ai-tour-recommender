# 오프라인 설치 키트

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
