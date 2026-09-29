import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_skills

ROOT = Path(__file__).resolve().parents[1]
MIT_LICENSE = (ROOT / "LICENSE").read_text(encoding="utf-8")


class ConverterFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="potato-converter-test-"
        )
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "plugins"
        self.output = self.root / "generated"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def add_plugin(
        self,
        plugin: str,
        skill: str,
        frontmatter: str | None = None,
        *,
        license_id: str = "MIT",
        license_text: str | None = MIT_LICENSE,
    ) -> Path:
        root = self.source / plugin
        manifest_directory = root / ".cursor-plugin"
        skill_directory = root / "skills" / skill
        manifest_directory.mkdir(parents=True)
        skill_directory.mkdir(parents=True)
        (manifest_directory / "plugin.json").write_text(
            json.dumps(
                {
                    "name": plugin,
                    "version": "1.0.0",
                    "license": license_id,
                    "skills": "./skills",
                }
            ),
            encoding="utf-8",
        )
        if license_text is not None:
            (root / "LICENSE").write_text(license_text, encoding="utf-8")
        if frontmatter is None:
            frontmatter = f"name: {skill}\ndescription: Test {skill} workflow"
        skill_file = skill_directory / "SKILL.md"
        skill_file.write_text(
            f"---\n{frontmatter}\n---\n\n# Test\n", encoding="utf-8"
        )
        return skill_directory


class FrontmatterTests(ConverterFixture):
    def test_supported_boolean_spellings_and_inline_comments(self) -> None:
        cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("on", True),
            ("On", True),
            ("ON", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("no", False),
            ("No", False),
            ("NO", False),
            ("off", False),
            ("Off", False),
            ("OFF", False),
            ("0", False),
        ]
        expected: dict[str, bool] = {}
        for index, (value, boolean) in enumerate(cases):
            name = f"skill-{index:02d}"
            self.add_plugin(
                f"plugin-{index:02d}",
                name,
                "\n".join(
                    [
                        f"name: {name}",
                        'description: "Description with # text" # inline comment',
                        f"disable-model-invocation: {value} # policy",
                    ]
                ),
            )
            expected[name] = boolean

        skills = build_skills.load_skills(self.source)

        self.assertEqual(
            {skill.name: skill.explicit_only for skill in skills}, expected
        )
        self.assertTrue(all(skill.description == "Description with # text" for skill in skills))

    def test_multiline_descriptions_are_parsed_by_yaml(self) -> None:
        self.add_plugin(
            "folded",
            "folded",
            "name: folded\ndescription: >-\n  First line\n  second line",
        )
        self.add_plugin(
            "literal",
            "literal",
            "name: literal\ndescription: |-\n  First line\n  second line",
        )

        skills = {skill.name: skill for skill in build_skills.load_skills(self.source)}

        self.assertEqual(skills["folded"].description, "First line second line")
        self.assertEqual(skills["literal"].description, "First line\nsecond line")

    def test_known_metadata_is_accepted_but_unknown_fields_fail_closed(self) -> None:
        self.add_plugin(
            "known",
            "known",
            "name: known\ndescription: Known metadata\nicon: star\npaths: ['**/*.py']",
        )
        build_skills.load_skills(self.source)
        self.add_plugin(
            "unknown",
            "unknown",
            "name: unknown\ndescription: Unknown metadata\nfuture-policy: enabled",
        )

        with self.assertRaisesRegex(ValueError, "unsupported frontmatter field"):
            build_skills.load_skills(self.source)

    def test_duplicate_yaml_key_and_malformed_frontmatter_are_rejected(self) -> None:
        self.add_plugin(
            "duplicate-key",
            "duplicate-key",
            "name: duplicate-key\nname: other\ndescription: Duplicate key",
        )
        with self.assertRaisesRegex(ValueError, "duplicate frontmatter field"):
            build_skills.load_skills(self.source)

        self.source = self.root / "other-plugins"
        directory = self.add_plugin("malformed", "malformed")
        (directory / "SKILL.md").write_text(
            "---\nname: [unterminated\ndescription: Broken\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "invalid YAML frontmatter"):
            build_skills.load_skills(self.source)

    def test_duplicate_normalized_skill_names_are_rejected(self) -> None:
        self.add_plugin("first", "same")
        self.add_plugin("second", "same")

        with self.assertRaisesRegex(ValueError, "duplicate skill name"):
            build_skills.load_skills(self.source)

    def test_plain_description_with_colon_is_supported_explicitly(self) -> None:
        self.add_plugin(
            "colon",
            "colon",
            "name: colon\ndescription: Compatibility pass: scan and validate",
        )

        skill = build_skills.load_skills(self.source)[0]

        self.assertEqual(skill.description, "Compatibility pass: scan and validate")

    def test_declared_skill_path_cannot_escape_plugin(self) -> None:
        directory = self.add_plugin("escape", "escape")
        manifest_file = directory.parents[1] / ".cursor-plugin" / "plugin.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["skills"] = "../../outside"
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "escapes plugin root"):
            build_skills.load_skills(self.source)


