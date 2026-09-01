# -*- coding: utf-8 -*-
"""app.py — 아직은 글자 하나만 보여주는 서버입니다."""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "AI 관광 추천 서비스"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
