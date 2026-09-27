#!/usr/bin/env python3
"""Build Claude Code and Codex skill distributions from Cursor plugins."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "ref" / "plugins"
DEFAULT_OUTPUT = ROOT / "skills"
ALLOWED_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# These duplicate skills are either identical or have a more self-contained copy.
PREFERRED_DUPLICATES = {
    "pr-review-canvas": "cursor-team-kit/skills/pr-review-canvas/SKILL.md",
    "thermo-nuclear-code-quality-review": (
        "thermos/skills/thermo-nuclear-code-quality-review/SKILL.md"
    ),
}

EXPERIMENTAL_SKILLS = {"docs-canvas"}

DOCS_CANVAS_SMOKE_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Docs Canvas smoke example</title>
  <style>
    body { font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 72rem; padding: 2rem; }
    nav { position: sticky; top: 0; background: white; padding: 0.75rem 0; }
    nav a { margin-right: 1rem; }
    pre { overflow: auto; padding: 1rem; background: #f4f4f5; }
    svg { max-width: 100%; height: auto; }
  </style>
</head>
<body>
  <header id="overview"><h1>Service documentation</h1><p>Standalone smoke artifact.</p></header>
  <nav aria-label="Documentation sections">
    <a href="#overview">Overview</a>
    <a href="#example">Code</a>
    <a href="#architecture">Architecture</a>
    <a href="#references">References</a>
  </nav>
  <main>
    <section id="example"><h2>Code</h2><pre><code>curl https://api.example.test/health</code></pre></section>
    <section id="architecture">
      <h2>Architecture</h2>
      <svg viewBox="0 0 420 100" role="img" aria-label="Client calls API">
        <rect x="10" y="20" width="120" height="50"></rect>
        <path d="M130 45 H285"></path>
        <rect x="285" y="20" width="120" height="50"></rect>
        <text x="35" y="52">Client</text><text x="325" y="52">API</text>
      </svg>
      <p>See the <a href="#references">source references</a>.</p>
    </section>
    <section id="references"><h2>References</h2><ul><li><code>src/api.ts</code></li></ul></section>
  </main>
</body>
</html>
"""

DOCS_CANVAS_EXPERIMENTAL_NOTICE = """# Experimental Skill

`docs-canvas` is converted from an upstream placeholder and is not installed by default.
Install it explicitly with `--skill docs-canvas` only when you want to evaluate it.

Promotion requires verified Cursor Canvas rendering plus Claude Code and Codex fallback
evaluation for navigation, code blocks, diagrams, cross-references, and a standalone artifact.
The bundled `references/smoke-example.html` is a structural smoke fixture, not proof of a
successful live-host rendering.
"""


@dataclass(frozen=True)
class SourceSkill:
    name: str
    description: str
    explicit_only: bool
    source_file: Path
    plugin_root: Path
    plugin_name: str
    plugin_version: str
    body: str
    has_agents: bool
    has_hooks: bool
    has_mcp: bool


def split_frontmatter(text: str, path: Path) -> tuple[list[str], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "".join(lines[index + 1 :]).lstrip("\n")
    raise ValueError(f"{path}: unterminated YAML frontmatter")


def frontmatter_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index].rstrip("\r\n")
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if not match:
            index += 1
            continue
        key, value = match.group(1), match.group(2) or ""
        if value in {">", ">-", "|", "|-"}:
            block: list[str] = []
            index += 1
            while index < len(lines):
                nested = lines[index].rstrip("\r\n")
                if nested and not nested[0].isspace():
                    break
                block.append(nested.strip())
                index += 1
            fields[key] = (" " if value.startswith(">") else "\n").join(block).strip()
            continue
        fields[key] = unquote_scalar(value.strip())
        index += 1
    return fields


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def find_plugin_root(skill_file: Path, source: Path) -> Path:
    for parent in skill_file.parents:
        if (parent / ".cursor-plugin" / "plugin.json").is_file():
            return parent
        if parent == source:
            break
    raise ValueError(f"{skill_file}: no parent plugin manifest")


def declared_skill_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for manifest_file in sorted(source.rglob(".cursor-plugin/plugin.json")):
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        relative = manifest.get("skills")
        if not relative:
            continue
        skill_root = (manifest_file.parent.parent / relative).resolve()
        if not skill_root.is_dir():
            raise ValueError(f"{manifest_file}: declared skills directory does not exist")
        files.extend(sorted(skill_root.rglob("SKILL.md")))
    return files


