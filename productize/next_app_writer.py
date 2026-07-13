"""Write a GeneratedAppBundle to disk with strict path validation."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

from schemas.generated_app import GeneratedAppBundle

MAX_FILES = 160
MAX_TOTAL_BYTES = 4 * 1024 * 1024
ALLOWED_ROOTS = {
    "app",
    "components",
    "lib",
    "public",
    "tests",
    "styles",
}
ALLOWED_ROOT_FILES = {
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "next.config.mjs",
    "postcss.config.mjs",
    "tailwind.config.ts",
    "README.md",
    ".gitignore",
    "vitest.config.ts",
    "playwright.config.ts",
    ".env.example",
}


def validate_generated_path(raw: str) -> PurePosixPath:
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe generated path: {raw}")
    if len(path.parts) == 1:
        if path.name not in ALLOWED_ROOT_FILES:
            raise ValueError(f"Unexpected root file: {raw}")
    elif path.parts[0] not in ALLOWED_ROOTS:
        raise ValueError(f"Unexpected root directory: {raw}")
    return path


def write_bundle(bundle: GeneratedAppBundle, destination: Path) -> dict:
    if len(bundle.files) > MAX_FILES:
        raise ValueError("Too many generated files")

    total_bytes = sum(len(item.content.encode("utf-8")) for item in bundle.files)
    if total_bytes > MAX_TOTAL_BYTES:
        raise ValueError("Generated app exceeds size limit")

    destination.mkdir(parents=True, exist_ok=False)
    manifest: list[dict] = []
    seen: set[str] = set()

    for item in bundle.files:
        relative = validate_generated_path(item.path)
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"Duplicate file: {normalized}")
        seen.add(normalized)

        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding="utf-8")
        manifest.append(
            {
                "path": normalized,
                "sha256": hashlib.sha256(
                    item.content.encode("utf-8")
                ).hexdigest(),
                "purpose": item.purpose,
            }
        )

    return {
        "files": manifest,
        "contract": bundle.contract.model_dump(),
        "integration_notes": bundle.integration_notes,
    }
