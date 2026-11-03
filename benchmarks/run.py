from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from morphkit_agent import editing, registry, verifying
from morphkit_agent.scanning import scan_project

SEGMENTS = ("request_id", "request_logging", "rate_limit")
PROJECTS = ROOT / "benchmarks" / "projects"


def run_one(name: str) -> tuple[int, str]:
    source_dir = PROJECTS / name
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / name
        shutil.copytree(source_dir, work)
        scan = scan_project(work)
        if not scan.apps:
            return 0, "no FastAPI app found"
        target = scan.apps[0]
        path = work / target.file
        source = path.read_text(encoding="utf-8")

        applied = 0
        for segment in SEGMENTS:
            manifest = registry.load_manifest(segment)
            builder = registry.load_builder(segment)
            params = {key: spec.get("default") for key, spec in manifest.params.items()}
            snippet = builder(params=params, slots={"app_var": target.app_var})
            try:
                result = editing.apply_snippet(
                    source, target.file, snippet, manifest, target.app_var
                )
            except editing.EditError as exc:
                return applied, f"{segment}: apply failed: {exc}"
            if not result.changed:
                return applied, f"{segment}: no change ({result.reason})"
            ok, error = verifying.check_syntax(result.new, target.file)
            if not ok:
                return applied, f"{segment}: syntax: {error}"
            source = result.new
            applied += 1

        path.write_text(source, encoding="utf-8")
        tests = verifying.run_tests(work)
        if not tests["ran"]:
            return applied, "no tests ran"
        if not tests["passed"]:
            return applied, "tests failed after all segments"
        return applied, "ok"


def main() -> int:
    projects = sorted(p.name for p in PROJECTS.iterdir() if p.is_dir())
    target_total = len(projects) * len(SEGMENTS)
    print(f"{'project':<22} {'applied':<9} note")
    total = 0
    for project in projects:
        applied, note = run_one(project)
        total += applied
        print(f"{project:<22} {applied}/{len(SEGMENTS):<7} {note}")
    print()
    print(f"{total}/{target_total} applies succeeded (target {target_total})")
    return 0 if total == target_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
