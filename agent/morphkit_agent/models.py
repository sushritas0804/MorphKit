from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AppTarget:
    file: str
    line: int
    app_var: str


@dataclass
class ProjectScan:
    root: str
    framework: str | None
    python_files: list[str]
    apps: list[AppTarget]
    existing_segments: dict[str, list[str]]
    has_tests: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class SegmentManifest:
    name: str
    version: str
    display_name: str
    summary: str
    kind: str
    stage: str
    params: dict[str, Any]
    adapt: dict[str, Any]
    tests: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "display_name": self.display_name,
            "summary": self.summary,
            "kind": self.kind,
            "stage": self.stage,
            "params": self.params,
            "adapt": self.adapt,
            "tests": self.tests,
        }


@dataclass
class Snippet:
    imports: list[str]
    defs: list[str]
    register: list[str]


@dataclass
class EditResult:
    file: str
    changed: bool
    reason: str
    old: str
    new: str
    diff: str
