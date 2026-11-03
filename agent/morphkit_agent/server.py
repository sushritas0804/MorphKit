from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import editing, registry, verifying
from .models import SegmentManifest
from .scanning import scan_project

UI_DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"
FALLBACK_HTML = """<!doctype html><html><body style="font-family:system-ui;padding:2rem">
<h1>Morphkit UI not built</h1>
<p>Run <code>npm install &amp;&amp; npm run build</code> in <code>ui/</code>, then reload.</p>
</body></html>"""


class PreviewRequest(BaseModel):
    segment: str
    params: dict = Field(default_factory=dict)
    app_file: str
    app_var: str


class ApplyRequest(PreviewRequest):
    pass


def _resolve_target(root: Path, app_file: str, app_var: str):
    scan = scan_project(root)
    for app in scan.apps:
        if app.file == app_file and app.app_var == app_var:
            return app
    raise HTTPException(status_code=400, detail="target FastAPI app not found in project")


def _preview(root: Path, req: PreviewRequest) -> editing.EditResult:
    target = _resolve_target(root, req.app_file, req.app_var)
    try:
        manifest: SegmentManifest = registry.load_manifest(req.segment)
    except registry.SegmentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    builder = registry.load_builder(req.segment)
    snippet = builder(params={**{k: v.get("default") for k, v in manifest.params.items()}, **req.params}, slots={"app_var": target.app_var})
    path = root / target.file
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"file not found: {target.file}")
    source = path.read_text(encoding="utf-8")
    try:
        return editing.apply_snippet(source, target.file, snippet, manifest, target.app_var)
    except editing.EditError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _safe_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="path escapes project root")
    return candidate


def create_app(root: Path, token: str, project_root: Path | None = None) -> FastAPI:
    root = root.resolve()
    project_root = project_root or root
    api_prefixes = ("/api/",)

    app = FastAPI(title="Morphkit agent", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def require_token(request, call_next):
        if (
            request.url.path.startswith(api_prefixes)
            and request.headers.get("x-morphkit-token") != token
        ):
            return JSONResponse({"detail": "invalid token"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "root": str(root)}

    @app.get("/api/project")
    def project() -> dict:
        return asdict(scan_project(root))

    @app.get("/api/segments")
    def list_segments() -> list[dict]:
        return [manifest.as_dict() for manifest in registry.load_all()]

    @app.post("/api/preview")
    def preview(req: PreviewRequest) -> dict:
        result = _preview(root, req)
        return {
            "file": result.file,
            "changed": result.changed,
            "reason": result.reason,
            "diff": result.diff,
        }

    @app.post("/api/apply")
    def apply(req: ApplyRequest) -> dict:
        result = _preview(root, req)
        payload = {
            "file": result.file,
            "changed": result.changed,
            "reason": result.reason,
            "diff": result.diff,
        }
        if not result.changed:
            payload["verify"] = {
                "syntax_ok": True,
                "syntax_error": None,
                "tests": {"ran": False, "passed": None, "exit_code": None, "output_tail": "nothing to write"},
            }
            return payload

        ok, error = verifying.check_syntax(result.new, result.file)
        if not ok:
            raise HTTPException(status_code=400, detail=f"generated code does not compile: {error}")

        path = _safe_path(root, result.file)
        path.write_text(result.new, encoding="utf-8")
        payload["verify"] = {
            "syntax_ok": True,
            "syntax_error": None,
            "tests": verifying.run_tests(root),
        }
        return payload

    if (project_root / "ui" / "dist").is_dir():
        app.mount("/", StaticFiles(directory=project_root / "ui" / "dist", html=True), name="ui")
    elif UI_DIST.is_dir():
        app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")
    else:
        @app.get("/", response_class=HTMLResponse)
        def index() -> str:
            return FALLBACK_HTML

    return app
