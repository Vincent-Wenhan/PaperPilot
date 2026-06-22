"""Write deterministic mock-first product prototype bundles."""

from __future__ import annotations

import shutil
import time
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from config import PROJECT_ROOT
from productize.product_templates import build_static_bundle_sources

MAX_PRODUCT_FILES = 64


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
repository analysis. It is a manifest-driven mini application with a browser
frontend and a FastAPI backend adapter.

## What This Demo Does

It demonstrates the product interaction with a deterministic mock adapter.

## Files

- `manifest.json`: generated file inventory, entrypoints, endpoints, commands
- `frontend/`: browser-native interface and local mock adapter
- `backend/`: FastAPI service and mock-first model adapter
- `requirements.txt`: backend dependencies
- `product_spec.md`: generated MVP requirements
- `outputs/`: downloaded or manually saved results

## How to Run

Install backend dependencies and start the generated API:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Open the frontend directly in a browser, or serve it locally:

```bash
python -m http.server 8080 -d frontend
```

Then open:

http://localhost:8080

## Mock Mode

This product runs in mock mode by default. Mock mode allows the demo workflow
to be shown even when the original research model is not fully integrated.

## Real Model Integration

To connect the real model, update `adapter.js` according to the original
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


def _safe_bundle_path(raw_path: str) -> PurePosixPath:
    normalized = raw_path.strip().replace("\\", "/")
    relative = PurePosixPath(normalized)
    if not normalized or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe product file path: {raw_path}")
    if relative.parts[0] in {".git", "__pycache__"}:
        raise ValueError(f"Unsafe product file path: {raw_path}")
    for part in relative.parts:
        if part in {"", ".", ".."} or part.endswith((" ", ".")):
            raise ValueError(f"Unsafe product file path: {raw_path}")
    return relative


def _custom_generated_sources(prototype_plan: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(prototype_plan, dict):
        return {}
    generated_files = prototype_plan.get("generated_files")
    if not isinstance(generated_files, list):
        return {}
    sources: dict[str, str] = {}
    for item in generated_files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        content = item.get("content")
        if not path or not isinstance(content, str):
            continue
        safe_path = _safe_bundle_path(path).as_posix()
        sources[safe_path] = content
    return sources


def _manifest(
    *,
    template_type: str,
    contents: dict[str, str],
    prototype_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    plan = prototype_plan if isinstance(prototype_plan, dict) else {}
    endpoints = plan.get("backend_endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        endpoints = [
            {"path": "/health", "method": "GET", "purpose": "Check backend readiness"},
            {"path": "/predict", "method": "POST", "purpose": "Run mock-first prediction"},
        ]
    run_commands = plan.get("run_commands")
    if not isinstance(run_commands, list) or not run_commands:
        run_commands = [
            "python -m pip install -r requirements.txt",
            "python -m uvicorn backend.main:app --reload --port 8000",
            "python -m http.server 8080 -d frontend",
        ]
    return {
        "mode": "productize",
        "template_type": template_type,
        "mock_first": True,
        "entrypoints": {
            "frontend": "frontend/index.html",
            "backend": "backend/main.py",
            "adapter": "backend/adapter.py",
        },
        "backend_endpoints": endpoints,
        "run_commands": [str(command) for command in run_commands],
        "files": [
            {
                "path": path,
                "role": _file_role(path),
                "size_bytes": len(content.encode("utf-8")),
            }
            for path, content in sorted(contents.items())
        ],
    }


def _file_role(path: str) -> str:
    if path.startswith("frontend/"):
        return "frontend"
    if path.startswith("backend/"):
        return "backend"
    if path == "requirements.txt":
        return "dependency"
    if path.endswith(".md"):
        return "documentation"
    if path.startswith("outputs/"):
        return "output"
    return "support"


def scaffold_product(
    template_type: str,
    product_spec: str,
    adapter_plan: str,
    frontend_plan: str,
    repo_path: str,
    output_dir: str | Path = "generated_product",
    prototype_plan: dict[str, Any] | None = None,
    ui_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a complete product bundle, backing up previous output."""
    root = Path(output_dir).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    root = root.resolve()
    backup_dir = _backup_existing_directory(root)
    root.mkdir(parents=True)
    (root / "outputs").mkdir()

    contents = build_static_bundle_sources(
        template_type,
        product_spec=product_spec,
        frontend_plan=frontend_plan,
        prototype_plan=prototype_plan,
        ui_spec=ui_spec,
        repo_path=repo_path,
    )
    contents.update(_custom_generated_sources(prototype_plan))
    contents.update(
        {
            "README.md": _build_readme(
                template_type,
                adapter_plan,
                frontend_plan,
            ),
            "product_spec.md": product_spec,
            "outputs/.gitkeep": "",
        }
    )
    if len(contents) > MAX_PRODUCT_FILES:
        raise ValueError(f"Generated product has too many files ({len(contents)}).")
    manifest = _manifest(
        template_type=template_type,
        contents=contents,
        prototype_plan=prototype_plan,
    )
    contents["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
    for filename, content in contents.items():
        relative = _safe_bundle_path(filename)
        target = root.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.rstrip() + "\n", encoding="utf-8")

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
        "message": "Generated static product prototype successfully.",
    }
