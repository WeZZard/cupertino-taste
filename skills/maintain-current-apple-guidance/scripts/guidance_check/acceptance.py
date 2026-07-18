"""Accept an exact prepared source set and advance the checked date."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .common import (
    EXIT_INVALID_REVIEW,
    RoutineError,
    atomic_write_json,
    atomic_write_text,
    guidance_digest,
    read_json,
    replace_guidance_date,
)
from .core import _load_baseline
from .manifest import load_manifest
from .validate import load_report, validate_receipt, validate_snapshot_files


def accept_report(repo_root: Path, report_path: Path, receipt_path: Optional[Path] = None) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    report_path = report_path.resolve()
    report = load_report(report_path)
    if report["status"] not in {"current", "changed"}:
        raise RoutineError("cannot accept a failed source report", EXIT_INVALID_REVIEW)
    validate_snapshot_files(report, report_path)
    manifest_path = Path(report["manifest_path"])
    manifest = load_manifest(manifest_path)
    if manifest.sha256 != report["manifest_sha256"]:
        raise RoutineError("manifest changed after the source check", EXIT_INVALID_REVIEW)
    baseline_path = Path(report["baseline_path"])
    baseline, baseline_sha256 = _load_baseline(baseline_path, manifest)
    if baseline_sha256 != report["baseline_sha256"]:
        raise RoutineError("baseline changed after the source check", EXIT_INVALID_REVIEW)

    target_path = (repo_root / manifest.review_target).resolve()
    try:
        target_path.relative_to(repo_root)
    except ValueError as error:
        raise RoutineError("review target escapes repository", EXIT_INVALID_REVIEW) from error
    try:
        current_markdown = target_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RoutineError("unable to read guidance target: {0}".format(error), EXIT_INVALID_REVIEW) from error

    accepted_receipt_sha256 = baseline.get("review_receipt_sha256")
    if report["status"] == "changed":
        selected_receipt = receipt_path.resolve() if receipt_path is not None else report_path.parent / "receipt.json"
        receipt = read_json(selected_receipt)
        receipt = validate_receipt(receipt, report, current_markdown)
        accepted_receipt_sha256 = receipt["receipt_sha256"]
    else:
        if guidance_digest(current_markdown) != report["guidance_sha256"]:
            raise RoutineError("guidance changed after the unchanged source check", EXIT_INVALID_REVIEW)
        accepted_by_id = {source["id"]: source for source in baseline["sources"]}
        for source in report["sources"]:
            accepted = accepted_by_id.get(source["id"])
            if accepted is None or accepted["normalized_sha256"] != source["normalized_sha256"]:
                raise RoutineError("current report is not covered by the accepted baseline", EXIT_INVALID_REVIEW)

    updated_markdown = replace_guidance_date(current_markdown, report["checked_on"])
    baseline_sources = [
        {
            "id": source["id"],
            "canonical_url": source["canonical_url"],
            "response_sha256": source["response_sha256"],
            "normalized_sha256": source["normalized_sha256"],
        }
        for source in report["sources"]
    ]
    updated_baseline: Dict[str, Any] = {
        "schema_version": 1,
        "normalizer_version": manifest.normalizer_version,
        "last_checked": report["checked_on"],
        "manifest_sha256": manifest.sha256,
        "guidance_sha256": guidance_digest(updated_markdown),
        "source_set_sha256": report["source_set_sha256"],
        "review_receipt_sha256": accepted_receipt_sha256,
        "sources": baseline_sources,
    }

    original_markdown = current_markdown
    try:
        atomic_write_text(target_path, updated_markdown)
        atomic_write_json(baseline_path, updated_baseline)
    except Exception:
        atomic_write_text(target_path, original_markdown)
        raise
    return updated_baseline
