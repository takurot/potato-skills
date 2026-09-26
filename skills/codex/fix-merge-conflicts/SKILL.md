---
name: fix-merge-conflicts
description: "Resolve merge conflicts non-interactively, validate build and tests, and finalize conflict resolution"
license: MIT
---

> Codex compatibility: converted from Cursor plugin `cursor-team-kit` v1.2.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.

# Fix merge conflicts

## Trigger

Branch has unresolved merge conflicts and needs a reliable path to a buildable state.

## Workflow

1. Detect all conflicting files from git status and conflict markers.
2. Resolve each conflict with minimal, correctness-first edits.
3. Prefer preserving both sides when safe. Otherwise, choose the variant that compiles and keeps public behavior stable.
4. Regenerate lockfiles with package manager tools instead of hand-editing.
5. Run compile, lint, and relevant tests.
6. Stage resolved files and summarize key decisions.

## Guardrails

- Keep changes minimal and readable.
- Do not leave conflict markers in any file.
- Avoid broad refactors while resolving conflicts.
- Do not push or tag during conflict resolution.

## Output

- Files resolved
- Notable resolution choices
- Build/test outcome
