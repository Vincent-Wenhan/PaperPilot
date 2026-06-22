"""Static checks for generated PaperPilot product prototypes."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

REQUIRED_FILES = (
    "manifest.json",
    "frontend/index.html",
    "frontend/app.js",
    "frontend/styles.css",
    "backend/main.py",
    "backend/adapter.py",
    "requirements.txt",
    "README.md",
    "product_spec.md",
)


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _basic_js_check(filename: str, source: str) -> str:
    if not source.strip():
        return f"{filename}: empty source"
    if "function invalid (" in source:
        return f"{filename}: invalid function declaration"
    pairs = {"(": ")", "{": "}", "[": "]"}
    stack: list[str] = []
    in_string = ""
    escaped = False
    for char in source:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = ""
            continue
        if char in {'"', "'", "`"}:
            in_string = char
            continue
        if char in pairs:
            stack.append(pairs[char])
        elif char in pairs.values():
            if not stack or stack.pop() != char:
                return f"{filename}: unbalanced delimiter near {char}"
    if stack:
        return f"{filename}: unbalanced delimiter"
    return ""


def inspect_generated_product(
    output_dir: str | Path = "generated_product",
) -> dict[str, Any]:
    """Inspect required files, static syntax, mock mode, and run instructions."""
    root = Path(output_dir).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    root = root.resolve()
    exists = root.is_dir()
    manifest_text = _read(root / "manifest.json")
    manifest: dict[str, Any] = {}
    manifest_errors: list[str] = []
    if manifest_text:
        try:
            parsed = json.loads(manifest_text)
            if isinstance(parsed, dict):
                manifest = parsed
            else:
                manifest_errors.append("manifest.json: expected object")
        except json.JSONDecodeError as exc:
            manifest_errors.append(f"manifest.json: {exc}")
    else:
        manifest_errors.append("manifest.json: missing")
    manifest_paths = [
        str(item.get("path") or "")
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    ]
    required_paths = set(REQUIRED_FILES)
    required_paths.update(path for path in manifest_paths if path)
    missing_files = [
        name for name in sorted(required_paths)
        if not (root / name).is_file()
    ]
    if not (root / "outputs").is_dir():
        missing_files.append("outputs/")

    frontend_entry = str(
        (manifest.get("entrypoints") or {}).get("frontend")
        or "frontend/index.html"
    )
    backend_entry = str(
        (manifest.get("entrypoints") or {}).get("backend")
        or "backend/main.py"
    )
    adapter_entry = str(
        (manifest.get("entrypoints") or {}).get("adapter")
        or "backend/adapter.py"
    )
    index_text = _read(root / frontend_entry)
    app_text = _read(root / "frontend/app.js")
    adapter_text = _read(root / adapter_entry)
    styles_text = _read(root / "frontend/styles.css")
    readme_text = _read(root / "README.md")

    compile_errors: list[str] = list(manifest_errors)
    if "<main id=\"app\"" not in index_text:
        compile_errors.append(f"{frontend_entry}: missing app mount")
    for filename in manifest_paths:
        if filename.endswith(".js"):
            error = _basic_js_check(filename, _read(root / filename))
            if error:
                compile_errors.append(error)
        if filename.endswith(".py"):
            source = _read(root / filename)
            if not source.strip() and not filename.endswith("__init__.py"):
                compile_errors.append(f"{filename}: empty source")
                continue
            try:
                ast.parse(source, filename=filename)
            except SyntaxError as exc:
                compile_errors.append(f"{filename}: {exc}")
    for filename, source in (("frontend/app.js", app_text),):
        error = _basic_js_check(filename, source)
        if error:
            compile_errors.append(error)

    can_run_mock = (
        "mock_mode" in adapter_text
        and "class ModelAdapter" in adapter_text
        and "def predict" in adapter_text
    )
    readme_has_run_command = (
        "uvicorn backend.main:app" in readme_text
        and "python -m http.server" in readme_text
    )
    run_launcher_ok = (
        '<script type="module" src="./adapter.js"></script>' in index_text
        and '<script type="module" src="./app.js"></script>' in index_text
        and "FastAPI" in _read(root / backend_entry)
        and "streamlit" not in readme_text.lower()
    )
    ui_spec_coverage = {
        "structured_controls": (
            "UI_SPEC_MARKERS" in app_text and "structured_controls" in app_text
        ),
        "result_components": (
            "UI_SPEC_MARKERS" in app_text and "result_components" in app_text
        ),
        "state_copy": "UI_SPEC_MARKERS" in app_text and "state_copy" in app_text,
        "mock_schema": "UI_SPEC_MARKERS" in app_text and "mock_schema" in app_text,
    }
    has_rich_layout = all(
        marker in app_text
        for marker in ("workspace-grid", "Core Features", "Prototype Plan", "Download JSON")
    ) and all(marker in styles_text for marker in (".workspace-grid", ".panel", ".json-block"))
    files = (
        sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file()
        )
        if exists
        else []
    )
    notes: list[str] = []
    if missing_files:
        notes.append("Generated product is missing required entries.")
    if manifest_errors:
        notes.append("Generated product manifest is missing or invalid.")
    if compile_errors:
        notes.append("Generated static source contains syntax or mounting errors.")
    if not can_run_mock:
        notes.append("Mock-mode markers were not found in adapter.js.")
    if not readme_has_run_command:
        notes.append("README.md does not include static product run instructions.")
    if not run_launcher_ok:
        notes.append("Static module wiring is missing or Streamlit is still documented.")
    if not has_rich_layout:
        notes.append("Generated static UI does not include the expected rich layout markers.")
    if not notes:
        notes.append("Static product checks passed.")

    return {
        "exists": exists,
        "missing_files": missing_files,
        "files": files,
        "can_run_mock": can_run_mock,
        "readme_has_run_command": readme_has_run_command,
        "run_launcher_ok": run_launcher_ok,
        "has_rich_layout": has_rich_layout,
        "manifest_ok": not manifest_errors and bool(manifest_paths),
        "manifest": manifest,
        "ui_spec_coverage": ui_spec_coverage,
        "syntax_ok": not compile_errors,
        "compile_errors": compile_errors,
        "notes": notes,
    }
