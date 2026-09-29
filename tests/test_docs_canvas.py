import json
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOTS = {
    "Claude Code": ROOT / "skills" / "claude-code" / "skills" / "docs-canvas",
    "Codex": ROOT / "skills" / "codex" / "docs-canvas",
}


class SmokeDocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.internal_links: set[str] = set()
        self.tags: set[str] = set()
        self.external_assets: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.tags.add(tag)
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"] or "")
        href = attributes.get("href")
        if href and href.startswith("#"):
            self.internal_links.add(href[1:])
        if tag in {"link", "script"}:
            source = attributes.get("href") or attributes.get("src")
            if source:
                self.external_assets.append(source)


class DocsCanvasReadinessTests(unittest.TestCase):
    def test_manifest_marks_docs_canvas_experimental_and_not_default(self) -> None:
        manifest = json.loads(
            (ROOT / "skills" / "manifest.json").read_text(encoding="utf-8")
        )
        entry = next(
            skill for skill in manifest["skills"] if skill["name"] == "docs-canvas"
        )

        self.assertIs(entry["experimental"], True)
        self.assertIs(entry["default_install"], False)

    def test_each_target_explains_status_and_target_specific_fallback(self) -> None:
        expected_phrases = {
            "Claude Code": "Claude Code fallback example",
            "Codex": "Codex fallback example",
        }
        for host, skill_root in TARGET_ROOTS.items():
            with self.subTest(host=host):
                skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
                status = (skill_root / "EXPERIMENTAL.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("Experimental", skill)
                self.assertIn(expected_phrases[host], skill)
                self.assertIn("Cursor Canvas example", skill)
                self.assertIn("not installed by default", status)
                if host == "Codex":
                    interface = (skill_root / "agents" / "openai.yaml").read_text(
                        encoding="utf-8"
                    )
                    self.assertIn("Experimental", interface)

    def test_bundled_smoke_artifact_is_standalone_and_navigable(self) -> None:
        for host, skill_root in TARGET_ROOTS.items():
            with self.subTest(host=host):
                artifact = (
                    skill_root / "references" / "smoke-example.html"
                ).read_text(encoding="utf-8")
                parser = SmokeDocumentParser()
                parser.feed(artifact)

                self.assertTrue(artifact.lstrip().lower().startswith("<!doctype html>"))
                self.assertIn("nav", parser.tags)
                self.assertIn("pre", parser.tags)
                self.assertIn("code", parser.tags)
                self.assertIn("svg", parser.tags)
                self.assertIn("references", parser.ids)
                self.assertTrue(parser.internal_links)
                self.assertTrue(parser.internal_links <= parser.ids)
                self.assertEqual(parser.external_assets, [])


if __name__ == "__main__":
    unittest.main()
