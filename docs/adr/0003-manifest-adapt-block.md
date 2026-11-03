# ADR 0003: Segments declare how they adapt

Status: accepted, 2026-11-03

## Context

README section 9.7 defines a segment manifest with typed params, stage, metrics,
and tests. Adaptation needs more: where the code goes, which scanned values fill
its slots, and how to detect an already-applied segment.

## Decision

Extend the manifest with an `adapt` block:

```yaml
adapt:
  target: fastapi_app
  marker: "# morphkit:segment:request_id"
```

The segment's `apply.py` exposes `build(params, slots) -> Snippet`. A snippet has
`imports`, `defs`, and `register` code. The generic editor decides where each
part goes.

## Consequences

- Segments stay declarative and testable without knowing LibCST.
- The marker makes apply idempotent and gives the scanner a cheap "is present"
  check.
- The editor owns insertion policy, so improving placement improves every
  segment at once.
- The format is a superset of the README manifest, so Phase 4 can still render
  it as a draggable block.
