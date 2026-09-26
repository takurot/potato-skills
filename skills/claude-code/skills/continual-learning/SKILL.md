---
name: continual-learning
description: "Orchestrate continual learning by delegating transcript mining and AGENTS.md updates to `agents-memory-updater`."
disable-model-invocation: true
---

> Claude Code compatibility: converted from Cursor plugin `continual-learning` v1.0.0.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.
> Cursor hooks are not installed; hook-driven repetition or lifecycle automation is unavailable.
> Original agent definitions are bundled under references/cursor-agents for use as subagent prompts.

# Continual Learning

Keep `AGENTS.md` current by delegating the memory update flow to one subagent.

## Trigger

Use when the user asks to mine prior chats, maintain `AGENTS.md`, or run the continual-learning loop.

## Workflow

1. Call `agents-memory-updater`.
2. Return the updater result.

## Guardrails

- Keep the parent skill orchestration-only.
- Do not mine transcripts or edit files in the parent flow.
- Do not bypass the subagent.
