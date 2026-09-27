import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"


class InstallerSelectionTests(unittest.TestCase):
    def run_installer(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="potato-installer-test-") as project:
            return subprocess.run(
                [
                    "bash",
                    str(INSTALLER),
                    "--target",
                    "codex",
                    "--scope",
                    "project",
                    "--project-dir",
                    project,
                    "--dry-run",
                    *arguments,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

    def test_rejects_empty_explicit_skill(self) -> None:
        result = self.run_installer("--skill", "")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--skill requires a non-empty value", result.stderr)
        self.assertNotIn("would install", result.stdout)

    def test_rejects_whitespace_skill_as_one_invalid_name(self) -> None:
        result = self.run_installer("--skill", "thermos tdd")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown skill: thermos tdd", result.stderr)
        self.assertNotIn("unknown skill: thermos\n", result.stderr)

    def test_repeated_skill_is_installed_once(self) -> None:
        result = self.run_installer(
            "--skill", "thermos", "--skill", "thermos"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("would install thermos "), 1)

    def test_rejects_unknown_skill(self) -> None:
        result = self.run_installer("--skill", "not-a-potato-skill")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown skill: not-a-potato-skill", result.stderr)

    def test_selects_one_valid_skill(self) -> None:
        result = self.run_installer("--skill", "thermos")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("would install "), 1)
        self.assertIn("would install thermos ", result.stdout)

    def test_omitting_skill_selects_every_manifest_entry(self) -> None:
        result = self.run_installer()
        manifest = json.loads((ROOT / "skills" / "manifest.json").read_text())

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.count("would install "), manifest["skill_count"]
        )


if __name__ == "__main__":
    unittest.main()
