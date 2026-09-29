import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HooklessSkillTests(unittest.TestCase):
    def skill_text(self, target: str, name: str) -> str:
        root = ROOT / "skills" / target
        if target == "claude-code":
            root /= "skills"
        return (root / name / "SKILL.md").read_text()

    def test_ralph_loop_exposes_manual_fallback_for_each_host(self) -> None:
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target, "ralph-loop")
                self.assertIn("Automatic continuation is unavailable", text)
                self.assertIn("manual iteration", text)
                self.assertNotIn("Confirm to the user that the Ralph loop is active", text)
                self.assertNotIn("The stop hook automatically intercepts", text)

    def test_ralph_help_describes_host_limit_instead_of_active_hook(self) -> None:
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target, "ralph-loop-help")
                self.assertIn("On this host, each later iteration requires", text)
                self.assertNotIn("Stop hook intercepts exit and feeds", text)
                self.assertNotIn("Ralph runs indefinitely", text)

    def test_cancel_ralph_calls_state_manual(self) -> None:
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target, "cancel-ralph")
                self.assertIn("saved manual Ralph state", text)
                self.assertNotIn("active Ralph loop", text)

    def test_advisor_does_not_promise_hook_updates_or_nudges(self) -> None:
        forbidden = (
            "The plugin's hooks fill in",
            "the hooks re-fill",
            "the hooks also append it",
            "the plugin's `stop` hook posts",
        )
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target, "advisor")
                self.assertIn("Automatic checkpoint and end-of-turn nudge hooks are unavailable", text)
                self.assertIn("Update `consults` and `last_consult_at` manually", text)
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
