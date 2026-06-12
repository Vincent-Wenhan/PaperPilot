"""Safely materialize generated reproduction code bundles."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from uuid import uuid4

from config import WORKSPACE_DIR
from schemas.reproduction_schema import ImplementationBundle


MAX_GENERATED_FILES = 24
MAX_GENERATED_CHARS = 600_000
FORBIDDEN_PATH_CHARACTERS = set('<>:"|?*')
RESERVED_GENERATED_PATHS = {"code_agent_manifest.json"}
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
URL_PATTERN = re.compile(r"https://[^\s<>\]\[()\"']+")
DOWNLOAD_SCRIPT_PATH = "scripts/download_data.py"
FORBIDDEN_DOWNLOAD_TOKENS = (
    "subprocess",
    "os.system",
    "shell=true",
    "eval(",
    "exec(",
    "zipfile",
    "tarfile",
    "unpack_archive",
)


def _safe_relative_path(raw_path: str) -> PurePosixPath:
    normalized = raw_path.strip().replace("\\", "/")
    relative = PurePosixPath(normalized)
    if not normalized or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe generated file path: {raw_path}")
    if not relative.parts or relative.parts[0].lower() == ".git":
        raise ValueError(f"Unsafe generated file path: {raw_path}")
    if relative.as_posix().lower() in RESERVED_GENERATED_PATHS:
        raise ValueError(f"Reserved generated file path: {raw_path}")
    for part in relative.parts:
        reserved_name = part.split(".", maxsplit=1)[0].lower()
        if (
            part in {"", ".", ".."}
            or any(character in FORBIDDEN_PATH_CHARACTERS for character in part)
            or part.endswith((" ", "."))
            or reserved_name in WINDOWS_RESERVED_NAMES
        ):
            raise ValueError(f"Unsafe generated file path: {raw_path}")
    return relative


def materialize_implementation(
    bundle: ImplementationBundle,
    workspace_dir: str | Path = WORKSPACE_DIR,
) -> dict[str, object]:
    """Validate and write one generated implementation under the workspace."""
    if not bundle.files:
        raise ValueError("Generated implementation contains no files.")
    if len(bundle.files) > MAX_GENERATED_FILES:
        raise ValueError(
            f"Generated implementation has too many files ({len(bundle.files)})."
        )

    resource_urls: set[str] = set()
    destinations: set[str] = set()
    for resource in bundle.data_resources:
        parsed = urlparse(resource.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Data resource URL must be HTTPS: {resource.url}")
        destination = _safe_relative_path(resource.destination)
        if destination.parts[0] not in {"data", "checkpoints"}:
            raise ValueError(
                f"Data resource destination must be under data/ or checkpoints/: {destination}"
            )
        if resource.url in resource_urls or destination.as_posix().lower() in destinations:
            raise ValueError("Data resource URLs and destinations must be unique.")
        resource_urls.add(resource.url)
        destinations.add(destination.as_posix().lower())

    validated: list[tuple[PurePosixPath, str, str]] = []
    seen_paths: set[str] = set()
    total_chars = 0
    for item in bundle.files:
        relative = _safe_relative_path(item.path)
        normalized = relative.as_posix().lower()
        if normalized in seen_paths:
            raise ValueError(f"Duplicate generated file path: {relative.as_posix()}")
        total_chars += len(item.content)
        if total_chars > MAX_GENERATED_CHARS:
            raise ValueError("Generated implementation exceeds the code size limit.")
        if relative.suffix.lower() == ".py":
            try:
                ast.parse(item.content, filename=relative.as_posix())
            except SyntaxError as exc:
                raise ValueError(
                    f"Generated Python file has invalid syntax: {relative.as_posix()}: {exc}"
                ) from exc
            urls = {url.rstrip(".,;:!?`") for url in URL_PATTERN.findall(item.content)}
            if relative.as_posix() == DOWNLOAD_SCRIPT_PATH:
                lowered = item.content.lower()
                if "--execute" not in item.content or "if not args.execute" not in lowered:
                    raise ValueError(
                        "Generated data download script must default to dry-run and require --execute."
                    )
                if any(token in lowered for token in FORBIDDEN_DOWNLOAD_TOKENS):
                    raise ValueError("Generated data download script contains unsafe behavior.")
                if urls != resource_urls:
                    raise ValueError(
                        "Generated data download script URLs must exactly match data_resources."
                    )
            elif urls:
                raise ValueError(
                    f"Network URLs are only allowed in {DOWNLOAD_SCRIPT_PATH}: {relative.as_posix()}"
                )
        if relative.suffix.lower() in {".sh", ".bat", ".cmd", ".ps1"}:
            raise ValueError("Generated shell or batch download scripts are not allowed.")
        seen_paths.add(normalized)
        validated.append((relative, item.purpose, item.content))

    has_download_script = DOWNLOAD_SCRIPT_PATH in seen_paths
    if resource_urls and not has_download_script:
        raise ValueError("Data resources require scripts/download_data.py.")
    if resource_urls and (
        "scripts/download_data.py" not in bundle.data_download_command
        or "--execute" not in bundle.data_download_command
    ):
        raise ValueError(
            "Data resources require an explicit scripts/download_data.py --execute command."
        )
    if not resource_urls and (has_download_script or bundle.data_download_command.strip()):
        raise ValueError("Download script is not allowed without data resources.")

    root = Path(workspace_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"generated_reproduction_{uuid4().hex[:10]}"
    destination.mkdir(parents=False, exist_ok=False)
    written_files: list[str] = []
    purposes: dict[str, str] = {}
    for relative, purpose, content in validated:
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        path = relative.as_posix()
        written_files.append(path)
        purposes[path] = purpose

    manifest = {
        "project_name": bundle.project_name,
        "summary": bundle.summary,
        "fidelity_scope": bundle.fidelity_scope,
        "assumptions": bundle.assumptions,
        "data_resources": [
            item.model_dump(mode="json") for item in bundle.data_resources
        ],
        "data_download_command": bundle.data_download_command,
        "smoke_test_command": bundle.smoke_test_command,
        "expected_smoke_test_output": bundle.expected_smoke_test_output,
        "files": written_files,
        "file_purposes": purposes,
    }
    (destination / "CODE_AGENT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"repo_path": str(destination), **manifest}
