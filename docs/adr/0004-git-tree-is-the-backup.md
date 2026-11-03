# ADR 0004: The git working tree is the only backup

Status: accepted, 2026-11-03

## Context

Applying a segment edits the user's source files. A safety net is expected.

## Decision

Do not create sidecar `.bak` files or a hidden undo store in the spike. The user
sees a diff before applying, and the project's own git working tree is the
recovery path. Add explicit undo only if the spike shows it is needed.

## Consequences

- Fewer file writes, less state to clean up, and no backup files in the user's
  repo.
- A project without git has only the preview diff as protection. The UI must
  warn before the first apply when the root is not a git repository.
- Undo becomes a UI feature later, not an implicit filesystem convention.
