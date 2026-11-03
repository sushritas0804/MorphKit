from __future__ import annotations

import logging
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from morphkit_agent import editing, registry


def _build_app(segment: str, params: dict) -> FastAPI:
    builder = registry.load_builder(segment)
    snippet = builder(params=params, slots={"app_var": "app"})
    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"ok": True}

    namespace: dict = {"app": app}
    for code in snippet.imports:
        exec(code, namespace)  # noqa: S102
    for code in snippet.defs:
        exec(code, namespace)  # noqa: S102
    for code in snippet.register:
        exec(code, namespace)  # noqa: S102
    return app


def test_request_id_sets_header() -> None:
    app = _build_app("request_id", {"header_name": "X-Trace"})
    response = TestClient(app).get("/")
    value = response.headers["x-trace"]
    uuid.UUID(value)


def test_request_logging_writes_one_line(caplog: pytest.LogCaptureFixture) -> None:
    app = _build_app("request_logging", {"logger_name": "morphkit.test"})
    with caplog.at_level(logging.INFO, logger="morphkit.test"):
        response = TestClient(app).get("/")
    assert response.status_code == 200
    assert any(record.name == "morphkit.test" for record in caplog.records)


def test_rate_limit_returns_429_after_limit() -> None:
    app = _build_app("rate_limit", {"requests_per_minute": 2})
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 200
    blocked = client.get("/")
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "60"


def test_all_segments_apply_together_and_compile() -> None:
    source = "from fastapi import FastAPI\n\napp = FastAPI()\n"
    path = "main.py"
    for name in ("request_id", "request_logging", "rate_limit"):
        manifest = registry.load_manifest(name)
        builder = registry.load_builder(name)
        params = {key: spec.get("default") for key, spec in manifest.params.items()}
        snippet = builder(params=params, slots={"app_var": "app"})
        result = editing.apply_snippet(source, path, snippet, manifest, "app")
        assert result.changed, name
        source = result.new
    compile(source, path, "exec")
    for name in ("request_id", "request_logging", "rate_limit"):
        assert f"# morphkit:segment:{name}" in source
