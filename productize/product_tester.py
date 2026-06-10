"""Static checks for generated PaperPilot product prototypes."""

from __future__ import annotations

import py_compile
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

REQUIRED_FILES = (
    "app.py",
    "adapter.py",
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
    for filename in ("app.py", "adapter.py"):
        path = root / filename
        if not path.is_file():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_errors.append(f"{filename}: {exc.msg}")

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
    can_run_mock = (
        "mock_mode: bool = True" in adapter_text
        and "if self.mock_mode" in adapter_text
    )
    readme_has_run_command = "streamlit run app.py" in readme_text
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
        notes.append("README.md does not include the Streamlit run command.")
    if not notes:
        notes.append("Static product checks passed.")

    return {
        "exists": exists,
        "missing_files": missing_files,
        "files": files,
        "can_run_mock": can_run_mock,
        "readme_has_run_command": readme_has_run_command,
        "syntax_ok": not compile_errors,
        "compile_errors": compile_errors,
        "notes": notes,
    }
