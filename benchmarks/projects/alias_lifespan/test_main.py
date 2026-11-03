from fastapi.testclient import TestClient
from main import application


def test_root_with_lifespan() -> None:
    with TestClient(application) as client:
        response = client.get("/")
    assert response.status_code == 200
