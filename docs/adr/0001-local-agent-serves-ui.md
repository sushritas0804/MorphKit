# ADR 0001: A local agent serves the UI

Status: accepted, 2026-11-03

## Context

Drag-and-drop adaptation must read the user's project files, write edits, and run
their tests. A hosted web app cannot do this without a local component. The
alternatives were a VS Code extension, a desktop app, a hosted app with GitHub
integration, or a local agent that serves a web UI.

## Decision

`morphkit open <path>` starts a local FastAPI agent on `127.0.0.1`. The agent
serves the prebuilt React UI and the JSON API from the same origin. One process,
one command.

## Consequences

- The UI can use relative `/api` calls, so no CORS setup is needed.
- The agent holds the project root and the API token, so every write is confined
  to one directory.
- Distribution is `pip install morphkit-agent` plus `npm run build` for now.
- A browser tab is the editor, not a native window. Monaco and React Flow fit.

## Security rules that follow from this

Bind loopback only. Require the random token from the printed URL on every
`/api/*` call. Resolve every write path and reject anything outside the project
root. Make no outbound network calls.
