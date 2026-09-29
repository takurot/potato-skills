# potato-skills

[日本語](README_JP.md)

**Last updated:** 2026-09-29

A distribution of Skills from the official [`cursor/plugins`](https://github.com/cursor/plugins) collection, converted into formats that Claude Code and Codex can load.

## Contents

- `skills/claude-code/skills/` — Skills for Claude Code; its parent directory is also a validatable Claude Code plugin
- `skills/codex/` — Skills for Codex, including `agents/openai.yaml`
- `install.sh` — Installer for user-level or project-level installation
- `scripts/build_skills.py` — Conversion script that regenerates the distributions from `ref/plugins`
- `skills/manifest.json` — Manifest recording source paths, licenses, versions, compatibility notes, and generated-file checksums

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

Each `--skill` value must be a non-empty, exact Skill name. Repeat the option to
select multiple Skills; omit it entirely to install all Skills.

The default set currently installs 90 production-ready Skills. `docs-canvas` is
listed in `--list` but excluded because its upstream workflow is still a
placeholder. To evaluate its host-specific fallback and bundled smoke artifact,
select it explicitly with `--skill docs-canvas`; the installer prints an
experimental warning.

Main options:

- `--dry-run` — Show planned operations without writing files
- `--force` — Move conflicting Skills to timestamped backups before updating
- `--scope user|project` — Select the installation scope
- `--target claude|codex|both` — Select the target host

By default, an existing Skill with the same name is not overwritten and is reported as `skipped`. Identical installations are reported as `unchanged`.

Backups are kept outside active Skill discovery directories:

- Claude Code: `~/.claude/skill-backups/` for user installs and `<project>/.claude/skill-backups/` for project installs. `CLAUDE_CONFIG_DIR` replaces `~/.claude` when set.
- Codex: `~/.codex/skill-backups/` for user installs and `<project>/.agents/skill-backups/` for project installs. `CODEX_HOME` replaces `~/.codex` when set.

Forced updates are staged on the destination filesystem. If activation fails after the existing Skill is backed up, the installer restores that original Skill automatically and removes its temporary staging directory.

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

Names are normalized to lowercase kebab-case. The converter parses frontmatter with
PyYAML, rejects duplicate or unknown fields and invalid values, and emits valid YAML.
The known legacy form of an unquoted plain `description` containing a colon is
normalized explicitly. Support trees reject symlinks, secrets, caches, and dependency
directories. A declared MIT license and a matching upstream `LICENSE` file are required.

## Compatibility boundaries

Skill instructions and local resources can be converted, but Cursor-specific runtime capabilities are not bundled.

- Automated repetition and stop interception that depend on Cursor hooks do not run automatically in Claude Code or Codex.
- Skills that use Cursor Canvas include a fallback to a standalone HTML artifact when Canvas is unavailable.
- Skills that use MCP require the corresponding MCP server to be configured separately in Claude Code or Codex.
- Skills that operate the Cursor SDK or Cursor Cloud Agents still require Cursor credentials and services.
- Named Cursor subagents are not registered automatically. Their original definitions are bundled under `references/cursor-agents/` for use as prompts with an available general-purpose subagent.
- `setup-pstack` writes a shared per-host Markdown file. The host does not load it as configuration; converted pstack Skills read it explicitly when invoked and use only model identifiers accepted by that host.

Each converted Skill also starts with a compatibility note that prevents unavailable host capabilities from being reported as executed. See `skills/manifest.json` for per-Skill constraints.

## Regeneration

Fetch or update the source plugins, then run the builder:

```bash
git clone https://github.com/cursor/plugins.git ref/plugins
python3 -m pip install --requirement requirements.txt
python3 scripts/build_skills.py
python3 scripts/validate_generated.py skills
```

The `ref/` directory is not included in this repository. If `ref/plugins` already exists, update that repository before converting. The builder discovers only the `skills` directories declared by `plugin.json` and deterministically regenerates `skills/`.

The manifest and its sidecar checksum protect the generated tree. A normal rebuild
refuses modified, added, or missing generated files. Review and preserve local work;
use `--force` only when intentionally replacing a recognized generated tree. Output
activation uses a rollback-safe rename. CI rebuilds both host distributions from the
pinned upstream revision and compares them with the committed tree.

## License

The repository-authored installer, converter, and documentation are available under the [MIT License](LICENSE).

Converted Skills retain their upstream MIT licenses. The applicable source license is bundled in each Skill's `LICENSE` file, with copyright notices belonging to Cursor, Lauren Tan, or Anysphere, Inc. The root license does not replace those notices. Keep each corresponding Skill `LICENSE` file when redistributing converted content.
