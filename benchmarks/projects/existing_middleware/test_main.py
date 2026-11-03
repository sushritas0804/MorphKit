from fastapi.testclient import TestClient
from main import app


def test_cors_still_works() -> None:
    response = TestClient(app).get("/", headers={"Origin": "http://example.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
