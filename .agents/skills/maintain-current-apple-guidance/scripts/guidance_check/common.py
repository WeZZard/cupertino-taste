"""Shared constants, hashing, paths, and atomic file operations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


EXIT_CURRENT = 0
EXIT_CHANGED = 10
EXIT_FETCH_FAILED = 20
EXIT_SOURCE_CONTRACT = 21
EXIT_INVALID_INPUT = 22
EXIT_INVALID_REVIEW = 23
EXIT_CODEX_FAILED = 24
EXIT_USAGE = 64
EXIT_SOFTWARE = 70

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LAST_CHECKED_RE = re.compile(r"(?m)^Last checked: (\d{4}-\d{2}-\d{2})\.$")


class RoutineError(Exception):
    """An expected routine failure with a stable process exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_INVALID_INPUT) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def repository_root() -> Path:
    return Path(__file__).resolve().parents[5]


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RoutineError("missing JSON file: {0}".format(path)) from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RoutineError("invalid JSON file {0}: {1}".format(path, error)) from error


def atomic_write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        existing_mode = None
    descriptor, temporary_name = tempfile.mkstemp(prefix=".{0}.".format(path.name), dir=str(path.parent))
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        if existing_mode is not None:
            os.chmod(str(temporary_path), existing_mode)
        os.replace(str(temporary_path), str(path))
    except Exception:
        try:
            temporary_path.unlink()
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, value: str) -> None:
    atomic_write_bytes(path, value.encode("utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_bytes(path, canonical_json_bytes(value))


def validate_date(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise RoutineError("expected a date in YYYY-MM-DD form, got {0!r}".format(value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise RoutineError("invalid calendar date: {0}".format(value)) from error
    return value


def utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def utc_run_id() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S.%fZ") + "-{0}".format(os.getpid())


def default_archive_root() -> Path:
    configured = os.environ.get("CUPERTINO_TASTE_GUIDANCE_ARCHIVE")
    if configured:
        return Path(configured).expanduser().resolve()

    das_root = Path("/Volumes/DAS/3.Resources/Documentations/WWDC/cupertino-taste/current-apple-guidance")
    if Path("/Volumes/DAS").is_dir():
        return das_root

    cache_root = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_root).expanduser() if cache_root else Path.home() / "Library" / "Caches"
    return (base / "cupertino-taste" / "current-apple-guidance").resolve()


def guidance_without_date(markdown: str) -> str:
    matches = list(LAST_CHECKED_RE.finditer(markdown))
    if len(matches) != 1:
        raise RoutineError("guidance must contain exactly one 'Last checked: YYYY-MM-DD.' line")
    normalized = LAST_CHECKED_RE.sub("Last checked: <date>.", markdown)
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def guidance_digest(markdown: str) -> str:
    return sha256_bytes(guidance_without_date(markdown).encode("utf-8"))


def guidance_last_checked(markdown: str) -> str:
    matches = LAST_CHECKED_RE.findall(markdown)
    if len(matches) != 1:
        raise RoutineError("guidance must contain exactly one 'Last checked: YYYY-MM-DD.' line")
    return validate_date(matches[0])


def replace_guidance_date(markdown: str, checked_on: str) -> str:
    validate_date(checked_on)
    if len(LAST_CHECKED_RE.findall(markdown)) != 1:
        raise RoutineError("guidance must contain exactly one 'Last checked: YYYY-MM-DD.' line")
    updated = LAST_CHECKED_RE.sub("Last checked: {0}.".format(checked_on), markdown)
    if not updated.endswith("\n"):
        updated += "\n"
    return updated


def report_hash(report: Dict[str, Any]) -> str:
    unsigned = dict(report)
    unsigned.pop("report_sha256", None)
    return sha256_json(unsigned)


def receipt_hash(receipt: Dict[str, Any]) -> str:
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256", None)
    return sha256_json(unsigned)


def relative_to_repository(path: Path, repo_root: Optional[Path] = None) -> str:
    root = (repo_root or repository_root()).resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise RoutineError("path is outside repository: {0}".format(path)) from error
