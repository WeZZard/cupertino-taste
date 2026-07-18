"""Deterministic semantic normalization for Apple Markdown and HTML."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

from .common import EXIT_SOURCE_CONTRACT, RoutineError, canonical_json_bytes
from .manifest import SourceSpec


METADATA_RE = re.compile(r"\A<!--\s*(\{.*?\})\s*-->\s*", re.DOTALL)
LEGAL_FOOTER_RE = re.compile(
    r"\n---\n\nCopyright &copy; \d{4} Apple Inc\. All rights reserved\. \| "
    r"\[Terms of Use\]\(https://www\.apple\.com/legal/internet-services/terms/site\.html\) \| "
    r"\[Privacy Policy\]\(https://www\.apple\.com/privacy/privacy-policy\)\s*\Z"
)


def _decode_utf8(raw: bytes, source_id: str) -> str:
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise RoutineError("{0}: response is not strict UTF-8".format(source_id), EXIT_SOURCE_CONTRACT) from error


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = unicodedata.normalize("NFC", value)
    value = "\n".join(re.sub(r"[ \t]+$", "", line) for line in value.split("\n"))
    return value.rstrip("\n") + "\n"


def normalize_markdown(raw: bytes, source: SourceSpec) -> bytes:
    text = _normalize_text(_decode_utf8(raw, source.id))
    match = METADATA_RE.match(text)
    if not match:
        raise RoutineError("{0}: missing DocC metadata comment".format(source.id), EXIT_SOURCE_CONTRACT)
    try:
        metadata = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise RoutineError("{0}: invalid DocC metadata JSON".format(source.id), EXIT_SOURCE_CONTRACT) from error
    if metadata.get("identifier") != source.expected_identifier:
        raise RoutineError(
            "{0}: expected identifier {1!r}, got {2!r}".format(source.id, source.expected_identifier, metadata.get("identifier")),
            EXIT_SOURCE_CONTRACT,
        )
    if metadata.get("title") != source.expected_title:
        raise RoutineError(
            "{0}: expected title {1!r}, got {2!r}".format(source.id, source.expected_title, metadata.get("title")),
            EXIT_SOURCE_CONTRACT,
        )
    text = LEGAL_FOOTER_RE.sub("", text.rstrip("\n"))
    return _normalize_text(text).encode("utf-8")


Node = Dict[str, Any]
Child = Union[str, Node]


class ArticleParser(HTMLParser):
    """Extract one article as a minimal semantic tree."""

    KEEP_TAGS = {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "ul",
        "ol",
        "li",
        "dl",
        "dt",
        "dd",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "blockquote",
        "pre",
        "code",
        "strong",
        "em",
        "b",
        "i",
        "a",
        "br",
    }
    SKIP_TAGS = {"script", "style", "template", "noscript"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.main_depth = 0
        self.article_depth = 0
        self.article_count = 0
        self.skip_depth = 0
        self.root: Node = {"tag": "article", "children": []}
        self.stack: List[Node] = [self.root]
        self.keep_stack: List[bool] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attributes = dict(attrs)
        if tag == "main" and attributes.get("id") == "main" and self.main_depth == 0:
            self.main_depth = 1
            return
        if self.main_depth and not self.article_depth:
            self.main_depth += 1
            if tag == "article":
                self.article_count += 1
                self.article_depth = 1
            return
        if not self.article_depth:
            return

        if tag in self.VOID_TAGS:
            if tag == "br" and not self.skip_depth:
                self.stack[-1]["children"].append({"tag": "br", "children": []})
            return

        self.article_depth += 1
        if self.skip_depth:
            self.skip_depth += 1
            return
        if tag in self.SKIP_TAGS:
            self.skip_depth = 1
            return

        kept = tag in self.KEEP_TAGS
        self.keep_stack.append(kept)
        if kept:
            node: Node = {"tag": tag, "children": []}
            if tag == "a":
                href = attributes.get("href")
                if href:
                    node["href"] = urljoin(self.base_url, href)
            self.stack[-1]["children"].append(node)
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.article_depth and tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self.article_depth:
            if self.main_depth:
                self.main_depth -= 1
            return
        if self.skip_depth:
            self.skip_depth -= 1
            self.article_depth -= 1
            return
        if tag == "article" and self.article_depth == 1:
            self.article_depth = 0
            self.main_depth = max(1, self.main_depth - 1)
            return
        if self.keep_stack:
            kept = self.keep_stack.pop()
            if kept and len(self.stack) > 1:
                self.stack.pop()
        self.article_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.article_depth or self.skip_depth:
            return
        normalized = unicodedata.normalize("NFC", html.unescape(data))
        normalized = re.sub(r"\s+", " ", normalized)
        if normalized.strip():
            children: List[Child] = self.stack[-1]["children"]
            if children and isinstance(children[-1], str):
                children[-1] += normalized
            else:
                children.append(normalized)


def _clean_tree(node: Node) -> Optional[Node]:
    cleaned_children: List[Child] = []
    for child in node.get("children", []):
        if isinstance(child, str):
            value = re.sub(r"\s+", " ", child).strip()
            if value:
                if cleaned_children and isinstance(cleaned_children[-1], str):
                    cleaned_children[-1] = (cleaned_children[-1] + " " + value).strip()
                else:
                    cleaned_children.append(value)
        else:
            cleaned = _clean_tree(child)
            if cleaned is not None:
                cleaned_children.append(cleaned)
    if node["tag"] != "br" and not cleaned_children:
        return None
    output: Node = {"tag": node["tag"]}
    if "href" in node:
        output["href"] = node["href"]
    output["children"] = cleaned_children
    return output


def _node_plain_text(node: Node) -> str:
    pieces: List[str] = []
    for child in node.get("children", []):
        pieces.append(child if isinstance(child, str) else _node_plain_text(child))
    return re.sub(r"\s+", " ", " ".join(pieces)).strip()


def normalize_html(raw: bytes, source: SourceSpec) -> bytes:
    text = _decode_utf8(raw, source.id)
    parser = ArticleParser(source.canonical_url)
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        raise RoutineError("{0}: invalid HTML article: {1}".format(source.id, error), EXIT_SOURCE_CONTRACT) from error
    if parser.article_count != 1:
        raise RoutineError(
            "{0}: expected exactly one article inside main#main, found {1}".format(source.id, parser.article_count),
            EXIT_SOURCE_CONTRACT,
        )
    cleaned = _clean_tree(parser.root)
    if cleaned is None:
        raise RoutineError("{0}: extracted article is empty".format(source.id), EXIT_SOURCE_CONTRACT)
    headings = [
        _node_plain_text(child)
        for child in cleaned["children"]
        if isinstance(child, dict) and child.get("tag") == "h1"
    ]
    if headings != [source.expected_title]:
        raise RoutineError(
            "{0}: expected one h1 {1!r}, got {2!r}".format(source.id, source.expected_title, headings),
            EXIT_SOURCE_CONTRACT,
        )
    return canonical_json_bytes(cleaned)


def normalize_source(raw: bytes, source: SourceSpec) -> bytes:
    if source.adapter == "docc-markdown":
        return normalize_markdown(raw, source)
    if source.adapter == "html-article":
        return normalize_html(raw, source)
    raise RoutineError("unsupported adapter: {0}".format(source.adapter), EXIT_SOURCE_CONTRACT)
