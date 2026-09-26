# potato-skills

[日本語](README_JP.md)

**Last updated:** 2026-09-26

A distribution of Skills from the official [`cursor/plugins`](https://github.com/cursor/plugins) collection, converted into formats that Claude Code and Codex can load.

## Contents

- `skills/claude-code/skills/` — Skills for Claude Code; its parent directory is also a validatable Claude Code plugin
- `skills/codex/` — Skills for Codex, including `agents/openai.yaml`
- `install.sh` — Installer for user-level or project-level installation
- `scripts/build_skills.py` — Conversion script that regenerates the distributions from `ref/plugins`
- `skills/manifest.json` — Manifest recording source paths, versions, and compatibility notes

Only Skills declared by each Cursor plugin's `plugin.json` are converted. Plugins that contain only MCP configuration are not converted because they are not Skills. Two duplicate Skill pairs are consolidated by selecting either the more self-contained copy or the copy from the canonical plugin. The current source revision generates 91 Skills for each host.

## Installation

Clone the repository:

```bash
git clone https://github.com/takurot/potato-skills.git
cd potato-skills
```

Install all Skills for both hosts at the user level:

```bash
./install.sh
```

Install for only one host:

```bash
./install.sh --target claude
./install.sh --target codex
```

Install into a project:

```bash
./install.sh --target both --scope project --project-dir /path/to/project
```

Claude Code Skills are installed in `<project>/.claude/skills/`. Codex Skills are installed in `<project>/.agents/skills/`.

You can also select individual Skills:

```bash
./install.sh --list
./install.sh --target codex --skill thermos --skill tdd
```

Main options:

- `--dry-run` — Show planned operations without writing files
- `--force` — Move conflicting Skills to timestamped backups before updating
- `--scope user|project` — Select the installation scope
- `--target claude|codex|both` — Select the target host

By default, an existing Skill with the same name is not overwritten and is reported as `skipped`. Identical installations are reported as `unchanged`.

User-level Codex backups are stored in `~/.codex/skill-backups/`. Project-level Codex backups are stored in `<project>/.agents/skill-backups/`. Both locations are outside Skill discovery directories.

## Conversion policy

Claude Code and Codex use different Skill frontmatter formats, so this repository provides separate distributions.

| Cursor element | Claude Code | Codex |
|---|---|---|
| `name`, `description` | Normalized to the supported format | Normalized to the supported format |
| `disable-model-invocation` | Preserved | Converted to `allow_implicit_invocation: false` in `agents/openai.yaml` |
| `icon`, `color`, `mode`, `reminder`, `paths` | Unsupported fields removed | Unsupported fields removed |
| Skill scripts, references, and assets | Preserved | Preserved |
| Cursor-specific agent definitions | Bundled under `references/cursor-agents/` | Bundled under `references/cursor-agents/` |
| References to `.cursor/skills/` | Converted to `.claude/skills/` | Converted to `.agents/skills/` or `~/.codex/skills/` |

Names are normalized to lowercase kebab-case. Invalid YAML frontmatter from the source is rewritten as valid YAML.

## Compatibility boundaries

Skill instructions and local resources can be converted, but Cursor-specific runtime capabilities are not bundled.

- Automated repetition and stop interception that depend on Cursor hooks do not run automatically in Claude Code or Codex.
- Skills that use Cursor Canvas include a fallback to a standalone HTML artifact when Canvas is unavailable.
- Skills that use MCP require the corresponding MCP server to be configured separately in Claude Code or Codex.
- Skills that operate the Cursor SDK or Cursor Cloud Agents still require Cursor credentials and services.
- Named Cursor subagents are not registered automatically. Their original definitions are bundled under `references/cursor-agents/` for use as prompts with an available general-purpose subagent.

Each converted Skill also starts with a compatibility note that prevents unavailable host capabilities from being reported as executed. See `skills/manifest.json` for per-Skill constraints.

## Regeneration

Fetch or update the source plugins, then run the builder:

```bash
git clone https://github.com/cursor/plugins.git ref/plugins
python3 scripts/build_skills.py
```

The `ref/` directory is not included in this repository. If `ref/plugins` already exists, update that repository before converting. The builder discovers only the `skills` directories declared by `plugin.json` and deterministically regenerates `skills/`.

## License

The source license for each converted Skill is bundled in that Skill's `LICENSE` file. Copyright notices differ between Skills; keep each corresponding `LICENSE` file when redistributing them.
