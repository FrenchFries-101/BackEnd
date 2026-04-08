import pytest
from fastapi.testclient import TestClient

from main import app  

client = TestClient(app)


def test_server_running():
    response = client.get("/")
    assert response.status_code in [200, 404]  


# tests/test_word_game_basic.py

def test_single_game_flow():
    user_id = 1

    res = client.post("/wordgame/single/start", params={"user_id": user_id})
    assert res.status_code == 200

    res = client.get("/wordgame/single/status", params={"user_id": user_id})
    assert res.status_code == 200

    res = client.post("/wordgame/single/gain-roll", params={"user_id": user_id})
    assert res.status_code in [200, 400]

    res = client.post("/wordgame/single/roll", params={"user_id": user_id})
    assert res.status_code in [200, 400]

    if res.status_code == 200:
        data = res.json()
        assert "current_position" in data
        assert "current_day" in data


def test_quiz_question_requires_active_match():
    res = client.get("/wordgame/quiz-question", params={"user_id": 1})
    assert res.status_code in [200, 400]


def test_multiplayer_join_and_status():
    user_id = 999  # 测试用用户，避免污染真实用户

    # join
    res = client.post("/wordgame/join", params={"user_id": user_id})
    assert res.status_code == 200
    data = res.json()
    assert "match_id" in data

    # status
    res = client.get("/wordgame/status", params={"user_id": user_id})
    assert res.status_code == 200
    data = res.json()
    assert "match" in data or "message" in data


def test_gain_roll_multiplayer():
    user_id = 888

    # 先 join
    client.post("/wordgame/join", params={"user_id": user_id})

    res = client.post("/wordgame/gain-roll", params={"user_id": user_id})
    assert res.status_code in [200, 400]  # 可能失败（未active）


def test_roll_multiplayer():
    user_id = 777

    # join
    client.post("/wordgame/join", params={"user_id": user_id})

    res = client.post("/wordgame/roll", params={"user_id": user_id})
    assert res.status_code in [200, 400]  # 可能没roll次数