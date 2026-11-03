from __future__ import annotations

from pathlib import Path

import pytest
from morphkit_agent.cli import prepare_demo


def test_prepare_demo_copies_fixture(tmp_path: Path) -> None:
    dest = prepare_demo(tmp_path, "basic")
    assert dest == tmp_path / ".demo" / "basic"
    assert (dest / "main.py").is_file()
    assert (dest / "test_main.py").is_file()


def test_prepare_demo_recreates_cleanly(tmp_path: Path) -> None:
    dest = prepare_demo(tmp_path, "basic")
    (dest / "stale.py").write_text("x = 1\n", encoding="utf-8")
    prepare_demo(tmp_path, "basic")
    assert not (dest / "stale.py").exists()
    assert (dest / "main.py").is_file()


def test_prepare_demo_rejects_unknown_project(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="unknown demo project"):
        prepare_demo(tmp_path, "does-not-exist")
