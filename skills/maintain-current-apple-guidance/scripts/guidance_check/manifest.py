"""Versioned source-manifest parsing and invariants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from .common import RoutineError, canonical_json_bytes, read_json, sha256_bytes


SUPPORTED_ADAPTERS = {"docc-markdown", "html-article"}
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "normalizer_version",
    "max_response_bytes",
    "review_target",
    "sources",
}
EXPECTED_SOURCE_KEYS = {
    "id",
    "canonical_url",
    "fetch_url",
    "adapter",
    "expected_content_type",
    "expected_identifier",
    "expected_title",
    "affected_sections",
}


@dataclass(frozen=True)
class SourceSpec:
    id: str
    canonical_url: str
    fetch_url: str
    adapter: str
    expected_content_type: str
    expected_identifier: str
    expected_title: str
    affected_sections: Tuple[str, ...]

    @property
    def extension(self) -> str:
        return ".md" if self.adapter == "docc-markdown" else ".html"


@dataclass(frozen=True)
class Manifest:
    path: Path
    schema_version: int
    normalizer_version: str
    max_response_bytes: int
    review_target: str
    sources: Tuple[SourceSpec, ...]
    sha256: str


def _require_exact_keys(value: Dict[str, Any], expected: set, label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise RoutineError("{0} keys differ; missing={1}, unknown={2}".format(label, missing, unknown))


def _validate_apple_url(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise RoutineError("{0} must be a string".format(label))
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != "developer.apple.com" or parsed.username or parsed.password:
        raise RoutineError("{0} must be an HTTPS developer.apple.com URL".format(label))
    if parsed.fragment and label.endswith("fetch_url"):
        raise RoutineError("{0} must not contain a fragment".format(label))
    return value


def load_manifest(path: Path) -> Manifest:
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise RoutineError("manifest root must be an object")
    _require_exact_keys(raw, EXPECTED_ROOT_KEYS, "manifest")

    if raw["schema_version"] != 1:
        raise RoutineError("unsupported manifest schema_version: {0!r}".format(raw["schema_version"]))
    if not isinstance(raw["normalizer_version"], str) or not raw["normalizer_version"]:
        raise RoutineError("normalizer_version must be a nonempty string")
    if not isinstance(raw["max_response_bytes"], int) or not 1024 <= raw["max_response_bytes"] <= 10_000_000:
        raise RoutineError("max_response_bytes is outside the supported range")
    if not isinstance(raw["review_target"], str) or not raw["review_target"].endswith(".md"):
        raise RoutineError("review_target must be a repository-relative Markdown path")
    if raw["review_target"].startswith("/") or ".." in Path(raw["review_target"]).parts:
        raise RoutineError("review_target must stay inside the repository")
    if not isinstance(raw["sources"], list) or not raw["sources"]:
        raise RoutineError("manifest sources must be a nonempty array")

    sources: List[SourceSpec] = []
    seen = set()
    for index, item in enumerate(raw["sources"]):
        label = "sources[{0}]".format(index)
        if not isinstance(item, dict):
            raise RoutineError("{0} must be an object".format(label))
        _require_exact_keys(item, EXPECTED_SOURCE_KEYS, label)
        source_id = item["id"]
        if not isinstance(source_id, str) or not source_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in source_id):
            raise RoutineError("{0}.id must use lowercase letters, digits, and hyphens".format(label))
        if source_id in seen:
            raise RoutineError("duplicate source id: {0}".format(source_id))
        seen.add(source_id)
        adapter = item["adapter"]
        if adapter not in SUPPORTED_ADAPTERS:
            raise RoutineError("unsupported adapter for {0}: {1!r}".format(source_id, adapter))
        content_type = item["expected_content_type"]
        expected_type = "text/markdown" if adapter == "docc-markdown" else "text/html"
        if content_type != expected_type:
            raise RoutineError("{0} requires content type {1}".format(source_id, expected_type))
        if not isinstance(item["expected_identifier"], str):
            raise RoutineError("{0}.expected_identifier must be a string".format(label))
        if adapter == "docc-markdown" and not item["expected_identifier"]:
            raise RoutineError("{0} requires an expected DocC identifier".format(source_id))
        if adapter == "html-article" and item["expected_identifier"]:
            raise RoutineError("{0} must leave expected_identifier empty".format(source_id))
        if not isinstance(item["expected_title"], str) or not item["expected_title"]:
            raise RoutineError("{0}.expected_title must be nonempty".format(label))
        sections = item["affected_sections"]
        if not isinstance(sections, list) or not sections or not all(isinstance(section, str) and section for section in sections):
            raise RoutineError("{0}.affected_sections must be a nonempty string array".format(label))
        sources.append(
            SourceSpec(
                id=source_id,
                canonical_url=_validate_apple_url(item["canonical_url"], label + ".canonical_url"),
                fetch_url=_validate_apple_url(item["fetch_url"], label + ".fetch_url"),
                adapter=adapter,
                expected_content_type=content_type,
                expected_identifier=item["expected_identifier"],
                expected_title=item["expected_title"],
                affected_sections=tuple(sections),
            )
        )

    canonical = canonical_json_bytes(raw)
    return Manifest(
        path=path.resolve(),
        schema_version=raw["schema_version"],
        normalizer_version=raw["normalizer_version"],
        max_response_bytes=raw["max_response_bytes"],
        review_target=raw["review_target"],
        sources=tuple(sources),
        sha256=sha256_bytes(canonical),
    )
