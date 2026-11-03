from __future__ import annotations

import difflib
from collections.abc import Sequence
from typing import Any, cast

import libcst as cst

from .models import EditResult, SegmentManifest, Snippet


class EditError(Exception):
    pass


def make_diff(old: str, new: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{path} (current)",
            tofile=f"{path} (proposed)",
        )
    )


def _is_fastapi_call(value: cst.BaseExpression | None) -> bool:
    if not isinstance(value, cst.Call):
        return False
    func = value.func
    if isinstance(func, cst.Name):
        return func.value == "FastAPI"
    if isinstance(func, cst.Attribute):
        return func.attr.value == "FastAPI"
    return False


def _assigns_app(stmt: cst.BaseStatement, app_var: str) -> bool:
    if not isinstance(stmt, cst.SimpleStatementLine):
        return False
    for small in stmt.body:
        if isinstance(small, cst.Assign):
            targets = [t.target for t in small.targets]
            named = any(isinstance(t, cst.Name) and t.value == app_var for t in targets)
            if named and _is_fastapi_call(small.value):
                return True
        elif isinstance(small, cst.AnnAssign):
            target = small.target
            if (
                isinstance(target, cst.Name)
                and target.value == app_var
                and _is_fastapi_call(small.value)
            ):
                return True
    return False


def _stmt_text(stmt: cst.BaseStatement) -> str:
    return cst.Module(body=[cast(Any, stmt)]).code.strip()


def _def_name(code: str) -> str | None:
    try:
        stmt = cst.parse_statement(code)
    except cst.ParserSyntaxError as exc:
        raise EditError(f"invalid segment definition: {exc}") from exc
    if isinstance(stmt, cst.ClassDef):
        return stmt.name.value
    if isinstance(stmt, cst.FunctionDef):
        return stmt.name.value
    return None


def _import_insert_index(body: list[cst.BaseStatement]) -> int:
    index = 0
    for i, stmt in enumerate(body):
        imports_only = isinstance(stmt, (cst.Import, cst.ImportFrom)) or (
            isinstance(stmt, cst.SimpleStatementLine)
            and bool(stmt.body)
            and all(isinstance(small, (cst.Import, cst.ImportFrom)) for small in stmt.body)
        )
        if imports_only:
            index = i + 1
        elif (
            i == 0
            and isinstance(stmt, cst.SimpleStatementLine)
            and len(stmt.body) == 1
            and isinstance(stmt.body[0], cst.Expr)
            and isinstance(stmt.body[0].value, (cst.SimpleString, cst.ConcatenatedString))
        ):
            index = 1
    return index


class _RegistrationInserter(cst.CSTTransformer):
    def __init__(self, app_var: str, register: Sequence[cst.BaseStatement]) -> None:
        self.app_var = app_var
        self.register = list(register)
        self.inserted = False

    def _insert(self, body: Sequence[cst.BaseStatement]) -> list[cst.BaseStatement]:
        if self.inserted:
            return list(body)
        out: list[cst.BaseStatement] = []
        for stmt in body:
            out.append(stmt)
            if _assigns_app(stmt, self.app_var):
                out.extend(self.register)
                self.inserted = True
        return out

    def leave_Module(self, original: cst.Module, updated: cst.Module) -> cst.Module:
        return updated.with_changes(body=self._insert(updated.body))

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        if not isinstance(updated.body, cst.IndentedBlock):
            return updated
        return updated.with_changes(body=updated.body.with_changes(body=self._insert(updated.body.body)))


def apply_snippet(
    source: str,
    path: str,
    snippet: Snippet,
    manifest: SegmentManifest,
    app_var: str,
) -> EditResult:
    marker = str(manifest.adapt.get("marker") or f"# morphkit:segment:{manifest.name}")
    if marker in source:
        return EditResult(path, False, "already applied", source, source, "")

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise EditError(f"cannot parse {path}: {exc}") from exc

    body = cast(list[cst.BaseStatement], list(module.body))
    existing_text = {_stmt_text(stmt) for stmt in body}
    existing_defs = {
        stmt.name.value
        for stmt in body
        if isinstance(stmt, (cst.ClassDef, cst.FunctionDef))
    }

    new_imports: list[cst.BaseStatement] = []
    for code in snippet.imports:
        if code.strip() in existing_text:
            continue
        new_imports.append(cst.parse_statement(code))

    new_defs: list[cst.BaseStatement] = []
    for code in snippet.defs:
        name = _def_name(code)
        if name is not None and name in existing_defs:
            continue
        new_defs.append(cst.parse_statement(code))

    insert_at = _import_insert_index(body)
    if new_imports or new_defs:
        body[insert_at:insert_at] = new_imports + new_defs
        module = module.with_changes(body=body)

    register_codes = list(snippet.register)
    if register_codes and marker:
        register_codes[-1] = f"{register_codes[-1]}  {marker}"
    register = [cst.parse_statement(code) for code in register_codes]

    inserter = _RegistrationInserter(app_var, register)
    updated = module.visit(inserter)
    if not inserter.inserted:
        raise EditError(
            f"could not find `{app_var} = FastAPI(...)` in {path}; "
            "the app object may be built indirectly"
        )

    new_source = updated.code
    return EditResult(path, True, "preview", source, new_source, make_diff(source, new_source, path))
