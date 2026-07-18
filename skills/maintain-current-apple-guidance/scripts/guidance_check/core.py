"""Prepare a complete source bundle and compare it with the accepted baseline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .acquire import acquire_source
from .common import (
    EXIT_CHANGED,
    EXIT_CURRENT,
    EXIT_FETCH_FAILED,
    EXIT_INVALID_INPUT,
    EXIT_SOURCE_CONTRACT,
    RoutineError,
    atomic_write_json,
    canonical_json_bytes,
    guidance_digest,
    guidance_last_checked,
    read_json,
    report_hash,
    sha256_bytes,
    sha256_json,
    utc_run_id,
    validate_date,
)
from .manifest import Manifest, load_manifest


@dataclass(frozen=True)
class CheckResult:
    report: Dict[str, Any]
    report_path: Path
    run_dir: Path
    exit_code: int


def _load_baseline(path: Path, manifest: Manifest) -> Tuple[Dict[str, Any], str]:
    if not path.exists():
        baseline: Dict[str, Any] = {
            "schema_version": 1,
            "normalizer_version": manifest.normalizer_version,
            "last_checked": None,
            "manifest_sha256": None,
            "guidance_sha256": None,
            "source_set_sha256": None,
            "review_receipt_sha256": None,
            "sources": [],
        }
        return baseline, sha256_json(baseline)
    baseline = read_json(path)
    if not isinstance(baseline, dict):
        raise RoutineError("baseline root must be an object")
    expected_keys = {
        "schema_version",
        "normalizer_version",
        "last_checked",
        "manifest_sha256",
        "guidance_sha256",
        "source_set_sha256",
        "review_receipt_sha256",
        "sources",
    }
    if set(baseline) != expected_keys:
        raise RoutineError("baseline keys differ from schema")
    if baseline["schema_version"] != 1:
        raise RoutineError("unsupported baseline schema_version")
    if baseline["normalizer_version"] != manifest.normalizer_version:
        raise RoutineError(
            "baseline normalizer {0!r} does not match manifest {1!r}; migrate deliberately".format(
                baseline["normalizer_version"], manifest.normalizer_version
            )
        )
    if baseline["last_checked"] is not None:
        validate_date(baseline["last_checked"])
    if not isinstance(baseline["sources"], list):
        raise RoutineError("baseline sources must be an array")
    seen = set()
    for item in baseline["sources"]:
        if not isinstance(item, dict) or set(item) != {"id", "canonical_url", "response_sha256", "normalized_sha256"}:
            raise RoutineError("invalid baseline source record")
        if item["id"] in seen:
            raise RoutineError("duplicate baseline source id: {0}".format(item["id"]))
        seen.add(item["id"])
    return baseline, sha256_bytes(canonical_json_bytes(baseline))


def _change_class(current: Dict[str, Any], accepted: Optional[Dict[str, Any]]) -> str:
    if accepted is None:
        return "content"
    if current["canonical_url"] != accepted["canonical_url"]:
        return "content"
    if current["normalized_sha256"] != accepted["normalized_sha256"]:
        return "content"
    if current["response_sha256"] != accepted["response_sha256"]:
        return "representation_only"
    return "none"


def _write_report(run_dir: Path, body: Dict[str, Any]) -> Path:
    report = dict(body)
    report["report_sha256"] = report_hash(report)
    report_path = run_dir / "report.json"
    atomic_write_json(report_path, report)
    return report_path


def prepare_check(
    repo_root: Path,
    manifest_path: Path,
    baseline_path: Path,
    archive_root: Path,
    checked_on: str,
    input_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
    timeout: float = 20.0,
    retries: int = 2,
) -> CheckResult:
    repo_root = repo_root.resolve()
    checked_on = validate_date(checked_on)
    manifest = load_manifest(manifest_path)
    baseline, baseline_sha256 = _load_baseline(baseline_path, manifest)
    target_path = (repo_root / manifest.review_target).resolve()
    try:
        target_path.relative_to(repo_root)
    except ValueError as error:
        raise RoutineError("review target escapes repository") from error
    try:
        guidance_markdown = target_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RoutineError("unable to read guidance target {0}: {1}".format(target_path, error)) from error

    selected_run_id = run_id or utc_run_id()
    run_dir = (archive_root.resolve() / "runs" / selected_run_id)
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise RoutineError("run directory already exists: {0}".format(run_dir)) from error
    except OSError as error:
        raise RoutineError("unable to create run directory {0}: {1}".format(run_dir, error)) from error

    accepted_by_id = {
        item["id"]: item
        for item in baseline["sources"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    source_records: List[Dict[str, Any]] = []
    error_exit_code = 0
    for source in manifest.sources:
        try:
            record = acquire_source(
                source,
                manifest.max_response_bytes,
                run_dir,
                input_dir=input_dir,
                timeout=timeout,
                retries=retries,
            )
            record["status"] = "ok"
            record["change_class"] = _change_class(record, accepted_by_id.get(source.id))
        except RoutineError as error:
            record = {
                "id": source.id,
                "canonical_url": source.canonical_url,
                "fetch_url": source.fetch_url,
                "adapter": source.adapter,
                "affected_sections": list(source.affected_sections),
                "status": "error",
                "error": str(error),
                "error_exit_code": error.exit_code,
            }
            if error_exit_code == 0 or error.exit_code == EXIT_SOURCE_CONTRACT:
                error_exit_code = error.exit_code
        source_records.append(record)

    complete_hashes = {
        record["id"]: record["normalized_sha256"]
        for record in source_records
        if record["status"] == "ok"
    }
    source_set_sha256 = sha256_json(complete_hashes) if len(complete_hashes) == len(manifest.sources) else None
    manifest_changed = baseline.get("manifest_sha256") != manifest.sha256
    if error_exit_code:
        status = "failed"
        exit_code = error_exit_code if error_exit_code in {EXIT_FETCH_FAILED, EXIT_SOURCE_CONTRACT} else EXIT_INVALID_INPUT
    elif manifest_changed or any(record["change_class"] == "content" for record in source_records):
        status = "changed"
        exit_code = EXIT_CHANGED
    else:
        status = "current"
        exit_code = EXIT_CURRENT

    report: Dict[str, Any] = {
        "schema_version": 1,
        "normalizer_version": manifest.normalizer_version,
        "checked_on": checked_on,
        "status": status,
        "manifest_path": str(manifest.path),
        "manifest_sha256": manifest.sha256,
        "manifest_changed": manifest_changed,
        "baseline_path": str(baseline_path.resolve()),
        "baseline_sha256": baseline_sha256,
        "previous_source_set_sha256": baseline.get("source_set_sha256"),
        "source_set_sha256": source_set_sha256,
        "review_target": manifest.review_target,
        "guidance_sha256": guidance_digest(guidance_markdown),
        "guidance_last_checked": guidance_last_checked(guidance_markdown),
        "sources": source_records,
    }
    report_path = _write_report(run_dir, report)
    report = read_json(report_path)
    return CheckResult(report=report, report_path=report_path, run_dir=run_dir, exit_code=exit_code)