def normalized_name(raw_name: str, skill_file: Path) -> str:
    candidate = raw_name.strip().lower().replace("_", "-")
    candidate = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
    folder_name = skill_file.parent.name
    if raw_name != candidate and ALLOWED_NAME.fullmatch(folder_name):
        # Existing relative links commonly use the already-valid folder name.
        candidate = folder_name
    if not candidate:
        candidate = folder_name.lower()
    if len(candidate) > 64:
        raise ValueError(f"{skill_file}: normalized name is longer than 64 characters")
    if not ALLOWED_NAME.fullmatch(candidate):
        raise ValueError(f"{skill_file}: cannot normalize skill name {raw_name!r}")
    return candidate


def normalized_description(description: str) -> str:
    # Codex reserves angle brackets in descriptions for internal parsing.
    description = description.replace("<", "").replace(">", "")
    if len(description) > 1024:
        description = description[:1020].rsplit(" ", 1)[0] + "..."
    return description


def load_skills(source: Path) -> list[SourceSkill]:
    candidates: list[SourceSkill] = []
    for skill_file in declared_skill_files(source):
        frontmatter, body = split_frontmatter(skill_file.read_text(encoding="utf-8"), skill_file)
        fields = frontmatter_fields(frontmatter)
        plugin_root = find_plugin_root(skill_file, source)
        manifest = json.loads(
            (plugin_root / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        raw_name = fields.get("name", skill_file.parent.name)
        description = fields.get("description", "").strip()
        if not description:
            raise ValueError(f"{skill_file}: missing description")
        description = normalized_description(description)
        candidates.append(
            SourceSkill(
                name=normalized_name(raw_name, skill_file),
                description=description,
                explicit_only=fields.get("disable-model-invocation", "false").lower()
                == "true",
                source_file=skill_file,
                plugin_root=plugin_root,
                plugin_name=manifest["name"],
                plugin_version=manifest.get("version", "unknown"),
                body=body,
                has_agents="agents" in manifest,
                has_hooks="hooks" in manifest,
                has_mcp="mcpServers" in manifest,
            )
        )

    grouped: dict[str, list[SourceSkill]] = {}
    for skill in candidates:
        grouped.setdefault(skill.name, []).append(skill)

    selected: list[SourceSkill] = []
    for name, matches in grouped.items():
        if len(matches) == 1:
            selected.append(matches[0])
            continue
        preferred = PREFERRED_DUPLICATES.get(name)
        if not preferred:
            origins = ", ".join(str(item.source_file.relative_to(source)) for item in matches)
            raise ValueError(f"duplicate skill name {name!r}: {origins}")
        chosen = [item for item in matches if str(item.source_file.relative_to(source)) == preferred]
        if len(chosen) != 1:
            raise ValueError(f"preferred duplicate {preferred!r} for {name!r} was not found")
        selected.append(chosen[0])
    return sorted(selected, key=lambda item: item.name)


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def compatibility_notes(skill: SourceSkill) -> list[str]:
    notes: list[str] = []
    combined = skill.body.lower()
    if skill.name in EXPERIMENTAL_SKILLS:
        notes.append(
            "Experimental: excluded from default installation until live host evaluation passes."
        )
    if skill.has_hooks:
        notes.append("Cursor hooks are not installed; hook-driven repetition or lifecycle automation is unavailable.")
    if referenced_agent_files(skill):
        notes.append("Original agent definitions are bundled under references/cursor-agents for use as subagent prompts.")
    if skill.has_mcp:
        notes.append("This skill requires the corresponding MCP server to be configured separately.")
    if "cursor canvas" in combined or "skills-cursor/canvas" in combined:
        notes.append("When Cursor Canvas is unavailable, create a standalone HTML artifact with ordinary web technologies.")
    if "~/.cursor/projects" in combined or "agent-transcripts" in combined:
        notes.append("Cursor transcript paths are not portable; use only an equivalent transcript source exposed by the active host.")
    if "cursor sdk" in combined or "@cursor/" in combined:
        notes.append("Cursor SDK operations still require Cursor credentials and services; the host agent does not replace them.")
    return notes


def referenced_agent_files(skill: SourceSkill) -> list[Path]:
    if not skill.has_agents:
        return []
    agent_dir = skill.plugin_root / "agents"
    if not agent_dir.is_dir():
        return []
    body = skill.body.lower()
    matches: list[Path] = []
    for agent_file in sorted(agent_dir.glob("*.md")):
        frontmatter, _ = split_frontmatter(
            agent_file.read_text(encoding="utf-8"), agent_file
        )
        fields = frontmatter_fields(frontmatter)
        names = {agent_file.stem.lower(), fields.get("name", "").lower()}
        if any(name and name in body for name in names):
            matches.append(agent_file)
    return matches


def adapt_hookless_workflow(skill_name: str, body: str, host: str) -> str:
    if skill_name == "ralph-loop":
        body = body.replace(
            "3. Confirm to the user that the Ralph loop is active, then begin working on the task.\n\n"
            "4. The stop hook automatically intercepts each turn end and feeds the same prompt "
            "back as a followup message. You will see it prefixed with `[Ralph loop iteration N.]`.",
            "3. Tell the user: Automatic continuation is unavailable on "
            f"{host}. The state file records a manual iteration; it does not activate a hook.\n\n"
            "4. Work on the first iteration. For each later iteration, the user must invoke the "
            "Skill again or the host must provide an independently verified continuation "
            "mechanism. On manual re-invocation, read the state, increment `iteration`, enforce "
            "`max_iterations`, and repeat the saved prompt.",
        )
        body = body.replace(
            "Confirm the loop is active (prompt, iteration limit, promise if set), then start "
            "working on the task immediately.",
            "Report that a manual iteration was initialized (prompt, iteration limit, and "
            "promise if set), state that automatic continuation is unavailable, then perform "
            "the first iteration.",
        )
    elif skill_name == "cancel-ralph":
        body = body.replace("an active Ralph loop", "saved manual Ralph state")
        body = body.replace("an active ralph loop", "saved manual Ralph state")
        body = body.replace("No active Ralph loop found.", "No saved manual Ralph state found.")
        body = body.replace(
            "Cancelled Ralph loop (was at iteration N).",
            "Removed saved manual Ralph state (was at iteration N).",
        )
        body = body.replace(
            "a message that no loop was active", "a message that no manual state was present"
        )
    elif skill_name == "ralph-loop-help":
        body = body.replace(
            "Each iteration:\n1. The agent receives the SAME prompt\n2. Works on the task, "
            "modifying files\n3. Tries to exit\n4. Stop hook intercepts and feeds the same "
            "prompt again\n5. The agent sees its previous work in the files\n6. Iteratively "
            "improves until completion",
            "In the original Cursor plugin, a stop hook repeats the prompt. On this host, "
            "each later iteration requires the user to invoke the Skill again or a separately "
            "verified host continuation mechanism. The saved state lets the agent read its "
            "previous work and continue without claiming that a hook is active.",
        )
        body = body.replace(
            "2. Agent works on the task\n3. Stop hook intercepts exit and feeds the same "
            "prompt back\n4. Agent sees its previous work and iterates\n5. Continues until "
            "promise detected or max iterations reached",
            "2. Agent performs one manual iteration\n3. A later invocation reads the "
            "saved prompt and increments the iteration\n4. The agent stops at the configured "
            "maximum or when the completion promise is genuinely satisfied",
        )
        body = body.replace(
            "The stop hook looks for this specific tag. Without it (or `--max-iterations`), "
            "Ralph runs indefinitely.",
            "On this host, the agent checks this tag during a manual iteration. No background "
            "or indefinite loop is created by the state file.",
        )
    elif skill_name == "advisor":
        body = body.replace(
            "When that file exists with `\"enabled\": true`, advisor mode is on for this project.",
            "When that file exists with `\"enabled\": true`, it records manual advisor "
            "preferences for the current conversation; it does not install lifecycle hooks.",
        )
        body = body.replace(
            "| `/advisor nudge on` / `off` | Toggle the end-of-turn reminder posted by the "
            "plugin's stop hook (default on). |",
            "| `/advisor nudge on` / `off` | Record a nudge preference only. Automatic "
            "end-of-turn nudges are unavailable on this host. |",
        )
        body = body.replace(
            "that re-binds the mode to this conversation, the hooks re-fill `conversation_id` "
            "and `transcript_path`, and the next consult starts a fresh advisor instead of "
            "resuming another chat's.",
            "that re-binds the manual preferences to this conversation. Leave "
            "`conversation_id` and `transcript_path` null unless the active host explicitly "
            "provides safe current-conversation values. The next consult starts a fresh advisor "
            "instead of resuming another chat's.",
        )
        body = body.replace(
            "The plugin's hooks fill in `conversation_id`, `transcript_path`, `consults`, and "
            "`last_consult_at`. Leave them alone.",
            "Automatic checkpoint and end-of-turn nudge hooks are unavailable. Keep "
            "`conversation_id` and `transcript_path` null unless the active host exposes them "
            "for this conversation. Update `consults` and `last_consult_at` manually only after "
            "a successful consult.",
        )
        body = body.replace(
            "Confirm in one line: `Advisor on: <slug>. I'll consult it before major decisions, "
            "when I'm stuck, and before I call the task done.` Then continue with any task in "
            "the same message.",
            "Confirm in one line: `Advisor preferences saved: <slug>. Automatic checkpoints "
            "and nudges are unavailable; I will consult only when explicitly invoked in this "
            "conversation.` Then continue with any task in the same message.",
        )
        body = body.replace(
            "Keep the advisor's full response out of the chat unless the user asks; the hooks "
            "also append it to `.cursor/advisor/log.md`.",
            "Keep the advisor's full response out of the chat unless the user asks. If a log is "
            "required, append it explicitly and report that write; no hook records it.",
        )
        body = body.replace(
            "Keep the advisor's full response out of the chat unless the user asks; the hooks "
            "also append it to",
            "Keep the advisor's full response out of the chat unless the user asks. If a log "
            "is required, append it explicitly and report that write; no hook records it at",
        )
        start = body.find("## End-of-turn nudge")
        end = body.find("## Disabling", start)
        if start != -1 and end != -1:
            body = (
                body[:start]
                + "## End-of-turn nudge\n\n"
                + "Automatic checkpoint and end-of-turn nudge hooks are unavailable on this "
                + "host. Do not promise or wait for a follow-up message. The user must invoke "
                + "`/advisor ask ...` explicitly for each consult. The `nudge` field is only a "
                + "saved preference for a future verified host integration.\n\n"
                + body[end:]
            )
    return body


def adapt_pr_review_canvas(skill_name: str, body: str) -> str:
    if skill_name != "pr-review-canvas":
        return body

    body = body.replace(
        "gh api repos/{owner}/{repo}/pulls/{number}/files --paginate \\\n"
        "  --jq '[.[] | {key: (.filename | gsub(\"[^a-zA-Z0-9]\"; \"_\")), "
        "value: (.patch // \"\")}] | from_entries' \\\n"
        "  > /tmp/pr-patches-{number}.json",
        "gh api repos/{owner}/{repo}/pulls/{number}/files --paginate \\\n"
        "  --jq '.[] | {key: .filename, value: (.patch // \"\")}' \\\n"
        "  | jq -s 'from_entries' \\\n"
        "  > /tmp/pr-patches-{number}.json",
    )
    body = body.replace(
        "The diff data keys should match the `data-diff` attribute values in the HTML:\n"
        "```html\n<div data-diff=\"path_to_file_ts\"></div>\n```",
        "The JSON key remains the exact original filename so distinct paths never collide. "
        "The `data-diff` attribute must contain that same filename with HTML attribute "
        "escaping only; the browser decodes the attribute before the renderer uses it as a "
        "JSON key. When generating placeholders in Python, use:\n"
        "```python\nimport html\n\n"
        "safe_filename = html.escape(filename, quote=True)\n"
        "placeholder = f'<div data-diff=\"{safe_filename}\"></div>'\n```",
    )
    return body


PSTACK_CONFIG_CONSUMERS = {
    "architect",
    "arena",
    "how",
    "interrogate",
    "reflect",
    "swarm",
    "why",
}


def adapt_pstack_config(skill_name: str, body: str, models_file: str) -> str:
    body = body.replace("pstack-models.mdc", models_file)
    if skill_name in PSTACK_CONFIG_CONSUMERS:
        body = (
            f"> Model configuration: Read `{models_file}` before choosing any model. The host "
            "does not load this file automatically. Use only the role lines in that file and "
            "only exact model identifiers accepted by the current host. For `auto` or "
            "`inherit-parent`, omit the subagent model parameter.\n\n"
            + body
        )
    if skill_name != "setup-pstack":
        return body

    body = body.replace(
        f"Write `{models_file}`, an always-applied rule that sets pstack's model per role.",
        f"Write `{models_file}`, a shared configuration file that each converted pstack Skill "
        "reads explicitly. It is not loaded automatically by the host.",
    )
    body = body.replace(
        "Enumerate the model slugs you can pass to a `Task` subagent in this session. That is "
        "the dependable source. If Cursor also exposes a models API or CLI that lists the "
        "user's entitled models, prefer it for completeness. If you cannot detect any, ask "
        "the user to paste the slugs they have access to. Never write a real slug you have "
        "not confirmed is available. The aliases `inherit-parent` and `auto` are always valid "
        "even though they are not detected slugs.",
        "Use the current host's subagent interface or its validation error to obtain model "
        "identifiers it actually accepts in this session. Do not use a Cursor model API for "
        "Claude Code or Codex. If the host cannot enumerate models without running a paid "
        "call, ask the user to select from identifiers already accepted in this session, or "
        "use `inherit-parent`. Never write an unverified real identifier. The aliases "
        "`inherit-parent` and `auto` mean to omit the subagent model parameter.",
    )
    body = body.replace(
        "**(b) Apply it.** Build the working table from the skill defaults, and on a re-run "
        "keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). "
        "`unlimited` leaves every effort as in that table. `large`, `medium`, and `small` set "
        "the effort token of every real slug, panel entries included, to `xhigh`, `high`, or "
        "`medium`. The effort token is the last token, or the one before a trailing `fast`, on "
        "the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a "
        "detected slug, use the same family's detected slug with the highest effort at or "
        "below the target, else mark the role as needing a choice. `inherit-parent` and `auto` "
        "do not change. So `small` turns `claude-opus-5-5-max` into "
        "`claude-opus-5-5-medium`, and `grok-4.7-xhigh-fast` into "
        "`grok-4.7-medium-fast`.",
        "**(b) Apply it.** Treat the budget as a selection preference, not as syntax inside a "
        "model name. Choose only exact identifiers accepted by the current host. If the host "
        "exposes reasoning effort separately, set it through that interface. If it exposes "
        "distinct model identifiers for effort tiers, choose only an identifier present in "
        "the accepted set. Do not construct a model identifier by editing a suffix. When no "
        "accepted identifier satisfies the requested budget, mark the role as needing a "
        "choice or use `inherit-parent` after confirmation.",
    )
    body = body.replace(
        f"Write `{models_file}` with `alwaysApply: true`, a `# budget` line with the chosen "
        "label and its target effort, and one line per role, using the same labels poteto-mode "
        "uses. Overwrite the whole file so re-runs stay idempotent. Shape:",
        f"Write `{models_file}` as plain Markdown with a `# budget` comment and one line per "
        "role. This file is not host configuration; converted pstack consumers read it "
        "explicitly. Overwrite the whole file so re-runs stay idempotent. Use only exact "
        "identifiers accepted by the current host. Shape:",
    )
    old_shape = """---
description: pstack per-role model choices (overrides skill defaults)
alwaysApply: true
---
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.
# budget: unlimited (max)
feature, refactoring: grok-4.7-xhigh-fast
bug-fix: grok-4.7-xhigh-fast
perf-issue: grok-4.7-xhigh-fast
hillclimb: grok-4.7-xhigh-fast
judgment and prose: claude-opus-5-5-max
hardest tasks: claude-opus-5-5-max
how explorer: grok-4.7-xhigh-fast
how explainer: claude-opus-5-5-max
why investigators: grok-4.7-xhigh-fast
why synthesizer: claude-opus-5-5-max
reflect tooling: gpt-5.6-sol-max
reflect judgment, divergent, synthesizer: claude-opus-5-5-max
arena runners: claude-opus-5-5-max, gpt-5.6-sol-max, grok-4.7-xhigh-fast
arena cross-judge pool: claude-opus-5-5-max, gpt-5.6-sol-max, grok-4.7-xhigh-fast
swarm workers: grok-4.7-xhigh-fast
architect runners: claude-opus-5-5-max, gpt-5.6-sol-max, grok-4.7-xhigh-fast
interrogate reviewers: claude-opus-5-5-max, gpt-5.6-sol-max, grok-4.7-xhigh-fast"""
    safe_shape = """# pstack model configuration. Consumers read this file explicitly.
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
interrogate reviewers: inherit-parent"""
    body = body.replace(old_shape, safe_shape)
    body = body.replace(
        "Tell the user the rule was written and that it applies to new sessions. Re-running "
        "this skill updates it.",
        "Tell the user the shared file was written. Explain that it is not loaded "
        "automatically by the host: each converted pstack Skill reads it when invoked. Do not "
        "claim a configured model is active until a consuming Skill successfully launches a "
        "subagent with that exact identifier. Re-running this Skill updates the file.",
    )
    return body


def adapt_docs_canvas(skill_name: str, body: str, host: str) -> str:
    if skill_name != "docs-canvas":
        return body

    if host == "Claude Code":
        fallback_example = (
            "### Claude Code fallback example\n\n"
            "Write one self-contained `docs-canvas.html` file in the requested project "
            "directory, then report its absolute path. Embed CSS, JavaScript, diagrams, and "
            "source citations in that file; do not claim that Cursor Canvas rendered it."
        )
    else:
        fallback_example = (
            "### Codex fallback example\n\n"
            "Write one self-contained `docs-canvas.html` file in the workspace and return a "
            "clickable local file link. Embed CSS, JavaScript, diagrams, and source citations "
            "in that file; do not claim that Cursor Canvas rendered it."
        )

    evaluation = f"""

## Experimental host contract

This converted Skill is experimental because its upstream workflow is still a placeholder.
It is excluded from default installation. Use it only when the user explicitly selects it,
and describe the result as an evaluation artifact rather than a production-ready canvas.

### Cursor Canvas example

Only when the active host actually exposes Cursor Canvas, read the installed Canvas SDK Skill
and type declarations, build the documented section/card components, and verify the rendered
canvas. Do not infer SDK availability from this text.

{fallback_example}

### Required smoke evaluation

Before reporting success, verify the produced artifact has all of the following:

1. navigation links whose fragment targets exist;
2. syntax-readable code blocks;
3. at least one diagram with an accessible label or text alternative;
4. cross-references that resolve to sections or cited source paths; and
5. one standalone output that does not require local package trees or external assets.

Use `references/smoke-example.html` as a structural baseline. Passing that static fixture is
not evidence that {host} or Cursor Canvas rendered a newly generated artifact; report live
rendering as unverified unless it was actually exercised.
"""
    return body.rstrip() + evaluation


def adapt_body(skill: SourceSkill, target: str) -> str:
    if target == "claude-code":
        user_skills = "~/.claude/skills/"
        project_skills = ".claude/skills/"
        state_root = ".claude/"
        models_file = "~/.claude/pstack-models.md"
        host = "Claude Code"
    else:
        user_skills = "~/.codex/skills/"
        project_skills = ".agents/skills/"
        state_root = ".codex/"
        models_file = "~/.codex/pstack-models.md"
        host = "Codex"

    body = skill.body
    protected = "__CURSOR_CANVAS_SKILLS_PATH__"
    body = body.replace("~/.cursor/skills-cursor/", protected)
    body = body.replace("~/.cursor/skills/", user_skills)
    body = body.replace(".cursor/skills/", project_skills)
    body = body.replace(protected, "~/.cursor/skills-cursor/")
    body = body.replace("~/.cursor/rules/pstack-models.mdc", models_file)
    body = body.replace(".cursor/advisor/", f"{state_root}advisor/")
    body = body.replace(".cursor/ralph/", f"{state_root}ralph/")
    body = body.replace(".cursor/ralph", f"{state_root}ralph")
    canvas_instruction = (
        "Read `~/.cursor/skills-cursor/canvas/SKILL.md` first. It contains the generation "
        "policy, design guidance, slop rules, self-check, and file-path conventions you must "
        "follow. The full component and hook surface is declared in "
        "`~/.cursor/skills-cursor/canvas/sdk/index.d.ts` and its sibling `.d.ts` files — read "
        "them to discover exact exports and prop shapes rather than guessing."
    )
    canvas_fallback = (
        "If the Cursor Canvas SDK is available, read its `SKILL.md` and type declarations "
        "before using it. Otherwise, skip Cursor SDK calls and produce an equivalent "
        "standalone HTML artifact with ordinary HTML, CSS, and JavaScript."
    )
    body = body.replace(canvas_instruction, canvas_fallback)
    cursor_transcript_location = (
        "Transcripts live at `~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl`, "
        "where `<slug>` is the workspace path with the leading slash dropped and each \"/\" "
        "turned into \"-\" (so `/Users/you/proj` becomes `Users-you-proj`). Every line is one "
        "chat message."
    )
    portable_transcript_location = (
        "Use only the active host's transcript source when it is explicitly exposed for the "
        "current workspace. Do not scan unrelated project or user-session directories. If the "
        "host does not expose transcripts, say so and continue with live repository state and "
        "the current conversation."
    )
    body = body.replace(cursor_transcript_location, portable_transcript_location)
    body = body.replace(
        "The parent finds its own transcript file before fanning out. The system prompt names "
        "the active workspace's `agent-transcripts/` directory. Use that path. Do not glob "
        "across `~/.cursor/projects/*/`. That crosses workspace boundaries and reads private "
        "chats from unrelated projects.",
        "Before fanning out, use the current transcript only when the active host explicitly "
        "exposes it. Do not scan other project or user-session roots. If no current transcript "
        "is exposed, continue from the current conversation and live workspace state.",
    )
    body = body.replace(
        "Locate the active workspace's transcripts before fanning out. The system prompt names "
        "the workspace's `agent-transcripts/` directory. Use only that path. Don't glob across "
        "`~/.cursor/projects/*/`. That crosses workspace boundaries and reads private chats "
        "from unrelated projects.",
        "Before fanning out, use workspace transcripts only when the active host explicitly "
        "exposes them. Do not scan other project or user-session roots. If transcripts are not "
        "available, continue from the current conversation and live workspace state.",
    )
    body = body.replace(
        "Read this run's transcript under the active workspace's `agent-transcripts/` directory "
        "(the system prompt names the path). Don't glob across `~/.cursor/projects/*/`. That "
        "reads unrelated private chats.",
        "Read this run's transcript only when the active host explicitly exposes it. Do not "
        "scan other project or user-session roots. If it is unavailable, audit the run from "
        "the current conversation and decision log.",
    )
    body = adapt_hookless_workflow(skill.name, body, host)
    body = adapt_pr_review_canvas(skill.name, body)
    body = adapt_pstack_config(skill.name, body, models_file)
    body = adapt_docs_canvas(skill.name, body, host)

    notes = compatibility_notes(skill)
    preface = [
        f"> {host} compatibility: converted from Cursor plugin `{skill.plugin_name}` v{skill.plugin_version}.",
        "> Use the host's equivalent tool or subagent interface when the text names a Cursor-specific control.",
        "> Never claim that an unavailable hook, MCP server, named agent, or Cursor service ran.",
    ]
    preface.extend(f"> {note}" for note in notes)
    return "\n".join(preface) + "\n\n" + body.rstrip() + "\n"


TEXT_RESOURCE_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}


def adapt_support_text(text: str, target: str) -> str:
    if target == "claude-code":
        user_skills = "~/.claude/skills/"
        project_skills = ".claude/skills/"
        state_root = ".claude/"
    else:
        user_skills = "~/.codex/skills/"
        project_skills = ".agents/skills/"
        state_root = ".codex/"

    protected = "__CURSOR_CANVAS_SKILLS_PATH__"
    text = text.replace("~/.cursor/skills-cursor/", protected)
    text = text.replace("~/.cursor/skills/", user_skills)
    text = text.replace(".cursor/skills/", project_skills)
    text = text.replace(protected, "~/.cursor/skills-cursor/")
    text = text.replace(
        f"(workspace `{project_skills}`, user-level `{user_skills}`, or "
        "plugin-installed paths under `~/.cursor/plugins/`)",
        f"(workspace `{project_skills}`, user-level `{user_skills}`, or another "
        "host-installed Skill root explicitly exposed in the active session)",
    )
    text = text.replace(
        "Inspect only transcript files under "
        "`~/.cursor/projects/<workspace-slug>/agent-transcripts/` that are new or have newer "
        "mtimes than the index.",
        "Inspect transcript files only when the active host explicitly exposes a transcript "
        "source for the current workspace. Process only entries newer than the index. If no "
        "source is exposed, do not scan user or unrelated project directories; report that "
        "transcript mining is unavailable.",
    )
    text = text.replace(
        ".cursor/hooks/state/continual-learning-index.json",
        f"{state_root}continual-learning/index.json",
    )
    text = text.replace(
        "A local transcript under the active workspace's `agent-transcripts/` directory "
        "(the system prompt names the path. Do not glob across "
        "`~/.cursor/projects/*/`, that crosses workspace boundaries and reads private chats "
        "from unrelated projects), a cloud-agent URL, or a pushed branch.",
        "A local transcript only when the active host explicitly exposes it for the current "
        "workspace, a cloud-agent URL, or a pushed branch. Never scan other project or user "
        "session roots for transcripts.",
    )
    text = text.replace(
        "Read each candidate's local transcript under the active workspace's "
        "`agent-transcripts/` directory (the system prompt names this path). Do not glob "
        "across `~/.cursor/projects/*/`. That crosses workspace boundaries and reads private "
        "chats from unrelated projects.",
        "Read each candidate transcript only when the active host explicitly exposes it for "
        "the current workspace. Never scan other project or user session roots. If no "
        "transcript is exposed, grade from the produced artifacts and state that chain-level "
        "verification was unavailable.",
    )
    text = text.replace(
        "# Transcripts dir: ~/.cursor/projects/<slugified-repo-path>/agent-transcripts.\n"
        "slug=$(printf '%s' \"$main_wt\" | sed 's#^/##; s#/#-#g')\n"
        'transcripts="$HOME/.cursor/projects/$slug/agent-transcripts"',
        "# Optional, explicitly supplied transcript root for the active workspace only.\n"
        "# Leave unset when the host does not expose workspace transcripts.\n"
        'transcripts="${POTATO_TRANSCRIPTS_DIR:-}"',
    )
    return text


def adapt_copied_resources(destination: Path, target: str) -> None:
    for path in destination.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_RESOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        adapted = adapt_support_text(text, target)
        if adapted != text:
            path.write_text(adapted, encoding="utf-8")


def copy_support_files(skill: SourceSkill, destination: Path, target: str) -> None:
    for child in skill.source_file.parent.iterdir():
        if child.name == "SKILL.md":
            continue
        target_path = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target_path, symlinks=True)
        else:
            shutil.copy2(child, target_path, follow_symlinks=False)

    for agent_file in referenced_agent_files(skill):
        agent_destination = destination / "references" / "cursor-agents"
        agent_destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_file, agent_destination / agent_file.name)

    license_file = skill.plugin_root / "LICENSE"
    if license_file.is_file():
        shutil.copy2(license_file, destination / "LICENSE")
    adapt_copied_resources(destination, target)


