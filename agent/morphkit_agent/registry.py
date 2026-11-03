from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from pathlib import Path

import yaml

from .models import SegmentManifest, Snippet

SEGMENTS_DIR = Path(__file__).parent / "segments"
NAME_RE = re.compile(r"^[a-z0-9_]+$")


class SegmentError(Exception):
    pass


def _check_name(name: str) -> str:
    if not NAME_RE.match(name):
        raise SegmentError(f"invalid segment name: {name!r}")
    return name


def available_names() -> list[str]:
    if not SEGMENTS_DIR.is_dir():
        return []
    return sorted(
        p.name for p in SEGMENTS_DIR.iterdir() if p.is_dir() and (p / "manifest.yaml").is_file()
    )


def load_manifest(name: str) -> SegmentManifest:
    _check_name(name)
    path = SEGMENTS_DIR / name / "manifest.yaml"
    if not path.is_file():
        raise SegmentError(f"unknown segment: {name}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return SegmentManifest(
        name=data.get("name", name),
        version=str(data.get("version", "0.0.0")),
        display_name=data.get("display_name", name),
        summary=data.get("summary", ""),
        kind=data.get("kind", "middleware"),
        stage=data.get("stage", "pre"),
        params=data.get("params", {}) or {},
        adapt=data.get("adapt", {}) or {},
        tests=data.get("tests", []) or [],
    )


def load_all() -> list[SegmentManifest]:
    return [load_manifest(name) for name in available_names()]


def load_builder(name: str) -> Callable[..., Snippet]:
    _check_name(name)
    try:
        module = importlib.import_module(f"morphkit_agent.segments.{name}.apply")
    except ImportError as exc:
        raise SegmentError(f"segment {name} has no apply module") from exc
    return module.build
