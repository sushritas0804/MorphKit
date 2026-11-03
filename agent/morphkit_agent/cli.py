from __future__ import annotations

import argparse
import json
import secrets
import shutil
import socket
import sys
import webbrowser
from dataclasses import asdict
from pathlib import Path

from .scanning import scan_project

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_PROJECTS = REPO_ROOT / "benchmarks" / "projects"


def _free_port(start: int) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"no free port in {start}-{start + 19}")


def _resolve_dir(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(f"not a directory: {path}")
    return path


def _print_scan(root: Path) -> None:
    scan = scan_project(root)
    print(f"project:   {scan.root}")
    print(f"framework: {scan.framework or 'unknown'}")
    print(f"py files:  {len(scan.python_files)}")
    print(f"tests:     {'yes' if scan.has_tests else 'no'}")
    if scan.apps:
        for app in scan.apps:
            print(f"app:       {app.file}:{app.line}  ({app.app_var})")
    else:
        print("app:       no `x = FastAPI(...)` found")
    if scan.existing_segments:
        for name, files in scan.existing_segments.items():
            print(f"segment:   {name} in {', '.join(files)}")
    for warning in scan.warnings:
        print(f"warning:   {warning}")


def prepare_demo(workspace: Path, project: str) -> Path:
    source = DEMO_PROJECTS / project
    if not source.is_dir():
        available = (
            sorted(p.name for p in DEMO_PROJECTS.iterdir() if p.is_dir())
            if DEMO_PROJECTS.is_dir()
            else []
        )
        raise SystemExit(
            f"unknown demo project: {project}. available: {', '.join(available) or 'none'}"
        )
    dest = workspace / ".demo" / project
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)
    return dest


def _serve(root: Path, port_start: int, no_browser: bool) -> int:
    _print_scan(root)

    import uvicorn

    from .server import create_app

    token = secrets.token_urlsafe(24)
    port = _free_port(port_start)
    url = f"http://127.0.0.1:{port}/?t={token}"
    app = create_app(root, token, project_root=REPO_ROOT)

    print()
    print(f"morphkit UI: {url}")
    print("press ctrl+c to stop")
    if not no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="morphkit", description="Morphkit local agent")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open", help="open the Morphkit UI against a project")
    open_cmd.add_argument("path", nargs="?", default=".")
    open_cmd.add_argument("--port", type=int, default=8765)
    open_cmd.add_argument("--no-browser", action="store_true")

    demo_cmd = sub.add_parser("demo", help="copy a benchmark project to .demo and open it")
    demo_cmd.add_argument("--project", default="basic")
    demo_cmd.add_argument("--port", type=int, default=8765)
    demo_cmd.add_argument("--no-browser", action="store_true")

    scan_cmd = sub.add_parser("scan", help="print project scan as JSON")
    scan_cmd.add_argument("path", nargs="?", default=".")

    args = parser.parse_args(argv)

    if args.command == "scan":
        root = _resolve_dir(args.path)
        print(json.dumps(asdict(scan_project(root)), indent=2))
        return 0

    if args.command == "demo":
        dest = prepare_demo(Path.cwd(), args.project)
        print(f"demo copy: {dest}")
        return _serve(dest, args.port, args.no_browser)

    return _serve(_resolve_dir(args.path), args.port, args.no_browser)


if __name__ == "__main__":
    sys.exit(main())
