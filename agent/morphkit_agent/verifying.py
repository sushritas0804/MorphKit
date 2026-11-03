from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT = 4000


def check_syntax(source: str, path: str) -> tuple[bool, str | None]:
    try:
        compile(source, path, "exec")
    except SyntaxError as exc:
        return False, f"{exc.__class__.__name__}: {exc}"
    return True, None


def run_tests(root: Path, timeout: int = 120) -> dict:
    has_tests = any(root.rglob("test_*.py")) or any(root.rglob("*_test.py"))
    if not has_tests:
        return {"ran": False, "passed": None, "exit_code": None, "output_tail": "no tests found"}

    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "ran": True,
            "passed": False,
            "exit_code": None,
            "output_tail": f"pytest timed out after {timeout}s",
        }

    output = (proc.stdout or "") + (proc.stderr or "")
    return {
        "ran": True,
        "passed": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output_tail": output[-MAX_OUTPUT:],
    }
