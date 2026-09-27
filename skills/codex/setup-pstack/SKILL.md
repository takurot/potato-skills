---
name: setup-pstack
description: "Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes a shared file that converted pstack Skills read explicitly. Use for /setup-pstack, \"configure pstack models\", \"pstack budget\", or changing pstack's model choices."
license: MIT
---

> Codex compatibility: converted from Cursor plugin `pstack` v0.15.5.
> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.
> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.

# Setup pstack

Write `~/.codex/pstack-models.md`, a shared configuration file that each converted pstack Skill reads explicitly. It is not loaded automatically by the host.

## Steps

### 1. Detect available models

Use the current host's subagent interface or its validation error to obtain model identifiers it actually accepts in this session. Do not use a Cursor model API for Claude Code or Codex. If the host cannot enumerate models without running a paid call, ask the user to select from identifiers already accepted in this session, or use `inherit-parent`. Never write an unverified real identifier. The aliases `inherit-parent` and `auto` mean to omit the subagent model parameter.

### 2. Load current state

The default role-to-model mapping is the rule shape shown in step 5 below. If `~/.codex/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these four options with these exact labels, and name the current budget when the rule records one.

- `unlimited — keep max`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Treat the budget as a selection preference, not as syntax inside a model name. Choose only exact identifiers accepted by the current host. If the host exposes reasoning effort separately, set it through that interface. If it exposes distinct model identifiers for effort tiers, choose only an identifier present in the accepted set. Do not construct a model identifier by editing a suffix. When no accepted identifier satisfies the requested budget, mark the role as needing a choice or use `inherit-parent` after confirmation.

**(c) Show the roles and confirm.** Show every role with its model, marking any real slug not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, which is how Auto users stay on Auto) as the options. Prefer AskQuestion over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.

### 5. Write the rule

Write `~/.codex/pstack-models.md` as plain Markdown with a `# budget` comment and one line per role. This file is not host configuration; converted pstack consumers read it explicitly. Overwrite the whole file so re-runs stay idempotent. Use only exact identifiers accepted by the current host. Shape:

```
# pstack model configuration. Consumers read this file explicitly.
# `inherit-parent` or `auto` means: omit the subagent model parameter.
# budget: medium (host-controlled)
feature, refactoring: inherit-parent
bug-fix: inherit-parent
perf-issue: inherit-parent
hillclimb: inherit-parent
judgment and prose: inherit-parent
hardest tasks: inherit-parent
how explorer: inherit-parent
how explainer: inherit-parent
why investigators: inherit-parent
why synthesizer: inherit-parent
reflect tooling: inherit-parent
reflect judgment, divergent, synthesizer: inherit-parent
arena runners: inherit-parent
arena cross-judge pool: inherit-parent
swarm workers: inherit-parent
architect runners: inherit-parent
interrogate reviewers: inherit-parent
```

### 6. Confirm

Tell the user the shared file was written. Explain that it is not loaded automatically by the host: each converted pstack Skill reads it when invoked. Do not claim a configured model is active until a consuming Skill successfully launches a subagent with that exact identifier. Re-running this Skill updates the file.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.
