from __future__ import annotations

import argparse
import json
import secrets
import socket
import sys
import webbrowser
from dataclasses import asdict
from pathlib import Path

from .scanning import scan_project


def _free_port(start: int) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"no free port in {start}-{start + 19}")


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="morphkit", description="Morphkit local agent")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open", help="open the Morphkit UI against a project")
    open_cmd.add_argument("path", nargs="?", default=".")
    open_cmd.add_argument("--port", type=int, default=8765)
    open_cmd.add_argument("--no-browser", action="store_true")

    scan_cmd = sub.add_parser("scan", help="print project scan as JSON")
    scan_cmd.add_argument("path", nargs="?", default=".")

    args = parser.parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    if args.command == "scan":
        scan = scan_project(root)
        print(json.dumps(asdict(scan), indent=2))
        return 0

    _print_scan(root)

    import uvicorn

    from .server import create_app

    token = secrets.token_urlsafe(24)
    port = _free_port(args.port)
    url = f"http://127.0.0.1:{port}/?t={token}"

    from . import __file__ as agent_file

    project_root = Path(agent_file).resolve().parents[2]
    app = create_app(root, token, project_root=project_root)

    print()
    print(f"morphkit UI: {url}")
    print("press ctrl+c to stop")
    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
