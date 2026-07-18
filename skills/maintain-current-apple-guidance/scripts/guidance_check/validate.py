"""Validate prepared reports, Codex results, and deterministic receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .common import (
    EXIT_INVALID_REVIEW,
    RoutineError,
    canonical_json_bytes,
    guidance_digest,
    guidance_last_checked,
    read_json,
    receipt_hash,
    report_hash,
    sha256_bytes,
    validate_date,
)
from .manifest import Manifest


RESULT_KEYS = {
    "schema_version",
    "status",
    "checked_on",
    "report_sha256",
    "source_assessments",
    "changes",
    "replacement_markdown",
    "blocked_reason",
    "summary",
}
ASSESSMENT_KEYS = {"id", "normalized_sha256", "classification", "impact"}
CHANGE_KEYS = {"section", "summary", "source_ids"}
CLASSIFICATIONS = {"supports_current_guidance", "guidance_gap", "editorial_only", "blocked"}


def load_report(path: Path) -> Dict[str, Any]:
    report = read_json(path)
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise RoutineError("invalid report schema", EXIT_INVALID_REVIEW)
    if report.get("report_sha256") != report_hash(report):
        raise RoutineError("report hash does not match its content", EXIT_INVALID_REVIEW)
    if report.get("status") not in {"current", "changed", "failed"}:
        raise RoutineError("invalid report status", EXIT_INVALID_REVIEW)
    validate_date(report.get("checked_on", ""))
    if not isinstance(report.get("sources"), list) or not report["sources"]:
        raise RoutineError("report has no sources", EXIT_INVALID_REVIEW)
    return report


def validate_snapshot_files(report: Dict[str, Any], report_path: Path) -> None:
    run_dir = report_path.resolve().parent
    for source in report["sources"]:
        if source.get("status") != "ok":
            raise RoutineError("cannot review an incomplete source report", EXIT_INVALID_REVIEW)
        normalized_path = Path(source.get("normalized_path", "")).resolve()
        raw_path = Path(source.get("raw_path", "")).resolve()
        try:
            normalized_path.relative_to(run_dir / "normalized")
            raw_path.relative_to(run_dir / "raw")
        except ValueError as error:
            raise RoutineError("source snapshot path escapes its run directory", EXIT_INVALID_REVIEW) from error
        try:
            normalized = normalized_path.read_bytes()
            raw = raw_path.read_bytes()
        except OSError as error:
            raise RoutineError("unable to read source snapshot: {0}".format(error), EXIT_INVALID_REVIEW) from error
        if sha256_bytes(normalized) != source.get("normalized_sha256"):
            raise RoutineError("normalized snapshot hash mismatch for {0}".format(source.get("id")), EXIT_INVALID_REVIEW)
        if sha256_bytes(raw) != source.get("response_sha256"):
            raise RoutineError("raw snapshot hash mismatch for {0}".format(source.get("id")), EXIT_INVALID_REVIEW)


def _require_exact_keys(value: Dict[str, Any], keys: set, label: str) -> None:
    if set(value) != keys:
        raise RoutineError("{0} has missing or unknown fields".format(label), EXIT_INVALID_REVIEW)


def validate_review_result(result: Any, report: Dict[str, Any], manifest: Manifest, current_markdown: str) -> Dict[str, Any]:
    if not isinstance(result, dict):
        raise RoutineError("Codex result must be a JSON object", EXIT_INVALID_REVIEW)
    _require_exact_keys(result, RESULT_KEYS, "Codex result")
    if result["schema_version"] != 1:
        raise RoutineError("unsupported Codex result schema", EXIT_INVALID_REVIEW)
    if result["status"] not in {"current", "updated", "blocked"}:
        raise RoutineError("invalid Codex result status", EXIT_INVALID_REVIEW)
    if result["checked_on"] != report["checked_on"]:
        raise RoutineError("Codex result date does not match the prepared report", EXIT_INVALID_REVIEW)
    if result["report_sha256"] != report["report_sha256"]:
        raise RoutineError("Codex result is bound to a different report", EXIT_INVALID_REVIEW)
    if not isinstance(result["summary"], str) or not result["summary"].strip():
        raise RoutineError("Codex result summary must be nonempty", EXIT_INVALID_REVIEW)
    if not isinstance(result["blocked_reason"], str):
        raise RoutineError("blocked_reason must be a string", EXIT_INVALID_REVIEW)
    if not isinstance(result["replacement_markdown"], str):
        raise RoutineError("replacement_markdown must be a string", EXIT_INVALID_REVIEW)

    expected_sources = [source["id"] for source in report["sources"]]
    source_hashes = {source["id"]: source["normalized_sha256"] for source in report["sources"]}
    classifications: Dict[str, str] = {}
    if not isinstance(result["source_assessments"], list):
        raise RoutineError("source_assessments must be an array", EXIT_INVALID_REVIEW)
    actual_sources: List[str] = []
    for index, assessment in enumerate(result["source_assessments"]):
        if not isinstance(assessment, dict):
            raise RoutineError("source assessment must be an object", EXIT_INVALID_REVIEW)
        _require_exact_keys(assessment, ASSESSMENT_KEYS, "source_assessments[{0}]".format(index))
        source_id = assessment["id"]
        actual_sources.append(source_id)
        if source_id not in source_hashes:
            raise RoutineError("unknown reviewed source: {0!r}".format(source_id), EXIT_INVALID_REVIEW)
        if assessment["normalized_sha256"] != source_hashes[source_id]:
            raise RoutineError("reviewed hash mismatch for {0}".format(source_id), EXIT_INVALID_REVIEW)
        if assessment["classification"] not in CLASSIFICATIONS:
            raise RoutineError("invalid source classification for {0}".format(source_id), EXIT_INVALID_REVIEW)
        classifications[source_id] = assessment["classification"]
        if not isinstance(assessment["impact"], str) or not assessment["impact"].strip():
            raise RoutineError("source impact must be nonempty for {0}".format(source_id), EXIT_INVALID_REVIEW)
    if actual_sources != expected_sources:
        raise RoutineError("source assessments must cover every report source once, in manifest order", EXIT_INVALID_REVIEW)

    if not isinstance(result["changes"], list):
        raise RoutineError("changes must be an array", EXIT_INVALID_REVIEW)
    target_sections = {
        line.lstrip("#").strip()
        for line in current_markdown.splitlines()
        if line.startswith("#") and line.lstrip("#").startswith(" ")
    }
    for index, change in enumerate(result["changes"]):
        if not isinstance(change, dict):
            raise RoutineError("change must be an object", EXIT_INVALID_REVIEW)
        _require_exact_keys(change, CHANGE_KEYS, "changes[{0}]".format(index))
        if not isinstance(change["section"], str) or not change["section"].strip():
            raise RoutineError("change section must be nonempty", EXIT_INVALID_REVIEW)
        if change["section"] not in target_sections:
            raise RoutineError("change names a section that is not in the current target", EXIT_INVALID_REVIEW)
        if not isinstance(change["summary"], str) or not change["summary"].strip():
            raise RoutineError("change summary must be nonempty", EXIT_INVALID_REVIEW)
        if not isinstance(change["source_ids"], list) or not change["source_ids"]:
            raise RoutineError("change source_ids must be a nonempty array", EXIT_INVALID_REVIEW)
        if len(set(change["source_ids"])) != len(change["source_ids"]):
            raise RoutineError("change source_ids contains duplicates", EXIT_INVALID_REVIEW)
        if any(source_id not in source_hashes for source_id in change["source_ids"]):
            raise RoutineError("change references an unknown source", EXIT_INVALID_REVIEW)

    if result["status"] == "blocked":
        if not result["blocked_reason"].strip():
            raise RoutineError("blocked result must explain why", EXIT_INVALID_REVIEW)
        raise RoutineError("Codex review blocked: {0}".format(result["blocked_reason"].strip()), EXIT_INVALID_REVIEW)
    if any(item["classification"] == "blocked" for item in result["source_assessments"]):
        raise RoutineError("nonblocked result contains a blocked source assessment", EXIT_INVALID_REVIEW)
    if result["blocked_reason"]:
        raise RoutineError("nonblocked result must leave blocked_reason empty", EXIT_INVALID_REVIEW)

    replacement = result["replacement_markdown"]
    if result["status"] == "current":
        if any(classification == "guidance_gap" for classification in classifications.values()):
            raise RoutineError("current result cannot contain a guidance_gap assessment", EXIT_INVALID_REVIEW)
        if replacement or result["changes"]:
            raise RoutineError("current result must not return changes or replacement Markdown", EXIT_INVALID_REVIEW)
    else:
        gap_sources = {source_id for source_id, classification in classifications.items() if classification == "guidance_gap"}
        if not gap_sources:
            raise RoutineError("updated result requires at least one guidance_gap assessment", EXIT_INVALID_REVIEW)
        for change in result["changes"]:
            if any(source_id not in gap_sources for source_id in change["source_ids"]):
                raise RoutineError("every changed claim must cite only guidance_gap sources", EXIT_INVALID_REVIEW)
        if not replacement or not result["changes"]:
            raise RoutineError("updated result requires changes and full replacement Markdown", EXIT_INVALID_REVIEW)
        if len(replacement.encode("utf-8")) > 200_000:
            raise RoutineError("replacement Markdown exceeds size limit", EXIT_INVALID_REVIEW)
        if not replacement.startswith("# Current Apple guidance\n"):
            raise RoutineError("replacement Markdown has the wrong document heading", EXIT_INVALID_REVIEW)
        if not replacement.endswith("\n"):
            raise RoutineError("replacement Markdown must end in one newline", EXIT_INVALID_REVIEW)
        if guidance_last_checked(replacement) != report["guidance_last_checked"]:
            raise RoutineError("Codex must not update Last checked", EXIT_INVALID_REVIEW)
        if "/tutorials/data/" in replacement:
            raise RoutineError("replacement exposes an acquisition URL", EXIT_INVALID_REVIEW)
        for source in manifest.sources:
            if source.canonical_url not in replacement:
                raise RoutineError("replacement dropped canonical source link for {0}".format(source.id), EXIT_INVALID_REVIEW)
        if guidance_digest(replacement) == guidance_digest(current_markdown):
            raise RoutineError("updated result did not change the guidance", EXIT_INVALID_REVIEW)
    return result


def build_receipt(
    result: Dict[str, Any],
    report: Dict[str, Any],
    current_markdown: str,
    resulting_markdown: str,
    model: str,
    codex_version: str,
) -> Dict[str, Any]:
    receipt: Dict[str, Any] = {
        "schema_version": 1,
        "status": result["status"],
        "checked_on": report["checked_on"],
        "report_sha256": report["report_sha256"],
        "result_sha256": sha256_bytes(canonical_json_bytes(result)),
        "guidance_sha256_before": guidance_digest(current_markdown),
        "guidance_sha256_after": guidance_digest(resulting_markdown),
        "reviewed_sources": [
            {"id": item["id"], "normalized_sha256": item["normalized_sha256"]}
            for item in result["source_assessments"]
        ],
        "changed_sections": [item["section"] for item in result["changes"]],
        "model": model,
        "codex_version": codex_version,
    }
    receipt["receipt_sha256"] = receipt_hash(receipt)
    return receipt


def validate_receipt(receipt: Any, report: Dict[str, Any], current_markdown: str) -> Dict[str, Any]:
    if not isinstance(receipt, dict):
        raise RoutineError("review receipt must be an object", EXIT_INVALID_REVIEW)
    expected_keys = {
        "schema_version",
        "status",
        "checked_on",
        "report_sha256",
        "result_sha256",
        "guidance_sha256_before",
        "guidance_sha256_after",
        "reviewed_sources",
        "changed_sections",
        "model",
        "codex_version",
        "receipt_sha256",
    }
    _require_exact_keys(receipt, expected_keys, "review receipt")
    if receipt["schema_version"] != 1 or receipt["status"] not in {"current", "updated"}:
        raise RoutineError("invalid review receipt schema or status", EXIT_INVALID_REVIEW)
    if receipt["receipt_sha256"] != receipt_hash(receipt):
        raise RoutineError("review receipt hash mismatch", EXIT_INVALID_REVIEW)
    if receipt["report_sha256"] != report["report_sha256"] or receipt["checked_on"] != report["checked_on"]:
        raise RoutineError("review receipt is bound to a different run", EXIT_INVALID_REVIEW)
    if receipt["guidance_sha256_before"] != report["guidance_sha256"]:
        raise RoutineError("review receipt starts from different guidance", EXIT_INVALID_REVIEW)
    if not isinstance(receipt["model"], str) or not receipt["model"]:
        raise RoutineError("review receipt has no model identifier", EXIT_INVALID_REVIEW)
    if not isinstance(receipt["codex_version"], str) or not receipt["codex_version"]:
        raise RoutineError("review receipt has no Codex version", EXIT_INVALID_REVIEW)
    expected_sources = [
        {"id": source["id"], "normalized_sha256": source["normalized_sha256"]}
        for source in report["sources"]
    ]
    if receipt["reviewed_sources"] != expected_sources:
        raise RoutineError("review receipt does not cover the exact source set", EXIT_INVALID_REVIEW)
    if receipt["guidance_sha256_after"] != guidance_digest(current_markdown):
        raise RoutineError("guidance no longer matches the reviewed result", EXIT_INVALID_REVIEW)
    return receipt
