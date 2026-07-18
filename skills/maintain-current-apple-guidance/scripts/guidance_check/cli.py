"""Command-line interface for check, review, accept, and composed runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .acceptance import accept_report
from .codex_runner import review_with_codex
from .common import (
    EXIT_CHANGED,
    EXIT_SOFTWARE,
    RoutineError,
    default_archive_root,
    repository_root,
    utc_date,
)
from .core import CheckResult, prepare_check


SKILL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = SKILL_ROOT / "data" / "sources.json"
DEFAULT_BASELINE = SKILL_ROOT / "data" / "baseline.json"
DEFAULT_SCHEMA = SKILL_ROOT / "references" / "result.schema.json"


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _emit(value: Dict[str, Any], stream=sys.stdout) -> None:  # type: ignore[assignment]
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    stream.flush()


def _add_repository_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=_path, default=repository_root(), help="repository root")


def _add_check_arguments(parser: argparse.ArgumentParser) -> None:
    _add_repository_argument(parser)
    parser.add_argument("--manifest", type=_path, default=DEFAULT_MANIFEST, help="versioned source manifest")
    parser.add_argument("--baseline", type=_path, default=DEFAULT_BASELINE, help="accepted hash baseline")
    parser.add_argument("--archive-root", type=_path, default=default_archive_root(), help="private run archive")
    parser.add_argument("--checked-on", default=utc_date(), help="check date in UTC, YYYY-MM-DD")
    parser.add_argument("--input-dir", type=_path, help="offline source directory for synthetic tests")
    parser.add_argument("--run-id", help="explicit private run directory name")
    parser.add_argument("--timeout", type=float, default=20.0, help="per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="retry count for transient fetch failures")


def _add_review_arguments(parser: argparse.ArgumentParser) -> None:
    _add_repository_argument(parser)
    parser.add_argument("--report", required=True, type=_path, help="prepared report.json")
    parser.add_argument("--schema", type=_path, default=DEFAULT_SCHEMA, help="Codex result JSON Schema")
    parser.add_argument("--model", default=os.environ.get("CUPERTINO_TASTE_CODEX_MODEL", "gpt-5.5"), help="explicit Codex model")
    parser.add_argument("--codex", default="codex", help="Codex executable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="current-apple-guidance",
        description="Deterministically acquire Apple guidance and constrain semantic review through Codex.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="fetch, normalize, compare, and report")
    _add_check_arguments(check_parser)

    review_parser = subparsers.add_parser("review", help="invoke the maintenance skill through Codex headless mode")
    _add_review_arguments(review_parser)

    accept_parser = subparsers.add_parser("accept", help="accept a prepared source set and advance Last checked")
    _add_repository_argument(accept_parser)
    accept_parser.add_argument("--report", required=True, type=_path, help="prepared report.json")
    accept_parser.add_argument("--receipt", type=_path, help="validated receipt.json; defaults beside report")

    run_parser = subparsers.add_parser("run", help="compose check, conditional review, and acceptance")
    _add_check_arguments(run_parser)
    run_parser.add_argument("--schema", type=_path, default=DEFAULT_SCHEMA, help="Codex result JSON Schema")
    run_parser.add_argument("--model", default=os.environ.get("CUPERTINO_TASTE_CODEX_MODEL", "gpt-5.5"), help="explicit Codex model")
    run_parser.add_argument("--codex", default="codex", help="Codex executable")
    return parser


def _prepare(args: argparse.Namespace) -> CheckResult:
    if args.retries < 0 or args.retries > 5:
        raise RoutineError("--retries must be between 0 and 5")
    if args.timeout <= 0 or args.timeout > 300:
        raise RoutineError("--timeout must be greater than 0 and no more than 300")
    return prepare_check(
        repo_root=args.repo_root,
        manifest_path=args.manifest,
        baseline_path=args.baseline,
        archive_root=args.archive_root,
        checked_on=args.checked_on,
        input_dir=args.input_dir,
        run_id=args.run_id,
        timeout=args.timeout,
        retries=args.retries,
    )


def _check_summary(result: CheckResult) -> Dict[str, Any]:
    return {
        "status": result.report["status"],
        "exit_code": result.exit_code,
        "checked_on": result.report["checked_on"],
        "report_sha256": result.report["report_sha256"],
        "report_path": str(result.report_path),
        "run_dir": str(result.run_dir),
        "source_set_sha256": result.report["source_set_sha256"],
    }


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "check":
        result = _prepare(args)
        _emit(_check_summary(result))
        return result.exit_code

    if args.command == "review":
        receipt_path = review_with_codex(
            repo_root=args.repo_root,
            report_path=args.report,
            schema_path=args.schema,
            model=args.model,
            codex_executable=args.codex,
        )
        _emit({"status": "reviewed", "receipt_path": str(receipt_path), "report_path": str(args.report.resolve())})
        return 0

    if args.command == "accept":
        baseline = accept_report(args.repo_root, args.report, args.receipt)
        _emit(
            {
                "status": "accepted",
                "checked_on": baseline["last_checked"],
                "source_set_sha256": baseline["source_set_sha256"],
                "report_path": str(args.report.resolve()),
            }
        )
        return 0

    if args.command == "run":
        result = _prepare(args)
        _emit(_check_summary(result))
        if result.exit_code not in {0, EXIT_CHANGED}:
            return result.exit_code
        receipt_path: Optional[Path] = None
        if result.exit_code == EXIT_CHANGED:
            receipt_path = review_with_codex(
                repo_root=args.repo_root,
                report_path=result.report_path,
                schema_path=args.schema,
                model=args.model,
                codex_executable=args.codex,
            )
            _emit({"status": "reviewed", "receipt_path": str(receipt_path)})
        baseline = accept_report(args.repo_root, result.report_path, receipt_path)
        _emit(
            {
                "status": "accepted",
                "checked_on": baseline["last_checked"],
                "source_set_sha256": baseline["source_set_sha256"],
                "report_path": str(result.report_path),
            }
        )
        return 0

    raise RoutineError("unknown command: {0}".format(args.command))


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        return dispatch(parser.parse_args(argv))
    except RoutineError as error:
        _emit({"status": "error", "exit_code": error.exit_code, "error": str(error)}, stream=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        _emit({"status": "error", "exit_code": 130, "error": "interrupted"}, stream=sys.stderr)
        return 130
    except Exception as error:
        _emit({"status": "error", "exit_code": EXIT_SOFTWARE, "error": "unexpected error: {0}".format(error)}, stream=sys.stderr)
        return EXIT_SOFTWARE


if __name__ == "__main__":
    raise SystemExit(main())