class LicenseAndSupportPolicyTests(ConverterFixture):
    def test_verified_manifest_license_is_propagated(self) -> None:
        self.add_plugin("licensed", "licensed")

        build_skills.build(self.source, self.output)

        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["skills"][0]["license"], "MIT")
        codex_skill = (self.output / "codex/licensed/SKILL.md").read_text()
        self.assertIn("license: MIT", codex_skill)
        self.assertEqual(
            (self.output / "codex/licensed/LICENSE").read_text(), MIT_LICENSE
        )

    def test_missing_or_incompatible_license_fails_closed(self) -> None:
        self.add_plugin("missing", "missing", license_text=None)
        with self.assertRaisesRegex(ValueError, "missing LICENSE"):
            build_skills.load_skills(self.source)

        self.source = self.root / "other-plugins"
        self.add_plugin(
            "apache", "apache", license_id="Apache-2.0", license_text="Apache License"
        )
        with self.assertRaisesRegex(ValueError, "unsupported license"):
            build_skills.load_skills(self.source)

    def test_secret_cache_dependency_and_symlink_support_files_are_rejected(self) -> None:
        cases = [
            ("secret", ".env"),
            ("credentials", "credentials.json"),
            ("cache", "__pycache__/state.pyc"),
            ("dependency", "node_modules/pkg/index.js"),
        ]
        for label, relative in cases:
            with self.subTest(label=label):
                self.source = self.root / f"plugins-{label}"
                directory = self.add_plugin(label, label)
                path = directory / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("unsafe", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "forbidden support path"):
                    build_skills.build(self.source, self.root / f"output-{label}")

        self.source = self.root / "plugins-symlink"
        directory = self.add_plugin("symlink", "symlink")
        (directory / "escape").symlink_to(self.root / "outside")
        with self.assertRaisesRegex(ValueError, "symlink"):
            build_skills.build(self.source, self.root / "output-symlink")


class OutputSafetyTests(ConverterFixture):
    def setUp(self) -> None:
        super().setUp()
        self.add_plugin("safe", "safe")

    def test_modified_or_extra_output_requires_force(self) -> None:
        build_skills.build(self.source, self.output)
        skill_file = self.output / "codex/safe/SKILL.md"
        skill_file.write_text("local modification\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "locally modified"):
            build_skills.build(self.source, self.output)

        build_skills.build(self.source, self.output, force=True)
        manifest_file = self.output / "manifest.json"
        manifest_file.write_text(
            manifest_file.read_text(encoding="utf-8").replace(
                '"schema_version": 2', '"schema_version": 999'
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "locally modified"):
            build_skills.build(self.source, self.output)

        build_skills.build(self.source, self.output, force=True)
        (self.output / "local-note.txt").write_text("local addition\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "locally modified"):
            build_skills.build(self.source, self.output)

    def test_activation_failure_restores_previous_generated_tree(self) -> None:
        build_skills.build(self.source, self.output)
        original_manifest = (self.output / "manifest.json").read_bytes()
        original_rename = Path.rename
        activation_failed = False

        def fail_activation(path: Path, target: Path) -> Path:
            nonlocal activation_failed
            if Path(target) == self.output.resolve() and not activation_failed:
                activation_failed = True
                raise OSError("injected activation failure")
            return original_rename(path, target)

        with mock.patch.object(Path, "rename", fail_activation):
            with self.assertRaisesRegex(OSError, "injected activation failure"):
                build_skills.build(self.source, self.output)

        self.assertEqual((self.output / "manifest.json").read_bytes(), original_manifest)
        build_skills.verify_generated_output(self.output)

    def test_symlink_output_is_rejected(self) -> None:
        target = self.root / "target"
        target.mkdir()
        link = self.root / "output-link"
        link.symlink_to(target, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "symlink output"):
            build_skills.build(self.source, link, force=True)


if __name__ == "__main__":
    unittest.main()
