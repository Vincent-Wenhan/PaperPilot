"""Static checks for generated PaperPilot product prototypes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

REQUIRED_FILES = (
    "index.html",
    "app.js",
    "adapter.js",
    "styles.css",
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
    missing_files = [
        name for name in REQUIRED_FILES if not (root / name).is_file()
    ]
    if not (root / "outputs").is_dir():
        missing_files.append("outputs/")

    index_text = _read(root / "index.html")
    app_text = _read(root / "app.js")
    adapter_text = _read(root / "adapter.js")
    styles_text = _read(root / "styles.css")
    readme_text = _read(root / "README.md")

    compile_errors: list[str] = []
    if "<main id=\"app\"" not in index_text:
        compile_errors.append("index.html: missing app mount")
    for filename, source in (("app.js", app_text), ("adapter.js", adapter_text)):
        error = _basic_js_check(filename, source)
        if error:
            compile_errors.append(error)

    can_run_mock = (
        "mockMode = true" in adapter_text
        and "class ModelAdapter" in adapter_text
        and "async predict" in adapter_text
    )
    readme_has_run_command = (
        "index.html" in readme_text
        and "python -m http.server" in readme_text
    )
    run_launcher_ok = (
        '<script type="module" src="./adapter.js"></script>' in index_text
        and '<script type="module" src="./app.js"></script>' in index_text
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
        "ui_spec_coverage": ui_spec_coverage,
        "syntax_ok": not compile_errors,
        "compile_errors": compile_errors,
        "notes": notes,
    }
