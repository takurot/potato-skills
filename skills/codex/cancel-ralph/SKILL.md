---
name: cancel-ralph
description: "Cancel an active Ralph Loop. Use when the user wants to stop, cancel, or abort a running ralph loop."
license: MIT
---

> Codex compatibility: converted from Cursor plugin `ralph-loop` v1.0.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.
> Cursor hooks are not installed; hook-driven repetition or lifecycle automation is unavailable.

# Cancel Ralph

## Trigger

The user wants to cancel or stop saved manual Ralph state.

## Workflow

1. Check if `.codex/ralph/scratchpad.md` exists.

2. **If it does not exist**: Tell the user "No saved manual Ralph state found."

3. **If it exists**:
   - Read `.codex/ralph/scratchpad.md` to get the current iteration from the `iteration:` field.
   - Remove the state file and any done flag:
     ```bash
     rm -rf .codex/ralph
     ```
   - Report: "Removed saved manual Ralph state (was at iteration N)."

## Output

A short confirmation with the iteration count, or a message that no manual state was present.
