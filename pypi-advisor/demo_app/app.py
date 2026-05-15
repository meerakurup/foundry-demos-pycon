"""
app.py — A simple web scraper the conference audience "inherited".
The agent will audit its requirements.txt for vulnerabilities and staleness.
"""

import simplejson as json

import flask
import jwt
import numpy as np
import requests
from bs4 import BeautifulSoup

app = flask.Flask(__name__)
SECRET_KEY = "super-secret"  # demo only


def scrape_title(url: str) -> dict:
    response = requests.get(url, timeout=5)
    soup = BeautifulSoup(response.text, "html.parser")
    return {"url": url, "title": soup.title.string if soup.title else None}


def make_token(user_id: str) -> str:
    # pyjwt 1.7.1 — vulnerable!
    return jwt.encode({"sub": user_id}, SECRET_KEY, algorithm="HS256")


def moving_average(data: list[float], window: int = 3) -> np.ndarray:
    return np.convolve(data, np.ones(window) / window, mode="valid")


@app.route("/scrape")
def scrape():
    url = flask.request.args.get("url", "https://example.com")
    result = scrape_title(url)
    return json.dumps(result)


@app.route("/token")
def token():
    user = flask.request.args.get("user", "demo-user")
    return json.dumps({"token": make_token(user)})


if __name__ == "__main__":
    app.run(debug=True)
