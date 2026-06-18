"""Static checks for generated PaperPilot product prototypes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

REQUIRED_FILES = (
    "app.py",
    "adapter.py",
    "run_product.py",
    "README.md",
    "product_spec.md",
    "requirements.txt",
)


def inspect_generated_product(
    output_dir: str | Path = "generated_product",
) -> dict[str, Any]:
    """Inspect required files, Python syntax, mock mode, and run instructions."""
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

    compile_errors: list[str] = []
    for filename in ("app.py", "adapter.py", "run_product.py"):
        path = root / filename
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            compile_errors.append(f"{filename}: {exc}")

    adapter_text = (
        (root / "adapter.py").read_text(encoding="utf-8")
        if (root / "adapter.py").is_file()
        else ""
    )
    readme_text = (
        (root / "README.md").read_text(encoding="utf-8")
        if (root / "README.md").is_file()
        else ""
    )
    app_text = (
        (root / "app.py").read_text(encoding="utf-8")
        if (root / "app.py").is_file()
        else ""
    )
    can_run_mock = (
        "mock_mode: bool = True" in adapter_text
        and "if self.mock_mode" in adapter_text
    )
    readme_has_run_command = (
        "python run_product.py" in readme_text
        and "python -m pip install -r requirements.txt" in readme_text
    )
    run_launcher_ok = (
        "python -m streamlit" in readme_text
        and "streamlit" in (
            (root / "run_product.py").read_text(encoding="utf-8")
            if (root / "run_product.py").is_file()
            else ""
        )
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
    legacy_rich_layout = all(
        marker in app_text
        for marker in ("st.sidebar", "st.tabs", "Confidence threshold", "Core Workflow")
    )
    structured_rich_layout = (
        all(
            ui_spec_coverage[marker]
            for marker in ("structured_controls", "result_components", "state_copy")
        )
        and all(marker in app_text for marker in ("st.sidebar", "st.tabs", "Core Workflow"))
    )
    has_rich_layout = legacy_rich_layout or structured_rich_layout
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
        notes.append("Generated Python source contains syntax errors.")
    if not can_run_mock:
        notes.append("Mock-mode markers were not found in adapter.py.")
    if not readme_has_run_command:
        notes.append("README.md does not include the generated product launcher command.")
    if not run_launcher_ok:
        notes.append("run_product.py launcher is missing or not documented.")
    if not has_rich_layout:
        notes.append("Generated app.py does not include the rich layout markers.")
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
