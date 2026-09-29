---
name: ralph-loop-help
description: "Explain the Ralph Loop plugin, how it works, and available skills. Use when the user asks for help with ralph loop, wants to understand the technique, or needs usage examples."
---

> Claude Code compatibility: converted from Cursor plugin `ralph-loop` v1.0.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.
> Cursor hooks are not installed; hook-driven repetition or lifecycle automation is unavailable.

# Ralph Loop Help

## Trigger

The user asks what Ralph Loop is, how it works, or needs usage guidance.

## What to Explain

### What is Ralph Loop?

Ralph Loop implements the Ralph Wiggum technique — an iterative development methodology based on continuous AI loops, pioneered by Geoffrey Huntley.

Core concept: the same prompt is fed to the agent repeatedly. The "self-referential" aspect comes from the agent seeing its own previous work in the files and git history, not from feeding output back as input.

In the original Cursor plugin, a stop hook repeats the prompt. On this host, each later iteration requires the user to invoke the Skill again or a separately verified host continuation mechanism. The saved state lets the agent read its previous work and continue without claiming that a hook is active.

### Starting a Ralph Loop

Tell the agent your task along with options:

```
Start a ralph loop: "Build a REST API for todos" --max-iterations 20 --completion-promise "COMPLETE"
```

Options:
- `--max-iterations N` — max iterations before auto-stop
- `--completion-promise "TEXT"` — phrase to signal completion

How it works:
1. Creates `.claude/ralph/scratchpad.md` state file
2. Agent performs one manual iteration
3. A later invocation reads the saved prompt and increments the iteration
4. The agent stops at the configured maximum or when the completion promise is genuinely satisfied

### Cancelling a Ralph Loop

Ask the agent to cancel the ralph loop. It will remove the state file and report the iteration count.

### Completion Promises

To signal completion, the agent outputs a `<promise>` tag:

```
<promise>TASK COMPLETE</promise>
```

On this host, the agent checks this tag during a manual iteration. No background or indefinite loop is created by the state file.

### When to Use Ralph

**Good for:**
- Well-defined tasks with clear success criteria
- Tasks requiring iteration and refinement
- Iterative development with self-correction
- Greenfield projects

**Not good for:**
- Tasks requiring human judgment or design decisions
- One-shot operations
- Tasks with unclear success criteria

### Learn More

- Original technique: https://ghuntley.com/ralph/
- Ralph Orchestrator: https://github.com/mikeyobrien/ralph-orchestrator

## Output

Present the above information clearly to the user, tailored to their specific question.
