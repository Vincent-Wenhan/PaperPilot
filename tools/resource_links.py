"""Extract evidence-backed dataset and checkpoint links from source text."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from schemas.reproduction_schema import ResourceLink


URL_PATTERN = re.compile(r"https://[^\s<>\]\[()\"']+")
RESOURCE_KEYWORDS = {
    "checkpoint": ("checkpoint", "pretrained", "pre-trained", "weights", "model zoo"),
    "dataset": ("dataset", "data set", "download", "training data", "evaluation data"),
}
CONTEXT_BOUNDARY_PATTERN = re.compile(r"(?:[.!?]\s+|\n+)")


def _clean_url(raw_url: str) -> str:
    return raw_url.rstrip(".,;:!?`")


def _destination(url: str, resource_type: str, index: int) -> str:
    parsed = urlparse(url)
    filename = PurePosixPath(unquote(parsed.path)).name
    if not filename or "." not in filename:
        filename = f"resource_{index}.bin"
    directory = "checkpoints" if resource_type == "checkpoint" else "data"
    return f"{directory}/{filename}"


def _evidence_context(text: str, start: int, end: int) -> str:
    """Return the sentence or Markdown line containing one URL."""
    context_start = 0
    context_end = len(text)
    for boundary in CONTEXT_BOUNDARY_PATTERN.finditer(text):
        if boundary.end() <= start:
            context_start = boundary.end()
            continue
        if boundary.start() >= end:
            context_end = boundary.start()
            break
    return text[context_start:context_end]


def extract_resource_links(text: str, source: str) -> list[ResourceLink]:
    """Return HTTPS links whose nearby source text identifies data or weights."""
    links: list[ResourceLink] = []
    seen: set[str] = set()
    for index, match in enumerate(URL_PATTERN.finditer(text), 1):
        url = _clean_url(match.group(0))
        if url in seen:
            continue
        context = _evidence_context(text, match.start(), match.start() + len(url))
        lowered = " ".join(context.lower().split())
        resource_type = next(
            (
                kind
                for kind, keywords in RESOURCE_KEYWORDS.items()
                if any(keyword in lowered for keyword in keywords)
            ),
            "",
        )
        if not resource_type:
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            continue
        seen.add(url)
        links.append(
            ResourceLink(
                name=PurePosixPath(unquote(parsed.path)).name or parsed.netloc,
                url=url,
                resource_type=resource_type,
                destination=_destination(url, resource_type, index),
                source=source,
                evidence=" ".join(context.split())[:500],
            )
        )
    return links
