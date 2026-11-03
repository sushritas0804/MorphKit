from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from morphkit_agent.server import create_app

TOKEN = "test-token"


def _client(tmp_path: Path) -> TestClient:
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()\n", encoding="utf-8"
    )
    return TestClient(create_app(tmp_path, TOKEN))


def test_api_requires_token(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert client.get("/api/project").status_code == 401


def test_scan_and_preview(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = {"x-morphkit-token": TOKEN}

    scan = client.get("/api/project", headers=headers).json()
    assert scan["apps"][0]["app_var"] == "app"

    response = client.post(
        "/api/preview",
        headers=headers,
        json={
            "segment": "request_id",
            "params": {"header_name": "X-Request-ID"},
            "app_file": "main.py",
            "app_var": "app",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["changed"] is True
    assert "add_middleware" in body["diff"]


def test_apply_writes_file(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = {"x-morphkit-token": TOKEN}
    response = client.post(
        "/api/apply",
        headers=headers,
        json={
            "segment": "request_id",
            "params": {},
            "app_file": "main.py",
            "app_var": "app",
        },
    )
    assert response.status_code == 200
    assert "RequestIDMiddleware" in (tmp_path / "main.py").read_text(encoding="utf-8")


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = {"x-morphkit-token": TOKEN}
    response = client.post(
        "/api/preview",
        headers=headers,
        json={
            "segment": "request_id",
            "params": {},
            "app_file": "../outside.py",
            "app_var": "app",
        },
    )
    assert response.status_code == 400
