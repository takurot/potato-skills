---
name: run-smoke-tests
description: "Run Playwright smoke tests, debug failures, and verify fixes"
license: MIT
---

> Codex compatibility: converted from Cursor plugin `cursor-team-kit` v1.2.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.

# Run smoke tests

## Trigger

Need end-to-end smoke verification before or after changes.

## Workflow

1. Build prerequisites for the target app.
2. Run the relevant smoke suite or a focused test file.
3. If failing, inspect traces/logs and isolate the root cause.
4. Apply a minimal fix and rerun until stable.

## Example Commands

```bash
# Run full smoke suite
npm run smoketest

# Run a specific smoke test file
npm run smoketest -- path/to/test.spec.ts

# Faster iteration when build artifacts are ready
npm run smoketest-no-compile -- path/to/test.spec.ts
```

## Guardrails

- Prefer deterministic waits and assertions over brittle timeouts.
- Re-run passing fixes to reduce flaky false positives.
- Quarantine tests only when explicitly requested and documented.

## Output

- Test results summary
- Root cause and fix
- Remaining flake risk (if any)