def short_description(description: str) -> str:
    plain = re.sub(r"[`*_#]", "", description).strip()
    if len(plain) > 64:
        plain = plain[:61].rsplit(" ", 1)[0] + "..."
    if len(plain) < 25:
        plain = f"Use this workflow: {plain}"
    return plain[:64]


def write_skill(skill: SourceSkill, target: str, destination: Path) -> None:
    destination.mkdir(parents=True)
    copy_support_files(skill, destination, target)
    description = skill.description
    if skill.name in EXPERIMENTAL_SKILLS:
        description = f"[Experimental] {description}"
        (destination / "EXPERIMENTAL.md").write_text(
            DOCS_CANVAS_EXPERIMENTAL_NOTICE, encoding="utf-8"
        )
        references = destination / "references"
        references.mkdir(exist_ok=True)
        (references / "smoke-example.html").write_text(
            DOCS_CANVAS_SMOKE_HTML, encoding="utf-8"
        )
    if skill.name == "setup-pstack":
        description = description.replace(
            "writes an always-applied rule that overrides the skill defaults",
            "writes a shared file that converted pstack Skills read explicitly",
        )
    frontmatter = [
        "---",
        f"name: {skill.name}",
        f"description: {yaml_string(description)}",
    ]
    if target == "codex":
        frontmatter.append("license: MIT")
    if target == "claude-code" and skill.explicit_only:
        frontmatter.append("disable-model-invocation: true")
    frontmatter.append("---")
    contents = "\n".join(frontmatter) + "\n\n" + adapt_body(skill, target)
    (destination / "SKILL.md").write_text(contents, encoding="utf-8")

    if target == "codex":
        agent_dir = destination / "agents"
        agent_dir.mkdir(exist_ok=True)
        lines = [
            "interface:",
            f"  display_name: {yaml_string(skill.name.replace('-', ' ').title())}",
            f"  short_description: {yaml_string(short_description(description))}",
        ]
        if skill.explicit_only:
            lines.extend(["policy:", "  allow_implicit_invocation: false"])
        (agent_dir / "openai.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def source_revision(source: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def assert_safe_output(output: Path, source: Path) -> None:
    protected = {Path("/"), Path.home().resolve(), ROOT.resolve(), ROOT.parent.resolve()}
    if output in protected:
        raise ValueError(f"refusing unsafe output directory: {output}")
    if output == source or output in source.parents or source in output.parents:
        raise ValueError("output and source directories must not contain one another")
    if not output.exists():
        return
    manifest_file = output / "manifest.json"
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"refusing to replace unrecognized output directory: {output}"
        ) from error
    if manifest.get("source") != "https://github.com/cursor/plugins":
        raise ValueError(f"refusing to replace unrecognized output directory: {output}")


