"""Cache per-PDF reproduce analyses to avoid redundant LLM calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from config import OUTPUTS_DIR

CACHE_DIR = OUTPUTS_DIR / ".analysis_cache"


def _cache_key(
    pdf_path: str | Path,
    github_url: str,
    hardware: str,
    gpu_info: str,
    mock_mode: bool,
) -> str:
    path = Path(pdf_path).expanduser().resolve()
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    digest.update(github_url.strip().encode("utf-8"))
    digest.update(hardware.encode("utf-8"))
    digest.update(gpu_info.encode("utf-8"))
    digest.update(b"mock" if mock_mode else b"real")
    return digest.hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def load_cached_analysis(
    pdf_path: str | Path,
    *,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    mock_mode: bool = False,
) -> dict[str, Any] | None:
    """Load a cached analysis result when inputs match."""
    path = Path(pdf_path).expanduser()
    if not path.is_file():
        return None
    key = _cache_key(path, github_url, hardware, gpu_info, mock_mode)
    cache_file = _cache_path(key)
    if not cache_file.is_file():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    payload["_cache_hit"] = True
    return payload


def save_cached_analysis(
    pdf_path: str | Path,
    result: dict[str, Any],
    *,
    github_url: str = "",
    hardware: str = "Not provided",
    gpu_info: str = "",
    mock_mode: bool = False,
) -> None:
    """Persist an analysis result for reuse in Productize Mode."""
    path = Path(pdf_path).expanduser()
    if not path.is_file():
        return
    key = _cache_key(path, github_url, hardware, gpu_info, mock_mode)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in result.items() if not str(k).startswith("_")}
    serializable["cache_key"] = key
    _cache_path(key).write_text(
        json.dumps(serializable, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
