"""Bounded acquisition with explicit response and document contracts."""

from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .common import (
    EXIT_FETCH_FAILED,
    EXIT_SOURCE_CONTRACT,
    RoutineError,
    atomic_write_bytes,
    sha256_bytes,
)
from .manifest import SourceSpec
from .normalize import normalize_source


USER_AGENT = "cupertino-taste-guidance-check/1 (+https://github.com/WeZZard/cupertino-taste)"


class AppleRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):  # type: ignore[no-untyped-def]
        parsed = urlparse(new_url)
        if parsed.scheme != "https" or parsed.hostname != "developer.apple.com":
            raise RoutineError(
                "rejected redirect outside https://developer.apple.com: {0}".format(new_url),
                EXIT_SOURCE_CONTRACT,
            )
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def _media_type(value: str) -> str:
    return value.split(";", 1)[0].strip().lower()


def _fetch(source: SourceSpec, maximum_bytes: int, timeout: float, retries: int) -> Tuple[bytes, str, str, Dict[str, str]]:
    opener = build_opener(AppleRedirectHandler())
    headers = {
        "Accept": source.expected_content_type,
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US",
        "User-Agent": USER_AGENT,
    }
    last_error: Optional[BaseException] = None
    for attempt in range(retries + 1):
        request = Request(source.fetch_url, headers=headers, method="GET")
        try:
            with opener.open(request, timeout=timeout) as response:
                status = getattr(response, "status", response.getcode())
                if status != 200:
                    raise RoutineError("{0}: expected HTTP 200, got {1}".format(source.id, status), EXIT_SOURCE_CONTRACT)
                effective_url = response.geturl()
                parsed = urlparse(effective_url)
                if parsed.scheme != "https" or parsed.hostname != "developer.apple.com":
                    raise RoutineError("{0}: unexpected effective URL {1}".format(source.id, effective_url), EXIT_SOURCE_CONTRACT)
                content_type = response.headers.get("Content-Type", "")
                if _media_type(content_type) != source.expected_content_type:
                    raise RoutineError(
                        "{0}: expected content type {1}, got {2!r}".format(source.id, source.expected_content_type, content_type),
                        EXIT_SOURCE_CONTRACT,
                    )
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        if int(content_length) > maximum_bytes:
                            raise RoutineError("{0}: response exceeds size limit".format(source.id), EXIT_SOURCE_CONTRACT)
                    except ValueError as error:
                        raise RoutineError("{0}: invalid Content-Length".format(source.id), EXIT_SOURCE_CONTRACT) from error
                raw = response.read(maximum_bytes + 1)
                if len(raw) > maximum_bytes:
                    raise RoutineError("{0}: response exceeds size limit".format(source.id), EXIT_SOURCE_CONTRACT)
                selected_headers = {
                    key.lower(): value.strip()
                    for key, value in response.headers.items()
                    if key.lower() in {"content-type", "etag", "last-modified"}
                }
                return raw, content_type, effective_url, selected_headers
        except RoutineError:
            raise
        except HTTPError as error:
            if 400 <= error.code < 500:
                raise RoutineError("{0}: HTTP {1}".format(source.id, error.code), EXIT_SOURCE_CONTRACT) from error
            last_error = error
        except (URLError, socket.timeout, TimeoutError, OSError) as error:
            last_error = error
        if attempt < retries:
            time.sleep(float(attempt + 1))
    raise RoutineError(
        "{0}: source unavailable after {1} attempt(s): {2}".format(source.id, retries + 1, last_error),
        EXIT_FETCH_FAILED,
    )


def acquire_source(
    source: SourceSpec,
    maximum_bytes: int,
    run_dir: Path,
    input_dir: Optional[Path] = None,
    timeout: float = 20.0,
    retries: int = 2,
) -> Dict[str, Any]:
    if input_dir is not None:
        fixture_path = input_dir / (source.id + source.extension)
        try:
            raw = fixture_path.read_bytes()
        except OSError as error:
            raise RoutineError("{0}: unable to read fixture {1}: {2}".format(source.id, fixture_path, error), EXIT_FETCH_FAILED) from error
        if len(raw) > maximum_bytes:
            raise RoutineError("{0}: fixture exceeds size limit".format(source.id), EXIT_SOURCE_CONTRACT)
        content_type = source.expected_content_type
        effective_url = source.fetch_url
        response_headers: Dict[str, str] = {"content-type": source.expected_content_type}
    else:
        raw, content_type, effective_url, response_headers = _fetch(source, maximum_bytes, timeout, retries)

    normalized = normalize_source(raw, source)
    raw_path = run_dir / "raw" / (source.id + source.extension)
    normalized_extension = ".md" if source.adapter == "docc-markdown" else ".json"
    normalized_path = run_dir / "normalized" / (source.id + normalized_extension)
    atomic_write_bytes(raw_path, raw)
    atomic_write_bytes(normalized_path, normalized)

    return {
        "id": source.id,
        "canonical_url": source.canonical_url,
        "fetch_url": source.fetch_url,
        "adapter": source.adapter,
        "effective_url": effective_url,
        "content_type": content_type,
        "response_headers": response_headers,
        "response_bytes": len(raw),
        "response_sha256": sha256_bytes(raw),
        "normalized_bytes": len(normalized),
        "normalized_sha256": sha256_bytes(normalized),
        "raw_path": str(raw_path.resolve()),
        "normalized_path": str(normalized_path.resolve()),
        "affected_sections": list(source.affected_sections),
    }
