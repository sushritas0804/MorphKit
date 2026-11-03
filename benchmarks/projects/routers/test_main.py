from fastapi.testclient import TestClient
from main import app


def test_items() -> None:
    response = TestClient(app).get("/items/")
    assert response.status_code == 200
    assert response.json() == []
