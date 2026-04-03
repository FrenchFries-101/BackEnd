import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_openapi_exists():
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_wordgame_routes_exist():
    response = client.get("/openapi.json")
    data = response.json()
    paths = data.get("paths", {})

    assert "/wordgame/join" in paths
    assert "/wordgame/status" in paths
    assert "/wordgame/quiz-question" in paths
    assert "/wordgame/gain-roll" in paths
    assert "/wordgame/roll" in paths