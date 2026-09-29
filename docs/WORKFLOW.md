# potato-skills Development Workflow

**Last updated:** 2026-09-29
**Applies to:** `takurot/potato-skills`

This document defines how to update the Cursor source snapshot, convert Skills for
Claude Code and Codex, change the installer, and publish repository changes without
losing upstream attribution or claiming unsupported host behavior.

## 1. Sources of truth

Review these sources before making a change:

1. [GitHub Issues](https://github.com/takurot/potato-skills/issues) for scope,
   priority, dependencies, and acceptance criteria.
2. [`README.md`](../README.md) for the public installation and compatibility
   contract.
3. [`skills/manifest.json`](../skills/manifest.json) for the converted Skill
   inventory, upstream paths, plugin versions, compatibility notes, and source
   revision.
4. [`scripts/build_skills.py`](../scripts/build_skills.py) for conversion policy.
5. [`install.sh`](../install.sh) for installation, conflict, and backup behavior.
6. The exact `cursor/plugins` revision recorded by `source_revision` when the
   behavior comes from upstream content.

Do not treat generated files as the only source of truth. A manual edit under
`skills/` will be lost the next time the converter runs unless the corresponding
conversion rule or upstream source is changed.

When an Issue, README statement, generated file, and implementation disagree,
verify the live behavior and update the affected contract in the same change. Do
not report an unavailable hook, MCP server, model, subagent, or Cursor service as
working on Claude Code or Codex.

## 2. Choose and scope the work

Inspect the Issue and current repository state:

```bash
gh issue view <ISSUE> \
  --repo takurot/potato-skills \
  --json number,title,body,comments,labels,state,url
git status --short --branch
git log -5 --oneline --decorate
```

Before implementation, record:

- the user-visible problem and acceptance criteria;
- whether the change belongs to the converter, installer, generated output, or
  documentation;
- the affected host or hosts;
- the upstream plugin and source files involved;
- compatibility and licensing risks;
- the smallest regression proof that will fail before the fix;
- behavior that cannot be verified locally.

Keep one independently reviewable concern per branch. Split unrelated installer,
converter, Skill-content, and documentation changes into separate Issues or
branches.

## 3. Start safely

Synchronize without discarding local work:

```bash
git switch main
git pull --ff-only
git status --short --branch
git switch -c issue/<ISSUE>-<short-description>
```

Use `docs/<topic>` for documentation-only work that has no Issue. Branch suffixes
should use short lowercase ASCII words separated by hyphens.

Treat modified, untracked, and ignored files as user-owned unless the task clearly
created them. Never use `git reset --hard`, broad `git clean`, or a checkout that
overwrites unrelated work. Use an isolated worktree when the current checkout
contains overlapping changes.

The following directories are intentionally not tracked:

- `ref/` — local upstream checkout;
- `temp/` — local audit artifacts and Issue drafts;
- Python bytecode and cache directories.

## 4. Change categories

### 4.1 Converter changes

Change [`scripts/build_skills.py`](../scripts/build_skills.py) when a rule must
apply reproducibly to generated distributions. Typical examples are:

- frontmatter normalization;
- host-specific paths and controls;
- invocation policy mapping;
- compatibility notices;
- selection of referenced agents and support files;
- manifest and provenance generation;
- license validation.

Use fail-closed behavior at the conversion boundary. Reject malformed manifests,
ambiguous names, unsafe paths, missing required licenses, unsupported syntax, and
output directories that are not positively identified as generated content.

Apply host adaptations to every resource the Skill executes or asks the agent to
read. Updating only the top-level `SKILL.md` is insufficient when references,
playbooks, scripts, or agent prompts retain Cursor-only instructions.

### 4.2 Upstream refreshes

Clone or update the ignored upstream checkout, then pin the exact revision used:

```bash
git clone https://github.com/cursor/plugins.git ref/plugins
git -C ref/plugins fetch origin
git -C ref/plugins switch main
git -C ref/plugins pull --ff-only
git -C ref/plugins rev-parse HEAD
```

If `ref/plugins` already exists, do not clone over it. Review upstream changes
before regenerating, including plugin manifests, licenses, hooks, agents, MCP
requirements, scripts, symlinks, and newly declared or removed Skills.

The converter must use only Skill directories declared by each plugin manifest.
MCP-only plugins are not converted into Skills. Duplicate names require an
explicit, documented selection rule rather than first-match behavior.

Run the canonical regeneration only after the source revision is confirmed:

```bash
python3 -m pip install --requirement requirements.txt
python3 scripts/build_skills.py --source ref/plugins --output skills
python3 scripts/validate_generated.py skills
```

If the checksum policy reports local generated changes, inspect and preserve them.
Use `--force` only when intentionally replacing that recognized generated tree.

Review the manifest revision, Skill count, additions, removals, and every changed
license before accepting the generated diff.

### 4.3 Installer changes

Keep the installer compatible with the shell versions documented by the project.
The installer must:

- distinguish an omitted selector from an invalid or empty selector;
- avoid whitespace splitting and pathname expansion for Skill names;
- default to preserving existing installations;
- keep backups outside active Skill discovery directories;
- restore the original installation if replacement fails;
- clean staging directories after success, failure, or interruption;
- reject unknown targets, scopes, Skills, unsafe destinations, and dangling
  destination links;
- make `--dry-run` describe the same decisions the real operation would take.

Test installation against temporary project directories. Do not use a developer's
real `~/.claude`, `~/.codex`, `.claude`, or `.agents` directories as test targets.

### 4.4 Skill compatibility changes

For every affected Skill, evaluate:

1. **Trigger:** Is the description specific enough to load at the right time?
2. **Actionability:** Can the target host perform each required step?
3. **Dependencies:** Are referenced Skills, tools, agents, MCP servers, scripts,
   and assets present or explicitly declared as external?
4. **Lifecycle:** Do continuation, cancellation, logging, and cleanup work without
   Cursor hooks?
5. **Configuration:** Does a written setting have a documented consumer?
6. **Safety:** Are external text, repository content, transcripts, paths, and
   command output treated as untrusted input?
7. **Evidence:** Does the Skill verify results instead of announcing success from
   intent or file creation alone?
8. **Licensing:** Is the applicable upstream license bundled and accurately
   represented?

If a Cursor capability has no equivalent, provide a bounded manual fallback or
mark the Skill unavailable/experimental for that host. A compatibility preface
does not repair contradictory instructions later in the Skill.

## 5. Test-first workflow

For bug fixes and behavior changes, use Red, Green, Refactor:

1. Add the smallest fixture or command that reproduces the failure.
2. Confirm it fails for the expected reason.
3. Implement the change in the converter or installer rather than patching only
   generated output.
4. Confirm the focused test passes.
5. Regenerate both host distributions.
6. Run the full repository checks below.
7. Review the generated diff for unrelated churn.

Fixtures should use synthetic plugins and temporary output directories where
possible. Do not make tests depend on a mutable upstream checkout, a real user
configuration, a live paid model call, or network access unless the test is
explicitly marked as an opt-in integration check.

## 6. Verification gates

### 6.1 Static checks

```bash
python3 -m py_compile scripts/build_skills.py
python3 scripts/validate_generated.py skills
shellcheck install.sh
python3 -m json.tool skills/manifest.json >/dev/null
claude plugin validate skills/claude-code
```

`claude plugin validate` is useful but not sufficient: a valid wrapper manifest
does not prove that every generated Skill, referenced resource, or runtime
workflow works.

### 6.2 Inventory and generated-output checks

```bash
bash install.sh --list
find skills/codex -mindepth 1 -maxdepth 1 -type d | wc -l
find skills/claude-code/skills -mindepth 1 -maxdepth 1 -type d | wc -l
jq '.skill_count, (.skills | length)' skills/manifest.json
```

All reported counts must agree. Also verify:

- every Codex Skill has `SKILL.md` and `agents/openai.yaml`;
- every generated Skill has a non-empty name and description;
- explicit-only policy is preserved for both hosts;
- relative links resolve inside the installed Skill;
- referenced files exist and do not escape through symlinks;
- generated content contains no unapproved Cursor-only paths or commands;
- each Skill retains its applicable upstream license;
- removed upstream Skills are intentional and documented.

### 6.3 Determinism

Build twice from the same clean upstream revision into separate temporary
directories and compare them:

```bash
first_output=$(mktemp -d /tmp/potato-skills-first.XXXXXX)
second_output=$(mktemp -d /tmp/potato-skills-second.XXXXXX)
python3 scripts/build_skills.py --source ref/plugins --output "$first_output/generated"
python3 scripts/build_skills.py --source ref/plugins --output "$second_output/generated"
diff -qr "$first_output/generated" "$second_output/generated"
```

A difference is a failure. Record the upstream commit and do not describe a build
from a dirty upstream checkout as reproducible.

### 6.4 Installer behavior

At minimum, cover:

- all Skills and one selected Skill;
- Claude-only, Codex-only, and both targets;
- user and project destination mapping;
- dry run without writes;
- identical reinstall as `unchanged`;
- conflict without force as `skipped`;
- forced replacement with an out-of-discovery backup;
- empty, whitespace, repeated, and unknown selectors;
- copy, backup, and activation failures with rollback;
- spaces in project paths;
- dangling symlink destinations.

Do not count a dry run as proof that copying, backup, rollback, or activation works.

## 7. Security and license review

Treat the upstream repository as external input even when it is official.

- Validate manifest paths before reading or copying them.
- Reject path traversal and symlinks that escape the declared plugin or Skill.
- Do not copy `.env` files, credentials, caches, package dependency trees, or
  unrelated build artifacts.
- Pass external values as data, not interpolated shell commands.
- Never include tokens, private transcript content, or local absolute paths in
  generated output, fixtures, logs, commits, or Issues.
- Do not silently assign MIT to content whose license is missing, different, or
  unclear. Stop and resolve the license before distribution.
- Preserve upstream copyright and license files with converted content.
- Review scripts bundled inside Skills before distribution; conversion does not
  make executable code trusted.

If a security or licensing condition cannot be verified, fail closed and document
the unresolved condition in the Issue.

## 8. Documentation synchronization

Update documentation in the same change when behavior changes:

| Change | Required synchronization |
| --- | --- |
| Installer option, destination, conflict, or backup behavior | `README.md`, `README_JP.md`, installer help, tests |
| Conversion policy or supported field | Both READMEs, manifest expectations, tests |
| Skill count or source revision | Generated manifest and relevant README text |
| Compatibility boundary | Both READMEs, affected Skill notes, evaluation fixtures |
| License handling | Root license section, bundled licenses, converter tests |
| Development or release procedure | This workflow |

Keep `README.md` in English and `README_JP.md` in Japanese. Verify that both
versions describe the same commands and behavior.

## 9. Commit and publish

Review only the intended changes:

```bash
git status --short
git diff --check
git diff --stat
git diff
```

Confirm that ignored upstream files, temporary audit data, bytecode, secrets, and
unrelated user changes are not staged. Stage explicit paths rather than the whole
working tree when unrelated files exist.

Use an imperative Conventional Commit message, for example:

```text
fix(installer): reject empty skill selectors
docs(workflow): document conversion and verification
```

After committing:

```bash
git status --short --branch
git show --stat --oneline HEAD
git push -u origin HEAD
```

Before opening a pull request, re-read the Issue, confirm every acceptance
criterion, and state any unverified live behavior honestly. A passing static check
is not proof that a Skill executed correctly in Claude Code or Codex.

## 10. Definition of done

A change is complete only when:

- its Issue scope and acceptance criteria are satisfied;
- converter and installer changes have regression coverage;
- both host distributions are regenerated when required;
- inventory, determinism, compatibility, security, and license checks pass;
- README and workflow contracts match the implementation;
- the diff contains no unrelated or generated noise;
- the commit is pushed to its dedicated branch;
- remaining limitations and unverified runtime behavior are documented.
