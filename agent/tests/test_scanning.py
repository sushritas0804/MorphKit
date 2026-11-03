from __future__ import annotations

from pathlib import Path

from morphkit_agent.scanning import scan_project


def test_scan_finds_fastapi_app(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "import fastapi as fa\n\napplication = fa.FastAPI()\n", encoding="utf-8"
    )
    scan = scan_project(tmp_path)
    assert scan.framework == "fastapi"
    assert scan.apps[0].file == "main.py"
    assert scan.apps[0].app_var == "application"
    assert scan.has_tests is False


def test_scan_skips_virtualenv(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "main.py").write_text("app = FastAPI()\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\n\napp = FastAPI()\n", encoding="utf-8")
    scan = scan_project(tmp_path)
    assert scan.python_files == ["main.py"]


def test_scan_records_existing_segments(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\n\napp = FastAPI()  # morphkit:segment:request_id\n",
        encoding="utf-8",
    )
    scan = scan_project(tmp_path)
    assert scan.existing_segments == {"request_id": ["main.py"]}
