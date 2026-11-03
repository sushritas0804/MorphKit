from __future__ import annotations

import pytest
from morphkit_agent import editing
from morphkit_agent import registry as segments

BASIC = """from fastapi import FastAPI

app = FastAPI()
"""

FACTORY = """from fastapi import FastAPI


def create_app():
    app = FastAPI()

    @app.get("/")
    def home():
        return {"ok": True}

    return app
"""

ALIAS = """import fastapi as fa

application = fa.FastAPI()
"""


def _apply(source: str, app_var: str = "app") -> editing.EditResult:
    manifest = segments.load_manifest("request_id")
    builder = segments.load_builder("request_id")
    snippet = builder(params={"header_name": "X-Request-ID"}, slots={"app_var": app_var})
    return editing.apply_snippet(source, "main.py", snippet, manifest, app_var)


def test_basic_inserts_imports_class_and_registration() -> None:
    result = _apply(BASIC)
    assert result.changed
    assert "import uuid" in result.new
    assert "class RequestIDMiddleware(BaseHTTPMiddleware):" in result.new
    assert "app.add_middleware(RequestIDMiddleware" in result.new
    assert "# morphkit:segment:request_id" in result.new
    compile(result.new, "main.py", "exec")


def test_registration_lands_after_app_creation() -> None:
    result = _apply(FACTORY)
    assert result.changed
    lines = result.new.splitlines()
    app_line = next(i for i, line in enumerate(lines) if line.strip() == "app = FastAPI()")
    reg_line = next(i for i, line in enumerate(lines) if "add_middleware" in line)
    assert reg_line > app_line
    assert lines[reg_line].startswith("    ")
    compile(result.new, "main.py", "exec")


def test_attribute_import_is_supported() -> None:
    result = _apply(ALIAS, app_var="application")
    assert result.changed
    assert "application.add_middleware(RequestIDMiddleware" in result.new
    compile(result.new, "main.py", "exec")


def test_second_apply_is_a_noop() -> None:
    first = _apply(BASIC)
    second = _apply(first.new)
    assert not second.changed
    assert second.reason == "already applied"


def test_missing_app_raises_clear_error() -> None:
    with pytest.raises(editing.EditError, match="could not find"):
        _apply("print('hello')\n")


def test_header_name_param_is_used() -> None:
    manifest = segments.load_manifest("request_id")
    builder = segments.load_builder("request_id")
    snippet = builder(params={"header_name": "X-Trace"}, slots={"app_var": "app"})
    result = editing.apply_snippet(BASIC, "main.py", snippet, manifest, "app")
    assert 'header_name="X-Trace"' in result.new
