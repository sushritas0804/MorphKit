from fastapi.testclient import TestClient
from main import app


def test_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
