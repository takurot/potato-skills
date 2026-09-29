import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrReviewCanvasTests(unittest.TestCase):
    def skill_text(self, target: str) -> str:
        root = ROOT / "skills" / target
        if target == "claude-code":
            root /= "skills"
        return (root / "pr-review-canvas" / "SKILL.md").read_text()

    def test_generated_workflow_aggregates_all_pages_without_key_normalization(self) -> None:
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target)
                self.assertIn(
                    "--jq '.[] | {key: .filename, value: (.patch // \"\")}'",
                    text,
                )
                self.assertIn("| jq -s 'from_entries'", text)
                self.assertNotIn('gsub("[^a-zA-Z0-9]"; "_")', text)

    def test_generated_workflow_requires_safe_original_filename_attributes(self) -> None:
        for target in ("claude-code", "codex"):
            with self.subTest(target=target):
                text = self.skill_text(target)
                self.assertIn("html.escape(filename, quote=True)", text)
                self.assertIn("The JSON key remains the exact original filename", text)

    def test_slurped_entries_preserve_large_collision_and_edge_case_fixture(self) -> None:
        entries = [
            {"key": f"src/file-{index}.ts", "value": f"patch-{index}"}
            for index in range(101)
        ]
        entries.extend(
            [
                {"key": "src/a-b.ts", "value": "dash"},
                {"key": "src/a_b.ts", "value": "underscore"},
                {"key": 'src/<script data-x="y">.ts', "value": "</script>"},
                {"key": "src/no-patch.ts", "value": ""},
            ]
        )
        ndjson = "".join(json.dumps(entry) + "\n" for entry in entries)

        result = subprocess.run(
            ["jq", "-s", "from_entries"],
            input=ndjson,
            check=True,
            capture_output=True,
            text=True,
        )
        patches = json.loads(result.stdout)

        self.assertEqual(len(patches), 105)
        self.assertEqual(patches["src/a-b.ts"], "dash")
        self.assertEqual(patches["src/a_b.ts"], "underscore")
        self.assertEqual(patches['src/<script data-x="y">.ts'], "</script>")
        self.assertEqual(patches["src/no-patch.ts"], "")


if __name__ == "__main__":
    unittest.main()
