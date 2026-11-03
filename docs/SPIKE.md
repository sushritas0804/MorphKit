# Adaptation spike: status

Goal: prove that dropping a segment into a real FastAPI project produces a
correct, verified edit. Deterministic only. No LLM. No gateway.

Exit gate: 3 segments, 5 fixture projects, 15/15 applies pass, one-command start
on Windows, macOS, and Linux.

## Done

- [x] Local agent: `morphkit open <path>` on loopback with a token in the URL
- [x] Scanner: framework, app objects, existing segment markers, test presence
- [x] Manifest loader and `S1` segment contract (`build(params, slots) -> Snippet`)
- [x] LibCST editor: import insertion, definition insertion, registration after
      `x = FastAPI(...)`, including app factories
- [x] Idempotent apply via marker comment
- [x] Unified diff preview in the UI
- [x] Apply endpoint with syntax check and `pytest` run
- [x] UI: palette, drag target, generated params form, diff, verification panel
- [x] Segments: `request_id`, `request_logging`, `rate_limit`
- [x] Template tests prove segment code works at runtime, not just that it parses
- [x] Target picker when a project has several app objects
- [x] 5 benchmark fixtures, 15/15 applies, fixture tests still pass
- [x] Agent tests: 17 passing; ruff and mypy clean

## Next

- [ ] React Flow canvas, replacing the single drop target
- [ ] Monaco diff view, replacing the plain diff
- [ ] Warn when the project root is not a git repository
- [ ] Run on macOS and Linux

## Commands

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\agent[dev]"
cd ui; npm install; npm run build; cd ..
.\.venv\Scripts\morphkit.exe open .\benchmarks\projects\basic
```

Checks:

```powershell
.\.venv\Scripts\python.exe -m pytest agent -q
.\.venv\Scripts\python.exe benchmarks\run.py
.\.venv\Scripts\ruff.exe check agent benchmarks
.\.venv\Scripts\mypy.exe agent\morphkit_agent --ignore-missing-imports
```
