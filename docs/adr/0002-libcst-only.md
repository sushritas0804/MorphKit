# ADR 0002: LibCST only for Python edits

Status: accepted, 2026-11-03

## Context

The adaptation pipeline needs structural edits that preserve formatting. The
README listed tree-sitter for parsing and LibCST for Python transforms. Running
both for the first stack adds a dependency and a second parse for no gain.

## Decision

Use LibCST for both scanning and editing Python. Do not add tree-sitter until
TypeScript support starts.

## Consequences

- One parser, one source of truth for positions and structure.
- LibCST preserves comments and whitespace, which makes diffs trustworthy.
- Scanning is slower than a regex prefilter, so detection first checks whether a
  file contains `FastAPI` before parsing it.
- Tree-sitter will be needed for the project-wide scanner once non-Python
  languages arrive.
