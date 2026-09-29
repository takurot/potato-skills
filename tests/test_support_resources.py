import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UNSUPPORTED_CURSOR_PATHS = (
    "~/.cursor/projects",
    ".cursor/hooks",
    ".cursor/skills",
    "~/.cursor/plugins",
)
CURSOR_DEVELOPMENT_ALLOWLIST = {"create-plugin-scaffold", "cursor-sdk"}


class SupportResourceAdaptationTests(unittest.TestCase):
    def skill_root(self, target: str, name: str) -> Path:
        root = ROOT / "skills" / target
        if target == "claude-code":
            root /= "skills"
        return root / name

    def test_continual_learning_uses_host_state_and_bounded_transcript_source(self) -> None:
        for target, state_root in (
            ("claude-code", ".claude"),
            ("codex", ".codex"),
        ):
            path = (
                self.skill_root(target, "continual-learning")
                / "references"
                / "cursor-agents"
                / "agents-memory-updater.md"
            )
            text = path.read_text()
            with self.subTest(target=target):
                self.assertIn("explicitly exposes a transcript source for the current workspace", text)
                self.assertIn(f"{state_root}/continual-learning/index.json", text)
                self.assertNotIn("~/.cursor/projects", text)
                self.assertNotIn(".cursor/hooks", text)

    def test_reflect_reviewers_use_target_skill_roots(self) -> None:
        for target, expected in (
            ("claude-code", "~/.claude/skills/"),
            ("codex", "~/.codex/skills/"),
        ):
            references = self.skill_root(target, "reflect") / "references"
            for path in references.glob("*-reviewer.md"):
                with self.subTest(target=target, file=path.name):
                    text = path.read_text()
                    self.assertIn(expected, text)
                    self.assertNotIn(".cursor/skills", text)
                    self.assertNotIn("~/.cursor/plugins", text)

    def test_worktree_audit_uses_explicit_transcript_directory(self) -> None:
        for target in ("claude-code", "codex"):
            path = (
                self.skill_root(target, "poteto-mode")
                / "scripts"
                / "worktree-audit.sh"
            )
            text = path.read_text()
            with self.subTest(target=target):
                self.assertIn("POTATO_TRANSCRIPTS_DIR", text)
                self.assertNotIn("$HOME/.cursor", text)

    def test_portable_playbooks_do_not_scan_cursor_project_transcripts(self) -> None:
        for target in ("claude-code", "codex"):
            playbooks = self.skill_root(target, "poteto-mode") / "playbooks"
            for name in ("session-pickup.md", "eval.md"):
                text = (playbooks / name).read_text()
                with self.subTest(target=target, file=name):
                    self.assertIn("active host explicitly exposes", text)
                    self.assertNotIn("~/.cursor/projects", text)

    def test_generated_trees_allow_cursor_paths_only_for_cursor_development(self) -> None:
        for target in ("claude-code", "codex"):
            root = ROOT / "skills" / target
            if target == "claude-code":
                root /= "skills"
            failures: list[str] = []
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text()
                except UnicodeDecodeError:
                    continue
                skill_name = path.relative_to(root).parts[0]
                if skill_name in CURSOR_DEVELOPMENT_ALLOWLIST:
                    continue
                for marker in UNSUPPORTED_CURSOR_PATHS:
                    if marker in text:
                        failures.append(f"{path.relative_to(root)}: {marker}")
            self.assertEqual(failures, [], f"{target}: unsupported Cursor paths")


if __name__ == "__main__":
    unittest.main()
