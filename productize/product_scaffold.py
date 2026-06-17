"""Write deterministic mock-first product prototype bundles."""

from __future__ import annotations

import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT
from productize.product_templates import build_adapter_source, build_app_source


def _backup_existing_directory(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_dir = output_dir.with_name(f"{output_dir.name}_backup_{timestamp}")
    try:
        shutil.move(str(output_dir), str(backup_dir))
    except OSError:
        shutil.copytree(str(output_dir), str(backup_dir))
        _remove_directory(output_dir)
    return backup_dir


def _remove_directory(path: Path, retries: int = 3, delay: float = 0.3) -> None:
    """Remove a directory tree with retries for transient file locks (e.g. Windows)."""
    for attempt in range(retries):
        try:
            shutil.rmtree(str(path))
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))


def _build_readme(
    template_type: str,
    adapter_plan: str,
    frontend_plan: str,
) -> str:
    return f"""# Generated Product Prototype

## Product Overview

This is a limited-scope `{template_type}` prototype generated from paper and
repository analysis.

## What This Demo Does

It demonstrates the product interaction with a deterministic mock adapter.

## Files

- `app.py`: Streamlit interface
- `adapter.py`: unified mock-first `ModelAdapter`
- `product_spec.md`: generated MVP requirements
- `outputs/`: downloaded or manually saved results

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Mock Mode

This product runs in mock mode by default. Mock mode allows the demo workflow
to be shown even when the original research model is not fully integrated.

## Real Model Integration

To connect the real model, update `adapter.py` according to the original
repository's inference code. Review dependencies, inputs, checkpoints, and
outputs manually before disabling mock mode.

### Adapter Plan

{adapter_plan or "No adapter plan was generated."}

### Frontend Plan

{frontend_plan or "No frontend plan was generated."}

## Limitations

This generated product is a prototype. It does not guarantee full reproduction
of the original paper results, and it never downloads weights, trains models,
or executes repository scripts automatically.
"""


def scaffold_product(
    template_type: str,
    product_spec: str,
    adapter_plan: str,
    frontend_plan: str,
    repo_path: str,
    output_dir: str | Path = "generated_product",
) -> dict[str, Any]:
    """Generate a complete product bundle, backing up previous output."""
    root = Path(output_dir).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    root = root.resolve()
    backup_dir = _backup_existing_directory(root)
    root.mkdir(parents=True)
    (root / "outputs").mkdir()

    contents = {
        "app.py": build_app_source(template_type, product_spec, frontend_plan),
        "adapter.py": build_adapter_source(template_type, repo_path),
        "README.md": _build_readme(
            template_type,
            adapter_plan,
            frontend_plan,
        ),
        "product_spec.md": product_spec,
        "requirements.txt": "streamlit>=1.40,<2\n",
    }
    for filename, content in contents.items():
        (root / filename).write_text(content.rstrip() + "\n", encoding="utf-8")

    files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )
    return {
        "output_dir": str(root),
        "files": files,
        "backup_dir": str(backup_dir) if backup_dir else "",
        "success": True,
        "message": "Generated product prototype successfully.",
    }
