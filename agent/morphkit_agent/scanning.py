from __future__ import annotations

import os
import re
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .models import AppTarget, ProjectScan

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".tox",
}
MAX_FILES = 2000
MARKER_RE = re.compile(r"#\s*morphkit:segment:([a-zA-Z0-9_]+)")
DEP_FILES = ("pyproject.toml", "requirements.txt", "requirements-dev.txt", "Pipfile", "setup.py")


def _iter_python_files(root: Path, warnings: list[str]) -> list[str]:
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.endswith(".py"):
                found.append(Path(dirpath, name).relative_to(root).as_posix())
                if len(found) >= MAX_FILES:
                    warnings.append(f"stopped scanning at {MAX_FILES} Python files")
                    return found
    return found


def _detect_framework(root: Path) -> str | None:
    for name in DEP_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if "fastapi" in text:
            return "fastapi"
    return None


class _AppFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def _check(self, node: cst.CSTNode, value: cst.BaseExpression | None, targets: list) -> None:
        if value is None or not isinstance(value, cst.Call):
            return
        func = value.func
        name = ""
        if isinstance(func, cst.Name):
            name = func.value
        elif isinstance(func, cst.Attribute):
            name = func.attr.value
        if name != "FastAPI":
            return
        line = self.get_metadata(PositionProvider, node).start.line
        for target in targets:
            if isinstance(target, cst.Name):
                self.hits.append((line, target.value))

    def visit_Assign(self, node: cst.Assign) -> None:
        self._check(node, node.value, [t.target for t in node.targets])

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        self._check(node, node.value, [node.target])


def _find_apps(root: Path, files: list[str]) -> list[AppTarget]:
    apps: list[AppTarget] = []
    for rel in files:
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "FastAPI" not in text:
            continue
        try:
            module = cst.parse_module(text)
        except cst.ParserSyntaxError:
            continue
        finder = _AppFinder()
        MetadataWrapper(module).visit(finder)
        for line, var in finder.hits:
            apps.append(AppTarget(file=rel, line=line, app_var=var))
    return apps


def scan_project(root: Path) -> ProjectScan:
    root = root.resolve()
    warnings: list[str] = []
    files = _iter_python_files(root, warnings)
    framework = _detect_framework(root)
    apps = _find_apps(root, files)
    if framework is None and apps:
        framework = "fastapi"

    existing: dict[str, list[str]] = {}
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in MARKER_RE.finditer(text):
            existing.setdefault(match.group(1), []).append(rel)

    has_tests = any(
        Path(rel).name.startswith("test_") or Path(rel).name.endswith("_test.py") for rel in files
    )

    return ProjectScan(
        root=str(root),
        framework=framework,
        python_files=files,
        apps=apps,
        existing_segments=existing,
        has_tests=has_tests,
        warnings=warnings,
    )
