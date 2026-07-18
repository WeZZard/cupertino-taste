"""Offline contract tests for the current-guidance maintenance package.

Every document fixture is synthetic. These tests must not acquire network data.
"""

from __future__ import annotations

import sys
import json
import shutil
import tempfile
import unicodedata
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = REPOSITORY_ROOT / "skills" / "maintain-current-apple-guidance" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "guidance-check"
sys.path.insert(0, str(PACKAGE_PARENT))

from guidance_check.common import (  # noqa: E402
    EXIT_CHANGED,
    EXIT_INVALID_REVIEW,
    EXIT_SOURCE_CONTRACT,
    RoutineError,
    guidance_last_checked,
    read_json,
    receipt_hash,
)
from guidance_check.acceptance import accept_report  # noqa: E402
from guidance_check.cli import main as guidance_cli_main  # noqa: E402
from guidance_check.codex_runner import codex_command, review_with_codex  # noqa: E402
from guidance_check.core import prepare_check  # noqa: E402
from guidance_check.manifest import SourceSpec, load_manifest  # noqa: E402
from guidance_check.normalize import normalize_html, normalize_markdown  # noqa: E402
from guidance_check.validate import (  # noqa: E402
    build_receipt,
    load_report,
    validate_receipt,
    validate_review_result,
    validate_snapshot_files,
)


def fixture_bytes(*parts: str) -> bytes:
    return FIXTURES.joinpath(*parts).read_bytes()


def markdown_source() -> SourceSpec:
    return SourceSpec(
        id="synthetic-guide",
        canonical_url="https://developer.apple.com/design/synthetic-guide",
        fetch_url="https://developer.apple.com/tutorials/data/design/synthetic-guide.md",
        adapter="docc-markdown",
        expected_content_type="text/markdown",
        expected_identifier="/design/Synthetic/response",
        expected_title="Synthetic guide",
        affected_sections=("Synthetic section",),
    )


def html_source() -> SourceSpec:
    return SourceSpec(
        id="synthetic-html-guide",
        canonical_url="https://developer.apple.com/help/synthetic-guide",
        fetch_url="https://developer.apple.com/help/synthetic-guide",
        adapter="html-article",
        expected_content_type="text/html",
        expected_identifier="",
        expected_title="Synthetic interaction guide",
        affected_sections=("Synthetic section",),
    )


class MarkdownNormalizationTests(unittest.TestCase):
    def test_line_endings_trailing_space_and_unicode_composition_are_noise(self) -> None:
        source = markdown_source()
        base = fixture_bytes("markdown", "base.md")
        text = unicodedata.normalize("NFD", base.decode("utf-8"))
        noisy_lines = [line + (" \t" if line else "") for line in text.splitlines()]
        noisy = ("\r\n".join(noisy_lines) + "\r\n\r\n").encode("utf-8")

        self.assertEqual(normalize_markdown(base, source), normalize_markdown(noisy, source))

    def test_normalized_markdown_is_idempotent(self) -> None:
        source = markdown_source()
        normalized = normalize_markdown(fixture_bytes("markdown", "base.md"), source)

        self.assertEqual(normalized, normalize_markdown(normalized, source))

    def test_substantive_markdown_change_changes_output(self) -> None:
        source = markdown_source()

        self.assertNotEqual(
            normalize_markdown(fixture_bytes("markdown", "base.md"), source),
            normalize_markdown(fixture_bytes("markdown", "content-change.md"), source),
        )

    def test_wrong_markdown_identifier_fails_source_contract(self) -> None:
        raw = fixture_bytes("markdown", "base.md").replace(
            b"/design/Synthetic/response", b"/design/Synthetic/other"
        )

        with self.assertRaises(RoutineError) as raised:
            normalize_markdown(raw, markdown_source())

        self.assertEqual(EXIT_SOURCE_CONTRACT, raised.exception.exit_code)
        self.assertIn("expected identifier", str(raised.exception))

    def test_wrong_markdown_title_fails_source_contract(self) -> None:
        raw = fixture_bytes("markdown", "base.md").replace(
            b'"title": "Synthetic guide"', b'"title": "Other synthetic guide"'
        )

        with self.assertRaises(RoutineError) as raised:
            normalize_markdown(raw, markdown_source())

        self.assertEqual(EXIT_SOURCE_CONTRACT, raised.exception.exit_code)
        self.assertIn("expected title", str(raised.exception))

    def test_invalid_utf8_fails_source_contract(self) -> None:
        with self.assertRaises(RoutineError) as raised:
            normalize_markdown(b"\xff\xfe", markdown_source())

        self.assertEqual(EXIT_SOURCE_CONTRACT, raised.exception.exit_code)


