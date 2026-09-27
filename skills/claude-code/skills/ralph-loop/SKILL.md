---
name: ralph-loop
description: "Start a Ralph Loop for iterative self-referential development. Use when the user asks to run a ralph loop, start an iterative loop, or wants repeated autonomous iteration on a task until completion."
---

> Claude Code compatibility: converted from Cursor plugin `ralph-loop` v1.0.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.
> Cursor hooks are not installed; hook-driven repetition or lifecycle automation is unavailable.

# Ralph Loop

## Trigger

The user wants to start a Ralph loop. An iterative development loop where the same prompt is fed back after every turn, and the agent sees its own previous work each iteration.

## Workflow

1. Gather the user's task prompt and optional parameters:
   - `max_iterations` (number, default 0 for unlimited)
   - `completion_promise` (text, or "null" if not set)

2. Create the directory `.claude/ralph/` if it doesn't exist, then write the state file at `.claude/ralph/scratchpad.md` with this exact format:

   ```markdown
   ---
   iteration: 1
   max_iterations: <N or 0>
   completion_promise: "<TEXT>" or null
   ---

   <the user's task prompt goes here>
   ```

   Example:
   ```markdown
   ---
   iteration: 1
   max_iterations: 20
   completion_promise: "COMPLETE"
   ---

   Build a REST API for todos with CRUD operations, input validation, and tests.
   ```

3. Tell the user: Automatic continuation is unavailable on Claude Code. The state file records a manual iteration; it does not activate a hook.

4. Work on the first iteration. For each later iteration, the user must invoke the Skill again or the host must provide an independently verified continuation mechanism. On manual re-invocation, read the state, increment `iteration`, enforce `max_iterations`, and repeat the saved prompt.

## Guardrails

- If a completion promise is set, you may ONLY output `<promise>TEXT</promise>` when the statement is completely and genuinely true.
- Do not output false promises to escape the loop.
- Always recommend setting `max_iterations` as a safety net.
- Quote the `completion_promise` value in the YAML frontmatter if it contains special characters.

## Output

Report that a manual iteration was initialized (prompt, iteration limit, and promise if set), state that automatic continuation is unavailable, then perform the first iteration.
