import json
import os
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
        default_count = sum(
            entry.get("default_install", True) for entry in manifest["skills"]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("would install "), default_count)

    def test_explicit_experimental_skill_is_available_with_warning(self) -> None:
        result = self.run_installer("--skill", "docs-canvas")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("experimental", result.stdout.lower())
        self.assertEqual(result.stdout.count("would install docs-canvas "), 1)


class InstallerExperimentalTests(unittest.TestCase):
    def run_project_install(
        self, project: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(INSTALLER),
                "--target",
                "codex",
                "--scope",
                "project",
                "--project-dir",
                str(project),
                *arguments,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_default_real_install_excludes_experimental_skill(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="potato-default-install-test-"
        ) as directory:
            project = Path(directory)
            result = self.run_project_install(project)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("excluded  codex: docs-canvas", result.stdout)
            self.assertFalse((project / ".agents/skills/docs-canvas").exists())
            self.assertTrue((project / ".agents/skills/thermos/SKILL.md").is_file())

    def test_explicit_real_install_includes_experimental_skill(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="potato-explicit-install-test-"
        ) as directory:
            project = Path(directory)
            result = self.run_project_install(
                project, "--skill", "docs-canvas"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("warning: docs-canvas is experimental", result.stdout)
            self.assertTrue(
                (project / ".agents/skills/docs-canvas/SKILL.md").is_file()
            )


class InstallerRollbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="potato-installer-rollback-test-"
        )
        self.project = Path(self.temporary_directory.name) / "project with spaces"
        self.project.mkdir()
        self.skills_root = self.project / ".claude" / "skills"
        self.destination = self.skills_root / "thermos"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_installer(
        self, *arguments: str, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if extra_env:
            environment.update(extra_env)
        return subprocess.run(
            [
                "bash",
                str(INSTALLER),
                "--target",
                "claude",
                "--scope",
                "project",
                "--project-dir",
                str(self.project),
                "--skill",
                "thermos",
                *arguments,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def seed_original_skill(self) -> None:
        self.destination.mkdir(parents=True)
        (self.destination / "SKILL.md").write_text(
            "original installation\n", encoding="utf-8"
        )

    def create_fault_command(self, name: str, body: str) -> Path:
        bin_directory = self.project / "fault-bin"
        bin_directory.mkdir(exist_ok=True)
        command = bin_directory / name
        command.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        command.chmod(0o755)
        return bin_directory

    def assert_no_staging_directories(self) -> None:
        if self.skills_root.exists():
            self.assertEqual(
                list(self.skills_root.glob(".potato-skills.*")), []
            )

    def test_claude_backup_is_outside_skill_discovery(self) -> None:
        self.seed_original_skill()

        result = self.run_installer("--force")

        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list(
            (self.project / ".claude" / "skill-backups").glob(
                "thermos.backup.*"
            )
        )
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            (backups[0] / "SKILL.md").read_text(encoding="utf-8"),
            "original installation\n",
        )
        self.assertNotEqual(
            (self.destination / "SKILL.md").read_text(encoding="utf-8"),
            "original installation\n",
        )
        self.assert_no_staging_directories()

    def test_dangling_symlink_is_a_conflict(self) -> None:
        self.skills_root.mkdir(parents=True)
        self.destination.symlink_to(self.project / "missing-skill")

        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped", result.stdout)
        self.assertTrue(self.destination.is_symlink())

    def test_regular_file_is_a_conflict(self) -> None:
        self.skills_root.mkdir(parents=True)
        self.destination.write_text("not a directory\n", encoding="utf-8")

        result = self.run_installer()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped", result.stdout)
        self.assertEqual(
            self.destination.read_text(encoding="utf-8"), "not a directory\n"
        )

    def test_copy_failure_preserves_original_and_cleans_stage(self) -> None:
        self.seed_original_skill()
        bin_directory = self.create_fault_command("cp", "exit 41")

        result = self.run_installer(
            "--force",
            extra_env={"PATH": f"{bin_directory}:{os.environ['PATH']}"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            (self.destination / "SKILL.md").read_text(encoding="utf-8"),
            "original installation\n",
        )
        self.assert_no_staging_directories()

    def test_backup_failure_preserves_original_and_cleans_stage(self) -> None:
        self.seed_original_skill()
        bin_directory = self.create_fault_command("mv", "exit 42")

        result = self.run_installer(
            "--force",
            extra_env={"PATH": f"{bin_directory}:{os.environ['PATH']}"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            (self.destination / "SKILL.md").read_text(encoding="utf-8"),
            "original installation\n",
        )
        self.assert_no_staging_directories()

    def test_activation_failure_restores_original_and_cleans_stage(self) -> None:
        self.seed_original_skill()
        counter = self.project / "mv-count"
        bin_directory = self.create_fault_command(
            "mv",
            """count=0
[ ! -f "$MV_COUNT_FILE" ] || count=$(cat "$MV_COUNT_FILE")
count=$((count + 1))
printf '%s\\n' "$count" > "$MV_COUNT_FILE"
[ "$count" -ne 2 ] || exit 43
exec /bin/mv "$@"
""".strip(),
        )

        result = self.run_installer(
            "--force",
            extra_env={
                "PATH": f"{bin_directory}:{os.environ['PATH']}",
                "MV_COUNT_FILE": str(counter),
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(counter.read_text(encoding="utf-8"), "3\n")
        self.assertIn("restored", result.stderr)
        self.assertEqual(
            (self.destination / "SKILL.md").read_text(encoding="utf-8"),
            "original installation\n",
        )
        self.assert_no_staging_directories()

    def test_interruption_cleans_stage(self) -> None:
        bin_directory = self.create_fault_command(
            "cp", 'kill -TERM "$PPID"\nsleep 1\nexit 44'
        )

        result = self.run_installer(
            extra_env={"PATH": f"{bin_directory}:{os.environ['PATH']}"}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())
        self.assert_no_staging_directories()


if __name__ == "__main__":
    unittest.main()