class HtmlNormalizationTests(unittest.TestCase):
    def test_shell_text_attributes_and_formatting_are_noise(self) -> None:
        source = html_source()

        self.assertEqual(
            normalize_html(fixture_bytes("html", "base.html"), source),
            normalize_html(fixture_bytes("html", "noise-variant.html"), source),
        )

    def test_normalized_html_is_stable(self) -> None:
        source = html_source()
        first = normalize_html(fixture_bytes("html", "base.html"), source)
        second = normalize_html(fixture_bytes("html", "base.html"), source)

        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

    def test_substantive_html_change_changes_output(self) -> None:
        source = html_source()

        self.assertNotEqual(
            normalize_html(fixture_bytes("html", "base.html"), source),
            normalize_html(fixture_bytes("html", "content-change.html"), source),
        )

    def test_link_destination_change_changes_output(self) -> None:
        source = html_source()
        base = fixture_bytes("html", "base.html")
        changed = base.replace(b"/design/synthetic-details", b"/design/different-details")

        self.assertNotEqual(normalize_html(base, source), normalize_html(changed, source))

    def test_missing_article_fails_source_contract(self) -> None:
        self.assert_html_contract_failure("missing-article.html", "found 0")

    def test_duplicate_article_fails_source_contract(self) -> None:
        self.assert_html_contract_failure("duplicate-article.html", "found 2")

    def test_wrong_heading_fails_source_contract(self) -> None:
        self.assert_html_contract_failure("wrong-title.html", "expected one h1")

    def assert_html_contract_failure(self, fixture_name: str, message: str) -> None:
        with self.assertRaises(RoutineError) as raised:
            normalize_html(fixture_bytes("html", fixture_name), html_source())

        self.assertEqual(EXIT_SOURCE_CONTRACT, raised.exception.exit_code)
        self.assertIn(message, str(raised.exception))


class ManifestTests(unittest.TestCase):
    def test_valid_manifest_loads_with_stable_identity(self) -> None:
        path = FIXTURES / "manifests" / "valid.json"

        first = load_manifest(path)
        second = load_manifest(path)

        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual("synthetic-v1", first.normalizer_version)
        self.assertEqual(("synthetic-guide",), tuple(source.id for source in first.sources))
        self.assertEqual(("Synthetic section",), first.sources[0].affected_sections)

    def test_duplicate_source_id_is_rejected(self) -> None:
        with self.assertRaises(RoutineError) as raised:
            load_manifest(FIXTURES / "manifests" / "duplicate-id.json")

        self.assertIn("duplicate source id", str(raised.exception))

    def test_non_apple_fetch_url_is_rejected(self) -> None:
        with self.assertRaises(RoutineError) as raised:
            load_manifest(FIXTURES / "manifests" / "non-apple-url.json")

        self.assertIn("HTTPS developer.apple.com URL", str(raised.exception))


class PipelineValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temporary_directory.name)
        self.manifest_path = FIXTURES / "manifests" / "valid.json"
        self.manifest = load_manifest(self.manifest_path)
        self.guidance_path = self.repo_root / self.manifest.review_target
        self.guidance_path.parent.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "guidance" / "current.md", self.guidance_path)
        self.input_dir = self.repo_root / "inputs"
        self.input_dir.mkdir()
        shutil.copyfile(
            FIXTURES / "markdown" / "base.md",
            self.input_dir / "synthetic-guide.md",
        )
        self.baseline_path = self.repo_root / "baseline.json"
        self.archive_root = self.repo_root / "archive"
        self.check_result = prepare_check(
            repo_root=self.repo_root,
            manifest_path=self.manifest_path,
            baseline_path=self.baseline_path,
            archive_root=self.archive_root,
            checked_on="2026-07-18",
            input_dir=self.input_dir,
            run_id="synthetic-run",
        )
        self.report = self.check_result.report
        self.current_markdown = self.guidance_path.read_text(encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def current_review_result(self) -> dict:
        source = self.report["sources"][0]
        return {
            "schema_version": 1,
            "status": "current",
            "checked_on": self.report["checked_on"],
            "report_sha256": self.report["report_sha256"],
            "source_assessments": [
                {
                    "id": source["id"],
                    "normalized_sha256": source["normalized_sha256"],
                    "classification": "supports_current_guidance",
                    "impact": "The synthetic source supports the fixture guidance.",
                }
            ],
            "changes": [],
            "replacement_markdown": "",
            "blocked_reason": "",
            "summary": "The synthetic guidance remains current.",
        }

    def updated_review_result(self) -> dict:
        result = self.current_review_result()
        result["status"] = "updated"
        result["source_assessments"][0]["classification"] = "guidance_gap"
        result["source_assessments"][0]["impact"] = "The fixture requires a synthetic wording change."
        result["changes"] = [
            {
                "section": "Synthetic section",
                "summary": "Clarify the reversible fixture state.",
                "source_ids": ["synthetic-guide"],
            }
        ]
        result["replacement_markdown"] = self.current_markdown.replace(
            "retains a reversible", "keeps a reversible"
        )
        result["summary"] = "The synthetic guidance needs one correction."
        return result

    def write_current_receipt(self) -> Path:
        result = validate_review_result(
            self.current_review_result(), self.report, self.manifest, self.current_markdown
        )
        receipt = build_receipt(
            result,
            self.report,
            self.current_markdown,
            self.current_markdown,
            model="synthetic-model",
            codex_version="codex synthetic",
        )
        receipt_path = self.check_result.run_dir / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return receipt_path

    def test_offline_check_writes_a_hash_bound_report_and_snapshots(self) -> None:
        self.assertEqual(EXIT_CHANGED, self.check_result.exit_code)
        self.assertEqual("changed", self.report["status"])
        self.assertEqual(self.report, load_report(self.check_result.report_path))
        validate_snapshot_files(self.report, self.check_result.report_path)
        serialized_report = json.dumps(self.report, ensure_ascii=False)
        self.assertNotIn("café control", serialized_report)
        self.assertTrue(Path(self.report["sources"][0]["raw_path"]).is_file())
        self.assertTrue(Path(self.report["sources"][0]["normalized_path"]).is_file())

    def test_tampered_report_hash_is_rejected(self) -> None:
        tampered = dict(self.report)
        tampered["status"] = "current"
        tampered_path = self.check_result.run_dir / "tampered-report.json"
        tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

        with self.assertRaises(RoutineError) as raised:
            load_report(tampered_path)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)
        self.assertIn("report hash", str(raised.exception))

    def test_snapshot_hash_mismatch_is_rejected(self) -> None:
        normalized_path = Path(self.report["sources"][0]["normalized_path"])
        normalized_path.write_bytes(normalized_path.read_bytes() + b"synthetic tamper\n")

        with self.assertRaises(RoutineError) as raised:
            validate_snapshot_files(self.report, self.check_result.report_path)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)
        self.assertIn("normalized snapshot hash mismatch", str(raised.exception))

    def test_current_review_result_is_accepted(self) -> None:
        result = self.current_review_result()

        self.assertEqual(
            result,
            validate_review_result(result, self.report, self.manifest, self.current_markdown),
        )

    def test_updated_review_result_is_accepted(self) -> None:
        result = self.updated_review_result()

        self.assertEqual(
            result,
            validate_review_result(result, self.report, self.manifest, self.current_markdown),
        )

    def test_review_result_must_cover_exact_source_hash(self) -> None:
        result = self.current_review_result()
        result["source_assessments"][0]["normalized_sha256"] = "0" * 64

        with self.assertRaises(RoutineError) as raised:
            validate_review_result(result, self.report, self.manifest, self.current_markdown)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)
        self.assertIn("reviewed hash mismatch", str(raised.exception))

    def test_current_result_cannot_report_a_guidance_gap(self) -> None:
        result = self.current_review_result()
        result["source_assessments"][0]["classification"] = "guidance_gap"

        with self.assertRaises(RoutineError) as raised:
            validate_review_result(result, self.report, self.manifest, self.current_markdown)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)

    def test_updated_change_must_cite_a_guidance_gap(self) -> None:
        result = self.updated_review_result()
        result["source_assessments"][0]["classification"] = "supports_current_guidance"

        with self.assertRaises(RoutineError) as raised:
            validate_review_result(result, self.report, self.manifest, self.current_markdown)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)

    def test_receipt_is_bound_to_report_sources_and_resulting_guidance(self) -> None:
        result = validate_review_result(
            self.current_review_result(), self.report, self.manifest, self.current_markdown
        )
        receipt = build_receipt(
            result,
            self.report,
            self.current_markdown,
            self.current_markdown,
            model="synthetic-model",
            codex_version="codex synthetic",
        )

        self.assertEqual(receipt, validate_receipt(receipt, self.report, self.current_markdown))

        tampered = dict(receipt)
        tampered["reviewed_sources"] = []
        tampered["receipt_sha256"] = receipt_hash(tampered)
        with self.assertRaises(RoutineError) as raised:
            validate_receipt(tampered, self.report, self.current_markdown)

        self.assertEqual(EXIT_INVALID_REVIEW, raised.exception.exit_code)
        self.assertIn("exact source set", str(raised.exception))

    def test_codex_command_uses_exact_headless_isolation_flags(self) -> None:
        repo_root = self.repo_root / "relative" / ".."
        run_dir = self.check_result.run_dir
        schema_path = FIXTURES / "manifests" / "valid.json"
        result_path = run_dir / "synthetic-result.json"

        self.assertEqual(
            [
                "/synthetic/codex",
                "exec",
                "--cd",
                str(repo_root.resolve()),
                "--add-dir",
                str(run_dir.resolve()),
                "--ignore-user-config",
                "--ephemeral",
                "--model",
                "synthetic-model",
                "-c",
                'model_reasoning_effort="high"',
                "--sandbox",
                "read-only",
                "--output-schema",
                str(schema_path.resolve()),
                "--output-last-message",
                str(result_path.resolve()),
                "--json",
                "-",
            ],
            codex_command(
                executable="/synthetic/codex",
                repo_root=repo_root,
                run_dir=run_dir,
                schema_path=schema_path,
                result_path=result_path,
                model="synthetic-model",
            ),
        )

    def test_headless_review_invokes_qualified_skill_without_running_codex(self) -> None:
        captured = {}

        def fake_run(command, *args, **kwargs):
            if command == ["/synthetic/codex", "--version"]:
                return SimpleNamespace(stdout="codex synthetic\n", returncode=0)
            captured["command"] = command
            captured["prompt"] = kwargs["input"].decode("utf-8")
            result_path = Path(command[command.index("--output-last-message") + 1])
            result_path.write_text(json.dumps(self.current_review_result()), encoding="utf-8")
            return SimpleNamespace(returncode=0)

        schema_path = (
            REPOSITORY_ROOT
            / "skills"
            / "maintain-current-apple-guidance"
            / "references"
            / "result.schema.json"
        )
        with mock.patch(
            "guidance_check.codex_runner.shutil.which", return_value="/synthetic/codex"
        ), mock.patch("guidance_check.codex_runner.subprocess.run", side_effect=fake_run):
            receipt_path = review_with_codex(
                repo_root=self.repo_root,
                report_path=self.check_result.report_path,
                schema_path=schema_path,
                model="synthetic-model",
                codex_executable="synthetic-codex",
            )

        self.assertTrue(receipt_path.is_file())
        self.assertTrue(
            captured["prompt"].startswith(
                "Use $cupertino-taste:maintain-current-apple-guidance.\n"
            )
        )
        self.assertIn(self.report["report_sha256"], captured["prompt"])
        self.assertIn("--ignore-user-config", captured["command"])
        self.assertIn("--ephemeral", captured["command"])
        self.assertEqual("read-only", captured["command"][captured["command"].index("--sandbox") + 1])

    def test_accepting_changed_report_updates_baseline_and_checked_date(self) -> None:
        receipt_path = self.write_current_receipt()
        receipt = read_json(receipt_path)

        baseline = accept_report(
            repo_root=self.repo_root,
            report_path=self.check_result.report_path,
            receipt_path=receipt_path,
        )

        self.assertEqual(baseline, read_json(self.baseline_path))
        self.assertEqual("2026-07-18", baseline["last_checked"])
        self.assertEqual(receipt["receipt_sha256"], baseline["review_receipt_sha256"])
        self.assertEqual(self.report["source_set_sha256"], baseline["source_set_sha256"])
        self.assertEqual(
            "2026-07-18",
            guidance_last_checked(self.guidance_path.read_text(encoding="utf-8")),
        )

    def test_unchanged_composed_run_accepts_without_codex(self) -> None:
        receipt_path = self.write_current_receipt()
        accept_report(self.repo_root, self.check_result.report_path, receipt_path)

        events = []
        with mock.patch(
            "guidance_check.cli.review_with_codex",
            side_effect=AssertionError("unchanged run must not invoke Codex"),
        ) as review_mock, mock.patch(
            "guidance_check.cli._emit", side_effect=lambda value, **kwargs: events.append(value)
        ):
            exit_code = guidance_cli_main(
                [
                    "run",
                    "--repo-root",
                    str(self.repo_root),
                    "--manifest",
                    str(self.manifest_path),
                    "--baseline",
                    str(self.baseline_path),
                    "--archive-root",
                    str(self.archive_root),
                    "--checked-on",
                    "2026-07-19",
                    "--input-dir",
                    str(self.input_dir),
                    "--run-id",
                    "unchanged-run",
                    "--codex",
                    "must-not-run",
                ]
            )

        self.assertEqual(0, exit_code)
        review_mock.assert_not_called()
        self.assertEqual(["current", "accepted"], [event["status"] for event in events])
        self.assertEqual("2026-07-19", read_json(self.baseline_path)["last_checked"])
        self.assertEqual(
            "2026-07-19",
            guidance_last_checked(self.guidance_path.read_text(encoding="utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
