"""Invoke the maintenance skill through isolated Codex headless mode."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

from .common import (
    EXIT_CODEX_FAILED,
    EXIT_INVALID_REVIEW,
    RoutineError,
    atomic_write_json,
    atomic_write_text,
    guidance_digest,
    read_json,
)
from .manifest import load_manifest
from .validate import build_receipt, load_report, validate_review_result, validate_snapshot_files


def codex_command(
    executable: str,
    repo_root: Path,
    run_dir: Path,
    schema_path: Path,
    result_path: Path,
    model: str,
) -> List[str]:
    return [
        executable,
        "exec",
        "--cd",
        str(repo_root.resolve()),
        "--add-dir",
        str(run_dir.resolve()),
        "--ignore-user-config",
        "--ephemeral",
        "--model",
        model,
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
    ]


def _codex_version(executable: str) -> str:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RoutineError("unable to read Codex version: {0}".format(error), EXIT_CODEX_FAILED) from error
    value = completed.stdout.strip()
    if not value:
        raise RoutineError("Codex returned an empty version", EXIT_CODEX_FAILED)
    return value


def review_with_codex(
    repo_root: Path,
    report_path: Path,
    schema_path: Path,
    model: str,
    codex_executable: str = "codex",
) -> Path:
    repo_root = repo_root.resolve()
    report_path = report_path.resolve()
    report = load_report(report_path)
    if report["status"] != "changed":
        raise RoutineError("Codex review is only valid for a changed report", EXIT_INVALID_REVIEW)
    validate_snapshot_files(report, report_path)
    manifest = load_manifest(Path(report["manifest_path"]))
    if manifest.sha256 != report["manifest_sha256"]:
        raise RoutineError("manifest changed after the source check", EXIT_INVALID_REVIEW)
    target_path = (repo_root / manifest.review_target).resolve()
    try:
        target_path.relative_to(repo_root)
    except ValueError as error:
        raise RoutineError("review target escapes repository", EXIT_INVALID_REVIEW) from error
    try:
        current_markdown = target_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RoutineError("unable to read review target: {0}".format(error), EXIT_INVALID_REVIEW) from error
    if guidance_digest(current_markdown) != report["guidance_sha256"]:
        raise RoutineError("guidance changed after the source check", EXIT_INVALID_REVIEW)

    executable = shutil.which(codex_executable) if "/" not in codex_executable else codex_executable
    if not executable:
        raise RoutineError("Codex executable not found: {0}".format(codex_executable), EXIT_CODEX_FAILED)
    run_dir = report_path.parent
    result_path = run_dir / "result.json"
    events_path = run_dir / "codex-events.jsonl"
    stderr_path = run_dir / "codex-stderr.log"
    version = _codex_version(executable)
    atomic_write_json(result_path, {"pending": True})
    prompt = (
        "Use $cupertino-taste:maintain-current-apple-guidance.\n"
        "Review the prepared report at {0}.\n"
        "The expected report SHA-256 is {1}, and the check date is {2}.\n"
        "Read every normalized source snapshot listed in it and the current review target.\n"
        "Do not fetch anything, do not edit files, and return only the schema-defined JSON result.\n"
    ).format(report_path, report["report_sha256"], report["checked_on"])
    command = codex_command(executable, repo_root, run_dir, schema_path, result_path, model)
    try:
        with events_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
            completed = subprocess.run(
                command,
                input=prompt.encode("utf-8"),
                stdout=stdout_stream,
                stderr=stderr_stream,
                cwd=str(repo_root),
                timeout=1800,
            )
    except (OSError, subprocess.SubprocessError) as error:
        raise RoutineError("Codex headless invocation failed: {0}".format(error), EXIT_CODEX_FAILED) from error
    if completed.returncode != 0:
        raise RoutineError(
            "Codex headless invocation exited {0}; see {1}".format(completed.returncode, stderr_path),
            EXIT_CODEX_FAILED,
        )
    try:
        result = read_json(result_path)
    except RoutineError as error:
        raise RoutineError("Codex did not produce valid structured output: {0}".format(error), EXIT_INVALID_REVIEW) from error
    result = validate_review_result(result, report, manifest, current_markdown)
    resulting_markdown = result["replacement_markdown"] if result["status"] == "updated" else current_markdown
    receipt = build_receipt(result, report, current_markdown, resulting_markdown, model, version)
    receipt_path = run_dir / "receipt.json"
    atomic_write_json(receipt_path, receipt)
    if result["status"] == "updated":
        atomic_write_text(target_path, resulting_markdown)
    return receipt_path