def build(source: Path, output: Path) -> None:
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")
    assert_safe_output(output, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    skills = load_skills(source)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))

    manifest_skills: list[dict[str, object]] = []
    for skill in skills:
        for target in ("claude-code", "codex"):
            destination_root = temporary / target
            if target == "claude-code":
                destination_root /= "skills"
            write_skill(skill, target, destination_root / skill.name)
        manifest_skills.append(
            {
                "name": skill.name,
                "plugin": skill.plugin_name,
                "plugin_version": skill.plugin_version,
                "source": str(skill.source_file.relative_to(source)),
                "explicit_only": skill.explicit_only,
                "experimental": skill.name in EXPERIMENTAL_SKILLS,
                "default_install": skill.name not in EXPERIMENTAL_SKILLS,
                "compatibility_notes": compatibility_notes(skill),
            }
        )

    manifest = {
        "schema_version": 1,
        "generator": "scripts/build_skills.py",
        "source": "https://github.com/cursor/plugins",
        "source_revision": source_revision(source),
        "skill_count": len(skills),
        "skills": manifest_skills,
    }
    (temporary / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    claude_manifest_dir = temporary / "claude-code" / ".claude-plugin"
    claude_manifest_dir.mkdir(parents=True)
    (claude_manifest_dir / "plugin.json").write_text(
        json.dumps(
            {
                "name": "potato-skills",
                "version": "1.0.0",
                "description": "Cursor plugin skills converted for Claude Code.",
                "author": {"name": "potato-skills contributors"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if output.exists():
        shutil.rmtree(output)
    temporary.rename(output)
    print(f"Built {len(skills)} skills for Claude Code and Codex in {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        build(args.source.resolve(), args.output.resolve())
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
