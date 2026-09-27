import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = (
    "architect",
    "arena",
    "how",
    "interrogate",
    "reflect",
    "swarm",
    "why",
)


class PstackConfigTests(unittest.TestCase):
    def skill_text(self, target: str, name: str) -> str:
        root = ROOT / "skills" / target
        if target == "claude-code":
            root /= "skills"
        return (root / name / "SKILL.md").read_text()

    def test_setup_writes_explicitly_consumed_host_config(self) -> None:
        expected_paths = {
            "claude-code": "~/.claude/pstack-models.md",
            "codex": "~/.codex/pstack-models.md",
        }
        for target, config_path in expected_paths.items():
            with self.subTest(target=target):
                text = self.skill_text(target, "setup-pstack")
                self.assertIn(config_path, text)
                self.assertIn("is not loaded automatically by the host", text)
                self.assertIn("Do not construct a model identifier by editing a suffix", text)
                self.assertIn("only exact identifiers accepted by the current host", text)
                self.assertNotIn("alwaysApply", text)
                self.assertNotIn("applies to new sessions", text)

    def test_each_consumer_reads_the_same_host_config(self) -> None:
        expected_paths = {
            "claude-code": "~/.claude/pstack-models.md",
            "codex": "~/.codex/pstack-models.md",
        }
        for target, config_path in expected_paths.items():
            for name in CONSUMERS:
                with self.subTest(target=target, name=name):
                    text = self.skill_text(target, name)
                    self.assertIn(f"Read `{config_path}`", text)
                    self.assertNotIn("pstack-models.mdc", text)

    def test_fresh_generated_consumer_contract_uses_saved_role(self) -> None:
        for target, config_path in (
            ("claude-code", "~/.claude/pstack-models.md"),
            ("codex", "~/.codex/pstack-models.md"),
        ):
            setup = self.skill_text(target, "setup-pstack")
            consumer = self.skill_text(target, "swarm")
            with self.subTest(target=target):
                self.assertIn("swarm workers: inherit-parent", setup)
                self.assertIn(f"Read `{config_path}`", consumer)
                self.assertIn("`swarm workers` line", consumer)
                self.assertIn("omit `model`", consumer)


if __name__ == "__main__":
    unittest.main()
